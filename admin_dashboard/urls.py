from django.urls import path
from . import views

app_name = 'admin_dashboard'

urlpatterns = [
    # Dashboard Home
    path('', views.dashboard_home, name='dashboard_home'),
    
    # Lapangan Management
    path('lapangan/', views.lapangan_list, name='lapangan_list'),
    path('lapangan/create/', views.lapangan_create, name='lapangan_create'),
    path('lapangan/<int:pk>/edit/', views.lapangan_edit, name='lapangan_edit'),
    path('lapangan/<int:pk>/delete/', views.lapangan_delete, name='lapangan_delete'),
    
    # Booking Management
    path('booking/', views.booking_pending_list, name='booking_pending'),
    path('booking/<int:pk>/approve/', views.booking_approve, name='booking_approve'),
    path('booking/<int:pk>/reject/', views.booking_reject, name='booking_reject'),
    
    # Transaksi/Riwayat
    path('transaksi/', views.transaksi_list, name='transaksi_list'),

    # Booking Sessions
    path('booking-sessions/', views.booking_sessions_list, name='booking_sessions_list'),
    path('booking-sessions/create/', views.booking_sessions_create, name='booking_sessions_create'),
    path('booking-sessions/<int:pk>/delete/', views.booking_session_delete, name='booking_session_delete'),

    # ========================================
    # API ENDPOINTS UNTUK FLUTTER
    # ========================================
    
    # API 1: Login Admin
    path('api/login/', views.api_admin_login, name='api_admin_login'),
    
    # API 2: Get Dashboard Stats
    path('api/dashboard/stats/', views.api_dashboard_stats, name='api_dashboard_stats'),
    
    # API 3: Get Pending Bookings
    path('api/booking/pending/', views.api_pending_bookings, name='api_pending_bookings'),
    
    # API 4: Approve Booking
    path('api/booking/<int:booking_id>/approve/', views.api_approve_booking, name='api_approve_booking'),
    
    # API 5: Reject Booking
    path('api/booking/<int:booking_id>/reject/', views.api_reject_booking, name='api_reject_booking'),
    
    # API 6: Get Lapangan List
    path('api/lapangan/list/', views.api_lapangan_list, name='api_lapangan_list'),
]