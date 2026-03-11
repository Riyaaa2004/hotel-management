from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from hotel_app.models import Reservation, ReservationAuditLog
from .serializer import RegisterSerializer


class RegisterAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "User registered Successfully"}, status=201)
        return Response(serializer.errors, status=400)

class AdminApproveReservationAPIView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]

    def post(self, request, pk):
        try:
            reservation = Reservation.objects.get(
                pk=pk,
                status='requested',
                room__is_premium=True
            )
        except Reservation.DoesNotExist:
            return Response(
                {"error": "Pending premium reservation not found"},
                status=status.HTTP_404_NOT_FOUND
            )

            # lifecycle transition
        reservation.status = 'approved'
        reservation.save()

        reservation.status = 'confirmed'
        reservation.save()

        ReservationAuditLog.objects.create(
            reservation=reservation,
            user=request.user,
            action='approved'
        )

        return Response(
            {"message": "Reservation approved and confirmed"},
            status=status.HTTP_200_OK
        )


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            request.user.auth_token.delete()
            return Response({"detail": "Successfully logged out."}, status=status.HTTP_200_OK)
        except (AttributeError, Token.DoesNotExist):
            return Response({"detail": "Already logged out."}, status=status.HTTP_400_BAD_REQUEST)