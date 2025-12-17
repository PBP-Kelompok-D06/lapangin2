# admin_dashboard/api_views.py - COMPLETE FIXED VERSION
"""
API Views untuk Admin Dashboard - Flutter Integration
Lengkap dengan semua endpoint yang dibutuhkan Flutter
"""

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth import authenticate, login
from django.shortcuts import get_object_or_404
from booking.models import Booking, Lapangan, SlotTersedia
from community.models import Community
import json
import base64
from django.core.files.base import ContentFile


# ============================================================
# HELPER: Check if user is PEMILIK
# ============================================================
def check_pemilik_permission(request):
    """Helper untuk cek apakah user adalah PEMILIK"""
    if not request.user.is_authenticated:
        return False, JsonResponse({
            'status': 'error',
            'message': 'Anda harus login terlebih dahulu'
        }, status=401)
    
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'PEMILIK':
        return False, JsonResponse({
            'status': 'error',
            'message': 'Hanya PEMILIK yang dapat mengakses endpoint ini'
        }, status=403)
    
    return True, None


# ============================================================
# API 1: Admin Login
# ============================================================
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
        data = json.loads(request.body)
        username = data.get('username', '').strip()
        password = data.get('password', '')
        
        if not username or not password:
            return JsonResponse({
                'status': False,
                'message': 'Username dan password harus diisi'
            }, status=400)
        
        user = authenticate(request, username=username, password=password)
        
        if user is None:
            return JsonResponse({
                'status': False,
                'message': 'Username atau password salah'
            }, status=401)
        
        if not hasattr(user, 'profile'):
            return JsonResponse({
                'status': False,
                'message': 'User tidak memiliki profile'
            }, status=401)
        
        if user.profile.role != 'PEMILIK':
            return JsonResponse({
                'status': False,
                'message': 'Hanya PEMILIK lapangan yang dapat login ke dashboard admin'
            }, status=403)
        
        # Set session (PENTING untuk Flutter)
        login(request, user)
        
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


# ============================================================
# API 2: Dashboard Stats
# ============================================================
@require_http_methods(["GET"])
def api_dashboard_stats(request):
    """
    GET /dashboard/api/dashboard/stats/
    
    Response Success (200):
    {
        "status": "success",
        "data": {
            "total_lapangan": 5,
            "pending_bookings": 3,
            "total_komunitas": 2
        }
    }
    """
    is_pemilik, error_response = check_pemilik_permission(request)
    if not is_pemilik:
        return error_response
    
    try:
        total_lapangan = Lapangan.objects.filter(
            pengelola=request.user.profile,
            is_active=True
        ).count()
        
        pending_bookings = Booking.objects.filter(
            slot__lapangan__pengelola=request.user.profile,
            status_pembayaran='PENDING'
        ).count()
        
        total_komunitas = Community.objects.filter(
            created_by=request.user
        ).count()
        
        return JsonResponse({
            'status': 'success',
            'data': {
                'total_lapangan': total_lapangan,
                'pending_bookings': pending_bookings,
                'total_komunitas': total_komunitas,
            }
        }, status=200)
    
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)


# ============================================================
# API 3: Get Pending Bookings
# ============================================================
@require_http_methods(["GET"])
def api_pending_bookings(request):
    """
    GET /dashboard/api/booking/pending/
    """
    is_pemilik, error_response = check_pemilik_permission(request)
    if not is_pemilik:
        return error_response
    
    try:
        pending_bookings = Booking.objects.filter(
            slot__lapangan__pengelola=request.user.profile,
            status_pembayaran='PENDING'
        ).select_related(
            'user',
            'slot',
            'slot__lapangan'
        ).order_by('-tanggal_booking')
        
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
            'message': str(e)
        }, status=500)


# ============================================================
# API 4: Approve Booking
# ============================================================
@csrf_exempt
@require_http_methods(["POST"])
def api_approve_booking(request, booking_id):
    """
    POST /dashboard/api/booking/{id}/approve/
    """
    is_pemilik, error_response = check_pemilik_permission(request)
    if not is_pemilik:
        return error_response
    
    try:
        booking = get_object_or_404(
            Booking,
            pk=booking_id,
            slot__lapangan__pengelola=request.user.profile
        )
        
        if booking.status_pembayaran != 'PENDING':
            return JsonResponse({
                'status': 'error',
                'message': 'Booking ini sudah diproses'
            }, status=400)
        
        booking.status_pembayaran = 'PAID'
        booking.save()
        
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
            'message': str(e)
        }, status=500)


# ============================================================
# API 5: Reject Booking
# ============================================================
@csrf_exempt
@require_http_methods(["POST"])
def api_reject_booking(request, booking_id):
    """
    POST /dashboard/api/booking/{id}/reject/
    """
    is_pemilik, error_response = check_pemilik_permission(request)
    if not is_pemilik:
        return error_response
    
    try:
        booking = get_object_or_404(
            Booking,
            pk=booking_id,
            slot__lapangan__pengelola=request.user.profile
        )
        
        if booking.status_pembayaran != 'PENDING':
            return JsonResponse({
                'status': 'error',
                'message': 'Booking ini sudah diproses'
            }, status=400)
        
        booking.status_pembayaran = 'CANCELLED'
        booking.save()
        
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
            'message': str(e)
        }, status=500)


# ============================================================
# API 6: Get Lapangan List (Admin)
# ============================================================
@require_http_methods(["GET"])
def api_lapangan_list(request):
    """
    GET /dashboard/api/lapangan/list/
    """
    is_pemilik, error_response = check_pemilik_permission(request)
    if not is_pemilik:
        return error_response
    
    try:
        lapangan_list = Lapangan.objects.filter(
            pengelola=request.user.profile,
            is_active=True
        ).order_by('nama_lapangan')
        
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
                'foto_utama': request.build_absolute_uri(lapangan.foto_utama.url) if lapangan.foto_utama else None,
                'foto_2': request.build_absolute_uri(lapangan.foto_2.url) if lapangan.foto_2 else None,
                'foto_3': request.build_absolute_uri(lapangan.foto_3.url) if lapangan.foto_3 else None,
            })
        
        return JsonResponse({
            'status': 'success',
            'data': data
        }, status=200)
    
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)


# ============================================================
# API 7: Create Lapangan (NEW)
# ============================================================
@csrf_exempt
@require_http_methods(["POST"])
def api_lapangan_create(request):
    """
    POST /dashboard/api/lapangan/create/
    
    Request Body (JSON):
    {
        "nama_lapangan": "string",
        "jenis_olahraga": "Futsal|Basket|Bulutangkis",
        "lokasi": "string",
        "harga_per_jam": int,
        "fasilitas": "string",
        "deskripsi": "string",
        "foto_utama": "base64_string", // optional
        "foto_2": "base64_string",      // optional
        "foto_3": "base64_string"       // optional
    }
    """
    is_pemilik, error_response = check_pemilik_permission(request)
    if not is_pemilik:
        return error_response
    
    try:
        data = json.loads(request.body)
        
        # Validasi field wajib
        required_fields = ['nama_lapangan', 'jenis_olahraga', 'lokasi', 'harga_per_jam']
        for field in required_fields:
            if not data.get(field):
                return JsonResponse({
                    'status': 'error',
                    'message': f'Field {field} wajib diisi'
                }, status=400)
        
        # Buat lapangan
        lapangan = Lapangan.objects.create(
            nama_lapangan=data['nama_lapangan'],
            jenis_olahraga=data['jenis_olahraga'],
            lokasi=data['lokasi'],
            harga_per_jam=data['harga_per_jam'],
            fasilitas=data.get('fasilitas', ''),
            deskripsi=data.get('deskripsi', ''),
            pengelola=request.user.profile
        )
        
        # Handle foto upload (base64)
        for foto_field in ['foto_utama', 'foto_2', 'foto_3']:
            foto_base64 = data.get(foto_field)
            if foto_base64:
                try:
                    # Decode base64
                    foto_data = base64.b64decode(foto_base64)
                    foto_file = ContentFile(foto_data, name=f'{foto_field}_{lapangan.id}.jpg')
                    setattr(lapangan, foto_field, foto_file)
                except Exception as e:
                    print(f"Error decoding {foto_field}: {e}")
        
        lapangan.save()
        
        return JsonResponse({
            'status': 'success',
            'message': 'Lapangan berhasil dibuat',
            'data': {
                'id': lapangan.id,
                'nama_lapangan': lapangan.nama_lapangan
            }
        }, status=201)
    
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)


# ============================================================
# API 8: Update Lapangan (NEW)
# ============================================================
@csrf_exempt
@require_http_methods(["POST"])
def api_lapangan_update(request, lapangan_id):
    """
    POST /dashboard/api/lapangan/{id}/update/
    """
    is_pemilik, error_response = check_pemilik_permission(request)
    if not is_pemilik:
        return error_response
    
    try:
        lapangan = get_object_or_404(
            Lapangan,
            pk=lapangan_id,
            pengelola=request.user.profile
        )
        
        data = json.loads(request.body)
        
        # Update fields
        lapangan.nama_lapangan = data.get('nama_lapangan', lapangan.nama_lapangan)
        lapangan.jenis_olahraga = data.get('jenis_olahraga', lapangan.jenis_olahraga)
        lapangan.lokasi = data.get('lokasi', lapangan.lokasi)
        lapangan.harga_per_jam = data.get('harga_per_jam', lapangan.harga_per_jam)
        lapangan.fasilitas = data.get('fasilitas', lapangan.fasilitas)
        lapangan.deskripsi = data.get('deskripsi', lapangan.deskripsi)
        
        # Handle foto update
        for foto_field in ['foto_utama', 'foto_2', 'foto_3']:
            foto_base64 = data.get(foto_field)
            if foto_base64:
                try:
                    foto_data = base64.b64decode(foto_base64)
                    foto_file = ContentFile(foto_data, name=f'{foto_field}_{lapangan.id}.jpg')
                    setattr(lapangan, foto_field, foto_file)
                except Exception as e:
                    print(f"Error decoding {foto_field}: {e}")
        
        lapangan.save()
        
        return JsonResponse({
            'status': 'success',
            'message': 'Lapangan berhasil diupdate'
        }, status=200)
    
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)


# ============================================================
# API 9: Delete Lapangan (NEW)
# ============================================================
@csrf_exempt
@require_http_methods(["POST"])
def api_lapangan_delete(request, lapangan_id):
    """
    POST /dashboard/api/lapangan/{id}/delete/
    """
    is_pemilik, error_response = check_pemilik_permission(request)
    if not is_pemilik:
        return error_response
    
    try:
        lapangan = get_object_or_404(
            Lapangan,
            pk=lapangan_id,
            pengelola=request.user.profile
        )
        
        # Cek apakah ada booking aktif
        active_bookings = Booking.objects.filter(
            slot__lapangan=lapangan,
            status_pembayaran__in=['PENDING', 'PAID']
        ).exists()
        
        if active_bookings:
            return JsonResponse({
                'status': 'error',
                'message': 'Tidak dapat menghapus lapangan yang masih memiliki booking aktif'
            }, status=400)
        
        lapangan.is_active = False  # Soft delete
        lapangan.save()
        
        return JsonResponse({
            'status': 'success',
            'message': 'Lapangan berhasil dihapus'
        }, status=200)
    
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)


# ============================================================
# API 10: Get Lapangan Detail (NEW)
# ============================================================
@require_http_methods(["GET"])
def api_lapangan_detail(request, lapangan_id):
    """
    GET /dashboard/api/lapangan/{id}/detail/
    """
    is_pemilik, error_response = check_pemilik_permission(request)
    if not is_pemilik:
        return error_response
    
    try:
        lapangan = get_object_or_404(
            Lapangan,
            pk=lapangan_id,
            pengelola=request.user.profile
        )
        
        data = {
            'id': lapangan.id,
            'nama_lapangan': lapangan.nama_lapangan,
            'jenis_olahraga': lapangan.jenis_olahraga,
            'lokasi': lapangan.lokasi,
            'harga_per_jam': float(lapangan.harga_per_jam),
            'fasilitas': lapangan.fasilitas,
            'deskripsi': lapangan.deskripsi,
            'rating': float(lapangan.rating),
            'jumlah_ulasan': lapangan.jumlah_ulasan,
            'foto_utama': request.build_absolute_uri(lapangan.foto_utama.url) if lapangan.foto_utama else None,
            'foto_2': request.build_absolute_uri(lapangan.foto_2.url) if lapangan.foto_2 else None,
            'foto_3': request.build_absolute_uri(lapangan.foto_3.url) if lapangan.foto_3 else None,
        }
        
        return JsonResponse({
            'status': 'success',
            'data': data
        }, status=200)
    
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)