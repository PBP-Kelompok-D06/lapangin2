# lapangin2/booking/urls.py
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


    # ========================================
    # API ENDPOINTS UNTUK FLUTTER
    # ========================================
    
    # API 1: Get All Lapangan
    # GET /booking/api/lapangan/
    path('api/lapangan/', views.api_get_lapangan_list, name='api_lapangan_list'),
    
    # API 2: Get Lapangan Detail
    # GET /booking/api/lapangan/<id>/
    path('api/lapangan/<int:lapangan_id>/', views.api_get_lapangan_detail, name='api_lapangan_detail'),
    
    # API 3: Get Available Slots
    # GET /booking/api/slots/<lapangan_id>/?date=YYYY-MM-DD&days=7
    path('api/slots/<int:lapangan_id>/', views.api_get_available_slots, name='api_available_slots'),
    
    # API 4: Create Booking
    # POST /booking/api/create/
    path('api/create/', views.api_create_booking, name='api_create_booking'),
    
    # API 5: Get Booking Detail
    # GET /booking/api/booking/<booking_id>/
    path('api/booking_detail/<int:booking_id>/', views.api_get_booking_detail, name='api_booking_detail'),
    
    # API 6: Get My Bookings
    # GET /booking/api/my-bookings/
    path('api/my-bookings/', views.api_get_my_bookings, name='api_my_bookings'),
    
    # API 7: Cancel Booking
    # POST /booking/api/booking/<booking_id>/cancel/
    path('api/booking/<int:booking_id>/cancel/', views.api_cancel_booking, name='api_cancel_booking'),
]