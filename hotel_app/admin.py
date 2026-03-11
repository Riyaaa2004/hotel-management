from django.conf import settings
from django.contrib import admin

# Register your models here.
from django.core.mail import send_mail

from accounts.models import CustomUser
from hotel_app.models import Hotel, Room, Reservation, ReservationAuditLog

admin.site.register(CustomUser)
admin.site.register(Hotel)


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ('id', 'room_number', 'hotel', 'is_premium', 'price_per_night')
    list_filter = ('is_premium', 'hotel')
    search_fields = ('room_number', 'hotel__name')


@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'user',
        'room',
        'check_in',
        'check_out',
        'status',
        'total_price',
    )

    list_filter = ('status', 'room__is_premium')
    search_fields = ('user__username', 'room__room_number')

    def save_model(self, request, obj, form, change):
        if change:
            old_obj = Reservation.objects.get(pk=obj.pk)
            old_status = old_obj.status
        else:
            old_status = None

        super().save_model(request, obj, form, change)


        if old_status == 'requested' and obj.status == 'confirmed':
            self.send_approval_email(obj)

    def send_approval_email(self, reservation):
        user = reservation.user
        room = reservation.room

        subject = "Hotel Booking Approved ✅"
        message = (
            f"Hello {user.username},\n\n"
            f"Good news! Your booking has been APPROVED.\n\n"
            f"Hotel: {room.hotel.name}\n"
            f"Room: {room.room_number}\n"
            f"Check-in: {reservation.check_in}\n"
            f"Check-out: {reservation.check_out}\n"
            f"Total Price: ₹{reservation.total_price}\n\n"
            f"We look forward to hosting you!"
        )

        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False
        )


@admin.register(ReservationAuditLog)
class ReservationAuditLogAdmin(admin.ModelAdmin):
    list_display = ('reservation', 'user', 'action', 'timestamp')