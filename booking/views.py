from datetime import datetime
from decimal import Decimal

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

import stripe

from .models import Hotel, Room, Booking


# -------------------- Home & Auth --------------------

def home(request):
    """Home page showing all hotels and rooms."""
    hotels = Hotel.objects.all().prefetch_related('rooms')
    return render(request, 'booking/home.html', {'hotels': hotels})


def _safe_next_url(request):
    """Prevent open redirects: only allow local paths."""
    next_param = request.GET.get('next') or request.POST.get('next')
    if next_param and next_param.startswith('/'):
        return next_param
    return None


def auth_view(request):
    """Login and Signup combined page."""
    next_url = _safe_next_url(request)

    if request.method == 'POST':
        mode = request.POST.get('mode')
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')

        if mode == 'signup':
            if User.objects.filter(username=username).exists():
                messages.error(request, 'Username already exists')
            elif not username or not password:
                messages.error(request, 'Please provide both username and password.')
            else:
                User.objects.create_user(username=username, password=password)
                messages.success(request, 'Account created. Please log in.')
            return render(request, 'booking/auth.html', {'next': next_url})

        # Login flow
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            return redirect(next_url or 'home')
        messages.error(request, 'Invalid credentials')
        return render(request, 'booking/auth.html', {'next': next_url})

    return render(request, 'booking/auth.html', {'next': next_url})


def logout_view(request):
    logout(request)
    return redirect('home')


# -------------------- Bookings --------------------

@login_required
def book_room(request, room_id):
    """Booking form → POST → Redirect → Confirmation page."""
    room = get_object_or_404(Room, id=room_id)

    if request.method == 'POST':
        check_in_s = request.POST.get('check_in')
        check_out_s = request.POST.get('check_out')

        try:
            check_in = datetime.strptime(check_in_s, "%Y-%m-%d").date()
            check_out = datetime.strptime(check_out_s, "%Y-%m-%d").date()
        except Exception:
            messages.error(request, "Invalid date format.")
            return render(request, 'booking/book_room.html', {'room': room})

        if check_in >= check_out:
            messages.error(request, "Check-out must be after check-in.")
            return render(request, 'booking/book_room.html', {'room': room})

        # Check overlapping bookings
        overlap = Booking.objects.filter(room=room).filter(
            Q(check_in__lt=check_out) & Q(check_out__gt=check_in)
        ).exists()
        if overlap:
            messages.error(request, "Room already booked for those dates.")
            return render(request, 'booking/book_room.html', {'room': room})

        # Create booking → redirect to booking detail
        booking = Booking.objects.create(
            user=request.user,
            room=room,
            check_in=check_in,
            check_out=check_out,
            paid=False
        )
        messages.success(request, "Booking created! Choose Pay now or Pay later.")
        return redirect('booking_detail', booking_id=booking.id)

    return render(request, 'booking/book_room.html', {'room': room})


@login_required
def booking_detail(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)
    return render(request, 'booking/booking_detail.html', {'booking': booking})


@login_required
def my_bookings(request):
    bookings = Booking.objects.filter(user=request.user)
    return render(request, 'booking/my_bookings.html', {'bookings': bookings})


# -------------------- Payments --------------------

def stripe_config_ok():
    pk = getattr(settings, "STRIPE_PUBLIC_KEY", "")
    sk = getattr(settings, "STRIPE_SECRET_KEY", "")
    return pk.startswith("pk_test_") and sk.startswith("sk_test_")


@login_required
def pay_booking(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)
    if booking.paid:
        messages.info(request, "This booking is already paid.")
        return redirect('my_bookings')

    if not stripe_config_ok():
        messages.info(request, "Stripe not configured. Switching to Demo Pay.")
        return redirect('demo_pay', booking_id=booking.id)

    nights = max((booking.check_out - booking.check_in).days, 0)
    if nights < 1:
        messages.error(request, "Invalid booking dates.")
        return redirect('my_bookings')

    total_amount = (booking.room.price_per_night or Decimal('0')) * nights
    amount_cents = int(total_amount * 100)

    try:
        stripe.api_key = settings.STRIPE_SECRET_KEY
        session = stripe.checkout.Session.create(
            mode='payment',
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'usd',
                    'product_data': {'name': f"Room {booking.room.number} @ {booking.room.hotel.name}"},
                    'unit_amount': amount_cents,
                },
                'quantity': 1,
            }],
            metadata={'booking_id': str(booking.id)},
            success_url=request.build_absolute_uri(reverse('payment_success')) + '?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=request.build_absolute_uri(reverse('payment_cancel')),
        )
        return redirect(session.url, code=303)

    except stripe.error.AuthenticationError:
        messages.error(request, "Stripe key invalid. Switching to Demo Pay.")
        return redirect('demo_pay', booking_id=booking.id)
    except Exception as e:
        messages.error(request, f"Payment error: {e}")
        return redirect('my_bookings')


@login_required
def payment_success(request):
    session_id = request.GET.get('session_id')
    if not session_id:
        messages.error(request, "Missing payment session.")
        return redirect('my_bookings')

    stripe.api_key = settings.STRIPE_SECRET_KEY
    session = stripe.checkout.Session.retrieve(session_id)

    if session.payment_status == 'paid':
        booking_id = session.metadata.get('booking_id')
        booking = Booking.objects.filter(id=booking_id, user=request.user).first()
        if booking and not booking.paid:
            booking.paid = True
            booking.save()
            messages.success(request, "Payment successful! Booking is now PAID.")
    else:
        messages.warning(request, "Payment not completed.")

    return redirect('my_bookings')


@login_required
def payment_cancel(request):
    messages.info(request, "Payment canceled.")
    return redirect('my_bookings')


@login_required
def demo_pay(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)
    if booking.paid:
        messages.info(request, "This booking is already paid.")
        return redirect('my_bookings')

    if request.method == 'POST':
        booking.paid = True
        booking.save()
        messages.success(request, "Demo payment successful. Booking marked as PAID.")
        return redirect('my_bookings')

    return render(request, 'booking/demo_pay.html', {'booking': booking})
