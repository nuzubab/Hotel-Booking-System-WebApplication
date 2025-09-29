from django.core.management.base import BaseCommand
from booking.models import Hotel, Room

class Command(BaseCommand):
    help = "Create demo hotel and rooms"

    def handle(self, *args, **kwargs):
        h, _ = Hotel.objects.get_or_create(name="Demo Hotel", city="Melbourne")
        for i in (101, 102, 201, 202):
            Room.objects.get_or_create(
                hotel=h, number=str(i),
                defaults={"room_type":"Standard","price_per_night":100,"capacity":2}
            )
        self.stdout.write(self.style.SUCCESS("Demo data created."))
