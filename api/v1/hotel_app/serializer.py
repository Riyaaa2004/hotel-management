from django.conf import settings
from django.core.mail import send_mail
from rest_framework import serializers

from hotel_app.models import Reservation


class ReservationSerializer(serializers.ModelSerializer):
    approval_status = serializers.SerializerMethodField()

    class Meta:
        model = Reservation
        fields = '__all__'
        read_only_fields = ['user', 'total_price', 'status']

    def get_approval_status(self, obj):
        if obj.status == 'requested':
            return 'pending'
        return obj.status

    def create(self, validated_data):
        request = self.context.get('request')
        user = request.user

        reservation = Reservation.objects.create(
            user=user,
            **validated_data
        )

        room = reservation.room

        if room.is_premium:
            subject = "Hotel Booking – Pending Approval"
            message = (
                f"Hello {user.username},\n\n"
                f"Your booking request has been received.\n\n"
                f"Hotel: {room.hotel.name}\n"
                f"Room: {room.room_number}\n"
                f"Check-in: {reservation.check_in}\n"
                f"Check-out: {reservation.check_out}\n"
                f"Total Price: ₹{reservation.total_price}\n\n"
                f"Status: PENDING (Admin approval required)"
            )
        else:
            subject = "Hotel Booking Confirmed"
            message = (
                f"Hello {user.username},\n\n"
                f"Your booking is CONFIRMED.\n\n"
                f"Hotel: {room.hotel.name}\n"
                f"Room: {room.room_number}\n"
                f"Check-in: {reservation.check_in}\n"
                f"Check-out: {reservation.check_out}\n"
                f"Total Price: ₹{reservation.total_price}"
            )

        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False
        )

        return reservation
