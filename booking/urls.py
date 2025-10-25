from django.urls import path
from . import views

# Namespace ini wajib agar kita bisa memanggil URL di template (contoh: {% url 'booking:create_booking' %})
app_name = 'booking' 

urlpatterns = [
    # Path 1: Halaman utama booking (Filter Data)
    # URL: /booking/
    path('', views.show_booking_page, name='show_booking_page'), 
    
    # Path 2: Endpoint AJAX POST untuk membuat booking (AJAX Wajib)
    # URL: /booking/create_booking/
    path('create_booking/', views.create_booking, name='create_booking'), 
    
    # Path 3: Halaman pembayaran, membutuhkan ID booking (Filter Login Wajib)
    # URL: /booking/payment/123/
    path('payment/<int:booking_id>/', views.show_payment_page, name='show_payment_page'), 

    # Path 4: Endpoint AJAX untuk update status card booking session 
    # URL: booking/check-status/
    path('check-status/', views.check_slot_status, name='check_slot_status'), 

    path('my-bookings/', views.my_bookings, name='my_bookings'),
]