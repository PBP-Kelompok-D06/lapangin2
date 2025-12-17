# admin_dashboard/urls.py - COMPLETE FIXED VERSION
from django.urls import path
from . import views
from . import api_views

app_name = 'admin_dashboard'

urlpatterns = [
    # ========================================
    # WEB VIEWS (Django Templates)
    # ========================================
    path('', views.dashboard_home, name='dashboard_home'),
    path('lapangan/', views.lapangan_list, name='lapangan_list'),
    path('lapangan/create/', views.lapangan_create, name='lapangan_create'),
    path('lapangan/<int:pk>/edit/', views.lapangan_edit, name='lapangan_edit'),
    path('lapangan/<int:pk>/delete/', views.lapangan_delete, name='lapangan_delete'),
    path('booking/', views.booking_pending_list, name='booking_pending'),
    path('booking/<int:pk>/approve/', views.booking_approve, name='booking_approve'),
    path('booking/<int:pk>/reject/', views.booking_reject, name='booking_reject'),
    path('transaksi/', views.transaksi_list, name='transaksi_list'),
    path('booking-sessions/', views.booking_sessions_list, name='booking_sessions_list'),
    path('booking-sessions/create/', views.booking_sessions_create, name='booking_sessions_create'),
    path('booking-sessions/<int:pk>/delete/', views.booking_session_delete, name='booking_session_delete'),

    # ========================================
    # API ENDPOINTS UNTUK FLUTTER
    # ========================================
    
    # API 1: Login Admin
    path('api/login/', api_views.api_admin_login, name='api_admin_login'),
    
    # API 2: Get Dashboard Stats
    path('api/dashboard/stats/', api_views.api_dashboard_stats, name='api_dashboard_stats'),
    
    # API 3: Get Pending Bookings
    path('api/booking/pending/', api_views.api_pending_bookings, name='api_pending_bookings'),
    
    # API 4: Approve Booking
    path('api/booking/<int:booking_id>/approve/', api_views.api_approve_booking, name='api_approve_booking'),
    
    # API 5: Reject Booking
    path('api/booking/<int:booking_id>/reject/', api_views.api_reject_booking, name='api_reject_booking'),
    
    # API 6: Get Lapangan List
    path('api/lapangan/list/', api_views.api_lapangan_list, name='api_lapangan_list'),
    
    # API 7: Create Lapangan (NEW)
    path('api/lapangan/create/', api_views.api_lapangan_create, name='api_lapangan_create'),
    
    # API 8: Update Lapangan (NEW)
    path('api/lapangan/<int:lapangan_id>/update/', api_views.api_lapangan_update, name='api_lapangan_update'),
    
    # API 9: Delete Lapangan (NEW)
    path('api/lapangan/<int:lapangan_id>/delete/', api_views.api_lapangan_delete, name='api_lapangan_delete'),
    
    # API 10: Get Lapangan Detail (NEW)
    path('api/lapangan/<int:lapangan_id>/detail/', api_views.api_lapangan_detail, name='api_lapangan_detail'),
]