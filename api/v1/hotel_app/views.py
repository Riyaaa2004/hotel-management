from smtplib import SMTPException

from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from hotel_app.models import Reservation
from .serializer import ReservationSerializer


class ReservationAPIView(APIView):
    permission_classes = [IsAuthenticated]

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
            reservation = serializer.save()
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
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            reservation = Reservation.objects.get(pk=pk, user=request.user)
        except Reservation.DoesNotExist:
            return Response(
                {"error": "Reservation not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = ReservationSerializer(reservation)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request, pk):
        try:
            reservation = Reservation.objects.get(pk=pk, user=request.user)
        except Reservation.DoesNotExist:
            return Response({"error": "Reservation not found"}, status=404)

        if reservation.status in ['confirmed', 'completed', 'cancelled']:
            return Response(
                {"error": "Cannot modify confirmed bookings"},
                status=400
            )

        serializer = ReservationSerializer(
            reservation,
            data=request.data,
            context={'request': request}
        )

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)

        return Response(serializer.errors, status=400)

    def patch(self, request, pk):
        try:
            reservation = Reservation.objects.get(pk=pk, user=request.user)
        except Reservation.DoesNotExist:
            return Response({"error": "Reservation not found"}, status=404)

        if reservation.status in ['confirmed','checked_in', 'completed', 'cancelled']:
            return Response(
                {"error": "Confirmed bookings cannot be modified"},
                status=400
            )

        serializer = ReservationSerializer(
            reservation,
            data=request.data,
            partial=True,
            context={'request': request}
        )

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)

        return Response(serializer.errors, status=400)

    def delete(self, request, pk):
        try:
            reservation = Reservation.objects.get(pk=pk, user=request.user)
        except Reservation.DoesNotExist:
            return Response({"error": "Reservation not found"}, status=404)

        if reservation.status in ['checked_in','completed']:
            return Response(
                {"error": "Cannot cancel after check-in"},
                status=400
            )

        reservation.status = 'cancelled'
        reservation.save()

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
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            reservation = Reservation.objects.get(pk=pk, user=request.user)
        except Reservation.DoesNotExist:
            return Response({"error": "Reservation not found"}, status=404)

        if reservation.status != 'confirmed':
            return Response(
                {"error": "Only confirmed bookings can check-in"},
                status=400
            )

        reservation.status = 'checked_in'
        reservation.save()

        return Response({"message": "Check-in successful"}, status=200)


class CheckOutAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            reservation = Reservation.objects.get(pk=pk, user=request.user)
        except Reservation.DoesNotExist:
            return Response({"error": "Reservation not found"}, status=404)

        if reservation.status != 'checked_in':
            return Response(
                {"error": "You must check-in before check-out"},
                status=400
            )

        reservation.status = 'completed'
        reservation.save()

        return Response({"message": "Check-out completed"}, status=200)
