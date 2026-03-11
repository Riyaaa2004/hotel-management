from smtplib import SMTPException

from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.db import transaction
from django.db.models import Count, Sum
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from hotel_app.models import Reservation, Room, ReservationAuditLog
from .permissions import IsReservationOwner
from .serializer import ReservationSerializer
from .throttles import BookingThrottle


class ReservationAPIView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [BookingThrottle]

    def post(self, request):

        if not request.user.is_verified:
            return Response(
                {"error": "User not verified"},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = ReservationSerializer(
            data=request.data,
            context={'request': request}
        )

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            with transaction.atomic():
                room = Room.objects.select_for_update().get(
                    pk=serializer.validated_data["room"].id
                )

            reservation = serializer.save()

            ReservationAuditLog.objects.create(
                reservation=reservation,
                user=request.user,
                action='created'
            )

            return Response(
                ReservationSerializer(reservation).data,
                status=status.HTTP_201_CREATED
            )

        except ValidationError as e:
            return Response(
                {"error": e.message_dict.get("__all__", e.messages)},
                status=status.HTTP_400_BAD_REQUEST
            )

        except SMTPException as e:
            return Response(
                {"error": "Booking saved but email failed"},
                status=status.HTTP_201_CREATED
            )

        except Exception as e:

            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ReservationDetailAPIView(APIView):
    permission_classes = [IsAuthenticated, IsReservationOwner]

    def get_object(self, pk):
        try:
            return Reservation.objects.get(pk=pk)
        except Reservation.DoesNotExist:
            return None

    def get(self, request, pk):
        reservation = self.get_object(pk)
        if not reservation:
            return Response({"error": "Reservation not found"}, status=404)

        self.check_object_permissions(request, reservation)

        serializer = ReservationSerializer(reservation)
        return Response(serializer.data, status=200)

    def put(self, request, pk):
        reservation = self.get_object(pk)
        self.check_object_permissions(request, reservation)

        if reservation.status in ['confirmed', 'checked_in', 'completed', 'cancelled']:
            return Response(
                {"error": "Cannot modify this reservation"},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = ReservationSerializer(
            reservation,
            data=request.data,
            context={'request': request}
        )

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request, pk):
        reservation = self.get_object(pk)

        self.check_object_permissions(request, reservation)

        if reservation.status in ['confirmed', 'checked_in', 'completed', 'cancelled']:
            return Response(
                {"error": "Cannot modify this reservation"},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = ReservationSerializer(
            reservation,
            data=request.data,
            partial=True,
            context={'request': request}
        )

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        reservation = self.get_object(pk)

        self.check_object_permissions(request, reservation)

        if reservation.status in ['checked_in', 'completed']:
            return Response(
                {"error": "Cannot cancel after check-in"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if reservation.status == 'cancelled':
            return Response(
                {"error": "Reservation already cancelled"},
                status=status.HTTP_400_BAD_REQUEST
            )

        reservation.status = 'cancelled'
        reservation.save()

        ReservationAuditLog.objects.create(
            reservation=reservation,
            user=request.user,
            action='cancelled'
        )

        return Response(
            {"message": "Reservation cancelled"},
            status=status.HTTP_200_OK
        )


class ReservationListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        reservations = Reservation.objects.filter(user=request.user)
        return Response(
            ReservationSerializer(reservations, many=True).data
        )


class CheckInAPIView(APIView):
    permission_classes = [IsAuthenticated, IsReservationOwner]

    def get_object(self, pk):
        try:
            return Reservation.objects.get(pk=pk)
        except Reservation.DoesNotExist:
            return None

    def post(self, request, pk):
        reservation = self.get_object(pk)
        if not reservation:
            return Response({"error": "Reservation not found"}, status=404)

        self.check_object_permissions(request, reservation)

        if reservation.status != 'confirmed':
            return Response(
                {"error": "Only confirmed bookings can check-in"},
                status=400
            )

        reservation.status = 'checked_in'
        reservation.save()

        return Response({"message": "Check-in successful"}, status=200)


class CheckOutAPIView(APIView):
    permission_classes = [IsAuthenticated, IsReservationOwner]

    def get_object(self, pk):
        try:
            return Reservation.objects.get(pk=pk)
        except Reservation.DoesNotExist:
            return None

    def post(self, request, pk):
        reservation = self.get_object(pk)
        if not reservation:
            return Response({"error": "Reservation not found"}, status=404)

        self.check_object_permissions(request, reservation)

        if reservation.status != 'checked_in':
            return Response(
                {"error": "You must check-in before check-out"},
                status=400
            )

        reservation.status = 'completed'
        reservation.save()

        return Response({"message": "Check-out completed"}, status=200)


class RoomAvailabilityAPIView(APIView):
    def get(self, request):
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')

        if not start_date or not end_date:
            return Response(
                {"error": "start_date and end_date are required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        cache_key = f"availability_{start_date}_{end_date}"
        cached_result = cache.get(cache_key)

        if cached_result:
            return Response({
                "source": "cache",
                **cached_result
            })

        overlapping_reservations = Reservation.objects.filter(
            check_in__lt=end_date,
            check_out__gt=start_date,
            status__in=['requested', 'approved', 'confirmed', 'checked_in']
        ).values_list('room_id', flat=True)


        available_rooms = Room.objects.exclude(id__in=overlapping_reservations)

        result = {
            "start_date": start_date,
            "end_date": end_date,
            "available_rooms_count": available_rooms.count(),
            "available_room_ids": list(available_rooms.values_list('id', flat=True))
        }
        cache.set(cache_key, result, timeout=300)

        return Response({
            "source": "database",
            **result
        })



class HotelOccupancyAPIView(APIView):
    def get(self, request, hotel_id):
        total_rooms = Room.objects.filter(hotel_id=hotel_id).count()

        if total_rooms == 0:
            return Response(
                {"error": "No rooms found for this hotel"},
                status=status.HTTP_404_NOT_FOUND
            )

        occupied_rooms = Reservation.objects.filter(
            room__hotel_id=hotel_id,
            status__in=['confirmed', 'checked_in']
        ).values('room').distinct().count()

        occupancy_rate = (occupied_rooms / total_rooms) * 100

        return Response({
            "hotel_id" : hotel_id,
            "total_rooms" : total_rooms,
            "occupied_rooms": occupied_rooms,
            "occupancy_rate" : round(occupancy_rate, 2)
        }, status=status.HTTP_200_OK)


class MostBookedRoomsAPIView(APIView):
    def get(self, request):
        bookings = Reservation.objects.filter(
            status__in=['confirmed', 'checked_in', 'completed']
        ).values(
            'room__id',
            'room__room_number',
            'room__hotel__name',
            'room__is_premium'
        ).annotate(
            total_bookings=Count('id')
        ).order_by('-total_bookings')

        return Response(bookings, status=status.HTTP_200_OK)


class RevenueAPIView(APIView):
    def get(self, request):

        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')

        if not start_date or not end_date:
            return Response(
                {"error": "start_date and end_date are required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        revenue_data = Reservation.objects.filter(
            status='completed',
            check_in__gte=start_date,
            check_out__lte=end_date
        ).aggregate(
            total_revenue=Sum('total_price')
        )

        total_revenue = revenue_data['total_revenue'] or 0

        return Response({
            "start_date": start_date,
            "end_date": end_date,
            "total_revenue": total_revenue
        }, status=status.HTTP_200_OK)

