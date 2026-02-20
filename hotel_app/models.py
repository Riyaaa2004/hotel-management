from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

# Create your models here.

User = settings.AUTH_USER_MODEL

class Hotel(models.Model):
    name = models.CharField(max_length=100)
    location = models.CharField(max_length=100)

    def __str__(self):
        return self.name

class Room(models.Model):
    hotel = models.ForeignKey(Hotel, on_delete=models.CASCADE)
    room_number = models.CharField(max_length=10)
    price_per_night = models.DecimalField(max_digits=8, decimal_places=2)
    is_premium = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.hotel.name} - {self.room_number}"


class Reservation(models.Model):
    STATUS = (
        ('requested', 'Requested'),
        ('approved', 'Approved'),
        ('confirmed', 'Confirmed'),
        ('checked_in', 'Checked In'),
        ('cancelled', 'Cancelled'),
        ('completed', 'Completed')
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    room = models.ForeignKey(Room, on_delete=models.CASCADE)
    check_in = models.DateField()
    check_out = models.DateField()
    total_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS, default='requested')

    def clean(self):
        if self.check_in >= self.check_out:
            raise ValidationError("Invalid date range")

        overlap = Reservation.objects.filter(
            room=self.room,
            check_in__lt=self.check_out,
            check_out__gt=self.check_in,
            status__in=['requested', 'approved', 'confirmed']
        )
        if self.pk:
            overlap = overlap.exclude(pk=self.pk)

        if overlap.exists():
            raise ValidationError("Room already booked")

    def save(self, *args, **kwargs):
        nights = (self.check_out - self.check_in).days
        self.total_price = nights * self.room.price_per_night

        if not self.pk and not self.room.is_premium:
            self.status = 'confirmed'

        self.full_clean()
        super().save(*args, **kwargs)
