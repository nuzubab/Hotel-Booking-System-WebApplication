from datetime import date, timedelta
from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse
from booking.models import Hotel, Room, Booking


class BookingFlowTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('testuser', password='pw123')
        self.hotel = Hotel.objects.create(name="Demo Hotel", city="Melbourne")
        self.room = Room.objects.create(
            hotel=self.hotel,
            number="101",
            room_type="Standard",
            price_per_night=100,
            capacity=2
        )

    def test_home_page_renders(self):
        """Home page loads successfully."""
        resp = self.client.get(reverse('home'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Demo Hotel")

    def test_login_required_for_booking(self):
        """Booking page requires login."""
        url = reverse('book_room', args=[self.room.id])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 302)
        self.assertIn(reverse('auth'), resp.url)

    def test_create_booking_redirects(self):
        """Booking creation should redirect then load detail page."""
        self.client.login(username='testuser', password='pw123')
        url = reverse('book_room', args=[self.room.id])
        payload = {
            "check_in": date.today().isoformat(),
            "check_out": (date.today() + timedelta(days=1)).isoformat()
        }
        resp = self.client.post(url, payload)
        self.assertEqual(resp.status_code, 302)  # Redirect to detail page

        resp2 = self.client.post(url, payload, follow=True)
        self.assertEqual(resp2.status_code, 200)
        self.assertContains(resp2, "Booking created!")
        self.assertEqual(Booking.objects.count(), 1)

    def test_my_bookings_shows_only_user_bookings(self):
        """My bookings page should show only logged-in user's bookings."""
        self.client.login(username='testuser', password='pw123')
        Booking.objects.create(
            user=self.user,
            room=self.room,
            check_in=date.today(),
            check_out=date.today() + timedelta(days=1),
            paid=False
        )
        user2 = User.objects.create_user('otheruser', password='pw456')
        self.client.logout()
        self.client.login(username='otheruser', password='pw456')
        resp = self.client.get(reverse('my_bookings'))
        self.assertEqual(resp.status_code, 200)
        self.assertNotContains(resp, "Booking #1")

    def test_admin_login_page_redirects(self):
        """Admin page should redirect to login page if not logged in."""
        resp = self.client.get('/admin/')
        self.assertEqual(resp.status_code, 302)
