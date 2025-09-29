from django.conf import settings
from django.db import models
from decimal import Decimal


class Hotel(models.Model):
    name = models.CharField(max_length=120)
    city = models.CharField(max_length=120, blank=True)
    address = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return f"{self.name} ({self.city})" if self.city else self.name

class Room(models.Model):
    hotel = models.ForeignKey(Hotel, on_delete=models.CASCADE, related_name='rooms')
    number = models.CharField(max_length=20)
    room_type = models.CharField(max_length=50, default='Standard')
    price_per_night = models.DecimalField(max_digits=8, decimal_places=2)
    capacity = models.PositiveIntegerField(default=2)

    def __str__(self):
        return f"{self.hotel.name} - Room {self.number}"

class Booking(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    room = models.ForeignKey(Room, on_delete=models.CASCADE)
    check_in = models.DateField()
    check_out = models.DateField()
    paid = models.BooleanField(default=False)
    @property
    def nights(self):
        # number of nights between the two dates (never negative)
        return max((self.check_out - self.check_in).days, 0)

    @property
    def total_amount(self):
        # price_per_night is Decimal; multiply by nights
        price = self.room.price_per_night or Decimal('0')
        return price * self.nights

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Booking #{self.id} - {self.user} - {self.room}"
