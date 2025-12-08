# admin_dashboard/api_views.py
"""
API Views untuk Admin Dashboard - Flutter Integration
Pekan 1: Login & Dashboard Home
Pekan 2: Booking Management APIs
"""

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth import authenticate
from django.shortcuts import get_object_or_404
from booking.models import Booking, Lapangan, SlotTersedia
from community.models import Community, CommunityRequest
import json




@csrf_exempt
@require_http_methods(["POST"])
def api_admin_login(request):
    """
    API Login untuk Admin Dashboard
    
    POST /dashboard/api/login/
    
    Request Body:
    {
        "username": "string",
        "password": "string"
    }
    
    Response Success (200):
    {
        "status": true,
        "message": "Login berhasil",
        "data": {
            "username": "juragan01",
            "role": "PEMILIK",
            "nomor_whatsapp": "081234567890",
            "nomor_rekening": "1234567890"
        }
    }
    """
    try:
        # Parse request body
        data = json.loads(request.body)
        username = data.get('username', '').strip()
        password = data.get('password', '')
        
        # Validasi input
        if not username or not password:
            return JsonResponse({
                'status': False,
                'message': 'Username dan password harus diisi'
            }, status=400)
        
        # Autentikasi user
        user = authenticate(request, username=username, password=password)
        
        if user is None:
            return JsonResponse({
                'status': False,
                'message': 'Username atau password salah'
            }, status=401)
        
        # Cek apakah user memiliki profile
        if not hasattr(user, 'profile'):
            return JsonResponse({
                'status': False,
                'message': 'User tidak memiliki profile'
            }, status=401)
        
        # Cek apakah user adalah PEMILIK
        if user.profile.role != 'PEMILIK':
            return JsonResponse({
                'status': False,
                'message': 'Hanya PEMILIK lapangan yang dapat login ke dashboard admin'
            }, status=403)
        
        # Login berhasil
        return JsonResponse({
            'status': True,
            'message': 'Login berhasil',
            'data': {
                'username': user.username,
                'role': user.profile.role,
                'nomor_whatsapp': user.profile.nomor_whatsapp or '',
                'nomor_rekening': user.profile.nomor_rekening or '',
            }
        }, status=200)
    
    except json.JSONDecodeError:
        return JsonResponse({
            'status': False,
            'message': 'Format JSON tidak valid'
        }, status=400)
    
    except Exception as e:
        return JsonResponse({
            'status': False,
            'message': f'Terjadi kesalahan: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def api_get_pending_bookings(request):
    """
    API untuk mengambil daftar booking PENDING
    
    GET /dashboard/api/booking/pending/
    
    Headers:
    - Cookie: sessionid=xxx (dari login)
    
    Response Success (200):
    {
        "status": "success",
        "data": [
            {
                "id": 1,
                "user": {
                    "username": "user1",
                    "email": "user1@test.com"
                },
                "lapangan": {
                    "id": 1,
                    "nama": "Futsal A",
                    "jenis_olahraga": "Futsal",
                    "lokasi": "Jakarta"
                },
                "slot": {
                    "tanggal": "2025-12-05",
                    "jam_mulai": "09:00",
                    "jam_akhir": "10:00"
                },
                "total_bayar": 100000,
                "tanggal_booking": "2025-12-04 10:30:00",
                "status_pembayaran": "PENDING"
            }
        ]
    }
    """
    # Cek autentikasi
    if not request.user.is_authenticated:
        return JsonResponse({
            'status': 'error',
            'message': 'Anda harus login terlebih dahulu'
        }, status=401)
    
    # Cek role PEMILIK
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'PEMILIK':
        return JsonResponse({
            'status': 'error',
            'message': 'Hanya PEMILIK yang dapat mengakses endpoint ini'
        }, status=403)
    
    try:
        # Ambil booking PENDING untuk lapangan milik pemilik
        pending_bookings = Booking.objects.filter(
            slot__lapangan__pengelola=request.user.profile,
            status_pembayaran='PENDING'
        ).select_related(
            'user',
            'slot',
            'slot__lapangan'
        ).order_by('-tanggal_booking')
        
        # Format data
        data = []
        for booking in pending_bookings:
            data.append({
                'id': booking.id,
                'user': {
                    'username': booking.user.username,
                    'email': booking.user.email
                },
                'lapangan': {
                    'id': booking.slot.lapangan.id,
                    'nama': booking.slot.lapangan.nama_lapangan,
                    'jenis_olahraga': booking.slot.lapangan.jenis_olahraga,
                    'lokasi': booking.slot.lapangan.lokasi
                },
                'slot': {
                    'tanggal': booking.slot.tanggal.strftime('%Y-%m-%d'),
                    'jam_mulai': booking.slot.jam_mulai.strftime('%H:%M'),
                    'jam_akhir': booking.slot.jam_akhir.strftime('%H:%M')
                },
                'total_bayar': float(booking.total_bayar),
                'tanggal_booking': booking.tanggal_booking.strftime('%Y-%m-%d %H:%M:%S'),
                'status_pembayaran': booking.status_pembayaran
            })
        
        return JsonResponse({
            'status': 'success',
            'data': data
        }, status=200)
    
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': f'Terjadi kesalahan: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def api_approve_booking(request, booking_id):
    """
    API untuk approve booking PENDING → PAID
    
    POST /dashboard/api/booking/{id}/approve/
    
    Response Success (200):
    {
        "status": "success",
        "message": "Booking berhasil di-approve"
    }
    """
    # Cek autentikasi
    if not request.user.is_authenticated:
        return JsonResponse({
            'status': 'error',
            'message': 'Anda harus login terlebih dahulu'
        }, status=401)
    
    # Cek role PEMILIK
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'PEMILIK':
        return JsonResponse({
            'status': 'error',
            'message': 'Hanya PEMILIK yang dapat mengakses endpoint ini'
        }, status=403)
    
    try:
        # Ambil booking
        booking = get_object_or_404(
            Booking,
            pk=booking_id,
            slot__lapangan__pengelola=request.user.profile
        )
        
        # Cek status
        if booking.status_pembayaran != 'PENDING':
            return JsonResponse({
                'status': 'error',
                'message': 'Booking ini sudah diproses'
            }, status=400)
        
        # Update status booking
        booking.status_pembayaran = 'PAID'
        booking.save()
        
        # Update slot
        slot = booking.slot
        slot.is_available = False
        slot.pending_booking = None
        slot.save()
        
        return JsonResponse({
            'status': 'success',
            'message': 'Booking berhasil di-approve'
        }, status=200)
    
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': f'Terjadi kesalahan: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def api_reject_booking(request, booking_id):
    """
    API untuk reject booking PENDING → CANCELLED
    
    POST /dashboard/api/booking/{id}/reject/
    
    Response Success (200):
    {
        "status": "success",
        "message": "Booking berhasil ditolak"
    }
    """
    # Cek autentikasi
    if not request.user.is_authenticated:
        return JsonResponse({
            'status': 'error',
            'message': 'Anda harus login terlebih dahulu'
        }, status=401)
    
    # Cek role PEMILIK
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'PEMILIK':
        return JsonResponse({
            'status': 'error',
            'message': 'Hanya PEMILIK yang dapat mengakses endpoint ini'
        }, status=403)
    
    try:
        # Ambil booking
        booking = get_object_or_404(
            Booking,
            pk=booking_id,
            slot__lapangan__pengelola=request.user.profile
        )
        
        # Cek status
        if booking.status_pembayaran != 'PENDING':
            return JsonResponse({
                'status': 'error',
                'message': 'Booking ini sudah diproses'
            }, status=400)
        
        # Update status booking
        booking.status_pembayaran = 'CANCELLED'
        booking.save()
        
        # Update slot (kembali available)
        slot = booking.slot
        slot.is_available = True
        slot.pending_booking = None
        slot.save()
        
        return JsonResponse({
            'status': 'success',
            'message': 'Booking berhasil ditolak'
        }, status=200)
    
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': f'Terjadi kesalahan: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def api_get_lapangan_list(request):
    """
    API untuk mengambil daftar lapangan milik pemilik
    
    GET /dashboard/api/lapangan/list/
    
    Response Success (200):
    {
        "status": "success",
        "data": [
            {
                "id": 1,
                "nama_lapangan": "Futsal A",
                "jenis_olahraga": "Futsal",
                "lokasi": "Jakarta",
                "harga_per_jam": 100000,
                "rating": 4.5,
                "jumlah_ulasan": 10
            }
        ]
    }
    """
    # Cek autentikasi
    if not request.user.is_authenticated:
        return JsonResponse({
            'status': 'error',
            'message': 'Anda harus login terlebih dahulu'
        }, status=401)
    
    # Cek role PEMILIK
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'PEMILIK':
        return JsonResponse({
            'status': 'error',
            'message': 'Hanya PEMILIK yang dapat mengakses endpoint ini'
        }, status=403)
    
    try:
        # Ambil lapangan milik pemilik
        lapangan_list = Lapangan.objects.filter(
            pengelola=request.user.profile,
            is_active=True
        ).order_by('nama_lapangan')
        
        # Format data
        data = []
        for lapangan in lapangan_list:
            data.append({
                'id': lapangan.id,
                'nama_lapangan': lapangan.nama_lapangan,
                'jenis_olahraga': lapangan.jenis_olahraga,
                'lokasi': lapangan.lokasi,
                'harga_per_jam': float(lapangan.harga_per_jam),
                'rating': float(lapangan.rating),
                'jumlah_ulasan': lapangan.jumlah_ulasan,
                'foto_utama': request.build_absolute_uri(lapangan.foto_utama.url) if lapangan.foto_utama else None
            })
        
        return JsonResponse({
            'status': 'success',
            'data': data
        }, status=200)
    
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': f'Terjadi kesalahan: {str(e)}'
        }, status=500)