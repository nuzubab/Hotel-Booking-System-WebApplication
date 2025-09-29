from django.contrib import admin
from django.urls import path
from booking import views

urlpatterns = [
    path('admin/', admin.site.urls),

    # public / user routes
    path('', views.home, name='home'),
    path('auth/', views.auth_view, name='auth'),
    path('logout/', views.logout_view, name='logout'),

    # booking flow
    path('book/<int:room_id>/', views.book_room, name='book_room'),
    path('booking/<int:booking_id>/', views.booking_detail, name='booking_detail'),
    path('my-bookings/', views.my_bookings, name='my_bookings'),

    # payments
    path('pay/<int:booking_id>/', views.pay_booking, name='pay_booking'),
    path('payment/success/', views.payment_success, name='payment_success'),
    path('payment/cancel/', views.payment_cancel, name='payment_cancel'),

    # demo pay fallback (no Stripe)
    path('demo-pay/<int:booking_id>/', views.demo_pay, name='demo_pay'),
]
