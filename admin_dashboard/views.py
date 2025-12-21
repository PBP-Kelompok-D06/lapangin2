from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count, Q
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods  
from django.views.decorators.csrf import csrf_protect  
from django.core.exceptions import PermissionDenied  
from django.templatetags.static import static
from django.contrib.staticfiles.finders import find
import os
from django.core.paginator import Paginator
import base64


# Import dari BOOKING models (bukan admin_dashboard models)
from booking.models import Booking, SlotTersedia, Lapangan
from community.models import Community, CommunityRequest 
from datetime import date, time, timedelta

from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import authenticate
import json

# Decorator untuk cek role PEMILIK
def is_pemilik(user):
    """Cek apakah user adalah PEMILIK lapangan"""
    return hasattr(user, 'profile') and user.profile.role == 'PEMILIK'

# Decorator gabungan
def pemilik_required(view_func):
    """Decorator untuk memastikan user adalah PEMILIK"""
    from django.contrib.auth.decorators import user_passes_test
    decorated_view = login_required(user_passes_test(is_pemilik, login_url='/accounts/login/')(view_func))
    return decorated_view


# ==================== HELPER FUNCTION ====================
def get_pending_bookings_count(user):
    """Helper function untuk menghitung pending bookings"""
    if hasattr(user, 'profile') and user.profile.role == 'PEMILIK':
        return Booking.objects.filter(
            slot__lapangan__pengelola=user.profile,
            status_pembayaran='PENDING'
        ).count()
    return 0


# ==================== DASHBOARD HOME ====================
@pemilik_required
def dashboard_home(request):
    """Halaman utama dashboard dengan overview"""
    # Hitung total lapangan milik pemilik ini
    total_lapangan = Lapangan.objects.filter(pengelola=request.user.profile).count()
    
    # Hitung total komunitas yang dibuat
    total_komunitas = Community.objects.filter(created_by=request.user).count()
    
    # Hitung booking pending untuk lapangan milik pemilik ini
    pending_bookings = get_pending_bookings_count(request.user)
    
    context = {
        'total_lapangan': total_lapangan,
        'total_komunitas': total_komunitas,
        'pending_requests': CommunityRequest.objects.filter(status='pending').count(), 
        'pending_bookings': pending_bookings,
    }
    return render(request, 'admin_dashboard/dashboard_home.html', context)


# ==================== LAPANGAN MANAGEMENT ====================
@pemilik_required
def lapangan_list(request):
    """Menampilkan daftar semua lapangan milik pemilik"""
    jenis_filter = request.GET.get('jenis', '')
    lokasi_filter = request.GET.get('lokasi', '')

    # Filter hanya lapangan milik pemilik yang login dan urutkan berdasarkan PK
    lapangan_queryset = Lapangan.objects.filter(pengelola=request.user.profile, is_active=True).order_by('pk')

    if jenis_filter:
        lapangan_queryset = lapangan_queryset.filter(jenis_olahraga=jenis_filter)
    if lokasi_filter:
        lapangan_queryset = lapangan_queryset.filter(lokasi__icontains=lokasi_filter)

    # === HANDLE MOBILE / JSON RESPONSE ===
    # Cek header Accept atau parameter format=json untuk mendeteksi request dari Flutter/API
    if request.headers.get('Accept') == 'application/json' or request.GET.get('format') == 'json':
        data = []
        for lap in lapangan_queryset:
            # Cari gambar statis (Logic sama dengan view asli)
            possible_static_path_png = f'images/lapangan{lap.pk}.png'
            possible_static_path_jpg = f'images/lapangan{lap.pk}.jpg'
            static_image_path = None
            if find(possible_static_path_png):
                 static_image_path = static(possible_static_path_png)
            elif find(possible_static_path_jpg):
                 static_image_path = static(possible_static_path_jpg)

            # Prioritas URL gambar: Uploaded Image -> Static Image -> Default/Empty
            final_image_url = ""
            if lap.foto_utama:
                final_image_url = lap.foto_utama.url
            elif static_image_path:
                final_image_url = static_image_path
            
            data.append({
                'pk': lap.pk,
                'nama': lap.nama_lapangan,
                'jenis': lap.jenis_olahraga,
                'lokasi': lap.lokasi,
                'harga': lap.harga_per_jam,
                'deskripsi': lap.deskripsi,
                'fasilitas': lap.fasilitas,
                'image_url': final_image_url
            })
        return JsonResponse({'status': True, 'data': data})

    # === HTML RESPONSE (WEB) ===
    # Siapkan list lapangan untuk ditambahkan path gambar statis
    lapangan_list_with_static = []
    for lapangan in lapangan_queryset:
        possible_static_path_png = f'images/lapangan{lapangan.pk}.png'
        possible_static_path_jpg = f'images/lapangan{lapangan.pk}.jpg'
        
        found_static_path = None
        if find(possible_static_path_png): 
             found_static_path = possible_static_path_png
        elif find(possible_static_path_jpg):
             found_static_path = possible_static_path_jpg
             
        # Tambahkan path yang ditemukan (atau None) ke objek
        lapangan.static_image_path = found_static_path 
        lapangan_list_with_static.append(lapangan)

    # --- Bagian Paginator (Jika Anda ingin menambahkannya) ---
    items_per_page = 16 
    paginator = Paginator(lapangan_list_with_static, items_per_page)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    # --------------------------------------------------------

    jenis_choices = [
        ('Futsal', 'Futsal'),
        ('Bulutangkis', 'Bulutangkis'),
        ('Basket', 'Basket'),
    ]

    context = {
        'lapangan_list': lapangan_list_with_static, 
        'jenis_choices': jenis_choices,
        'pending_bookings': get_pending_bookings_count(request.user),
    }
    return render(request, 'admin_dashboard/lapangan_list.html', context)
    


@csrf_exempt
def lapangan_create(request):
    """Form untuk membuat lapangan baru (Hybrid Request: Web & Mobile/JSON)"""
    
    # Deteksi request Mobile/JSON
    is_mobile_api = request.content_type == 'application/json' or request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.GET.get('format') == 'json'

    # 1. Manual Auth Check
    if not request.user.is_authenticated:
        if is_mobile_api:
             return JsonResponse({'status': False, 'message': 'Authentication required'}, status=401)
        return redirect('login') 

    # 2. Manual Role Check
    if not is_pemilik(request.user):
        if is_mobile_api:
             return JsonResponse({'status': False, 'message': 'Unauthorized. Role is not PEMILIK.'}, status=403)
        return redirect('dashboard_home')

    if request.method == 'POST':
        try:
            data = {}
            if request.content_type == 'application/json':
                data = json.loads(request.body)
            else:
                data = request.POST

            nama = data.get('nama', '').strip()
            jenis = data.get('jenis', '').strip()
            lokasi = data.get('lokasi', '').strip()
            harga = str(data.get('harga', '')).strip() 
            
            if not all([nama, jenis, lokasi, harga]):
                error_msg = 'Semua field wajib diisi!'
                if is_mobile_api:
                    return JsonResponse({'status': False, 'message': error_msg}, status=400)
                messages.error(request, error_msg)
                return redirect('admin_dashboard:lapangan_create')
            
            try:
                harga_int = int(harga)
                if harga_int <= 0:
                    raise ValueError
            except ValueError:
                error_msg = 'Harga harus berupa angka positif!'
                if is_mobile_api:
                     return JsonResponse({'status': False, 'message': error_msg}, status=400)
                messages.error(request, error_msg)
                return redirect('admin_dashboard:lapangan_create')
            
            valid_jenis = ['Futsal', 'Bulutangkis', 'Basket']
            if jenis not in valid_jenis:
                error_msg = 'Jenis olahraga tidak valid!'
                if is_mobile_api:
                     return JsonResponse({'status': False, 'message': error_msg}, status=400)
                messages.error(request, error_msg)
                return redirect('admin_dashboard:lapangan_create')
            
            lapangan = Lapangan.objects.create(
                nama_lapangan=nama,
                jenis_olahraga=jenis,
                lokasi=lokasi,
                harga_per_jam=harga_int,
                deskripsi=data.get('deskripsi', '').strip(),
                fasilitas=data.get('fasilitas', '').strip(),
                pengelola=request.user.profile
            )

            # Helper: Handle Image
            def handle_image(files_key, json_key, target_field_name):
                if request.FILES.get(files_key):
                    file_obj = request.FILES.get(files_key)
                    if not is_mobile_api:
                         if file_obj.size > 5 * 1024 * 1024: raise ValueError(f"Ukuran {files_key} max 5MB")
                         if file_obj.content_type not in ['image/jpeg', 'image/jpg', 'image/png']: raise ValueError(f"Format {files_key} harus JPG/PNG")
                    setattr(lapangan, target_field_name, file_obj)
                elif data.get(json_key):
                    image_data = data.get(json_key)
                    try:
                        if ";base64," in image_data:
                            format, imgstr = image_data.split(';base64,') 
                            ext = format.split('/')[-1] 
                        else:
                            imgstr = image_data
                            ext = "jpg"
                        file_name = f"{request.user.username}_{uuid.uuid4()}.{ext}"
                        data_img = ContentFile(base64.b64decode(imgstr), name=file_name)
                        setattr(lapangan, target_field_name, data_img)
                    except Exception as e:
                        print(f"Error decoding {json_key}: {e}") 
            
            try:
                handle_image('foto_utama', 'foto_utama', 'foto_utama')
                handle_image('foto_2', 'foto_2', 'foto_2')
                handle_image('foto_3', 'foto_3', 'foto_3')
            except ValueError as ve:
                 lapangan.delete() 
                 if is_mobile_api: return JsonResponse({'status': False, 'message': str(ve)}, status=400)
                 messages.error(request, str(ve))
                 return redirect('admin_dashboard:lapangan_create')

            lapangan.save()
            
            if is_mobile_api:
                return JsonResponse({'status': True, 'message': 'Lapangan berhasil ditambahkan!', 'pk': lapangan.pk})
            
            messages.success(request, 'Lapangan berhasil ditambahkan!')
            return redirect('admin_dashboard:lapangan_list')
            
        except Exception as e:
            if is_mobile_api:
                 return JsonResponse({'status': False, 'message': str(e)}, status=500)
            messages.error(request, f'Terjadi kesalahan: {str(e)}')
            return redirect('admin_dashboard:lapangan_create')
    
    if is_mobile_api:
         return JsonResponse({'status': False, 'message': 'Method not allowed'}, status=405)

    jenis_choices = [
        ('Futsal', 'Futsal'),
        ('Bulutangkis', 'Bulutangkis'),
        ('Basket', 'Basket'),
    ]
    
    context = {
        'jenis_choices': jenis_choices,
        'pending_bookings': get_pending_bookings_count(request.user),
    }
    return render(request, 'admin_dashboard/lapangan_form.html', context)


@csrf_exempt
def lapangan_edit(request, pk):
    """Edit lapangan yang sudah ada (Hybrid Request)"""
    
    is_mobile_api = request.content_type == 'application/json' or request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.GET.get('format') == 'json'

    # 1. Auth Check
    if not request.user.is_authenticated:
        if is_mobile_api: return JsonResponse({'status': False, 'message': 'Authentication required'}, status=401)
        return redirect('login')
    
    # 2. Role Check
    if not is_pemilik(request.user):
        if is_mobile_api: return JsonResponse({'status': False, 'message': 'Unauthorized'}, status=403)
        return redirect('dashboard_home')
    
    lapangan = get_object_or_404(Lapangan, pk=pk, pengelola=request.user.profile)

    if request.method == 'POST':
        try:
            nama = request.POST.get('nama', '').strip()
            jenis = request.POST.get('jenis', '').strip()
            lokasi = request.POST.get('lokasi', '').strip()
            harga = request.POST.get('harga', '').strip()

            if not all([nama, jenis, lokasi, harga]):
                messages.error(request, 'Semua field wajib diisi!')
                return render(request, 'admin_dashboard/lapangan_form.html', {
                    'lapangan': lapangan,
                    'jenis_choices': [('Futsal', 'Futsal'), ('Bulutangkis', 'Bulutangkis'), ('Basket', 'Basket')],
                    'pending_bookings': get_pending_bookings_count(request.user),
                })
            
            try:
                harga_int = int(harga)
                if harga_int <= 0: raise ValueError
            except ValueError:
                error_msg = 'Harga harus berupa angka positif!'
                if is_mobile_api: return JsonResponse({'status': False, 'message': error_msg}, status=400)
                messages.error(request, error_msg)
                return render(request, 'admin_dashboard/lapangan_form.html', {
                    'lapangan': lapangan,
                    'jenis_choices': [('Futsal', 'Futsal'), ('Bulutangkis', 'Bulutangkis'), ('Basket', 'Basket')],
                    'pending_bookings': get_pending_bookings_count(request.user),
                })

            valid_jenis = ['Futsal', 'Bulutangkis', 'Basket']
            if jenis not in valid_jenis:
                 if is_mobile_api: return JsonResponse({'status': False, 'message': 'Jenis tidak valid'}, status=400)
                 messages.error(request, 'Jenis tidak valid!')
                 return render(request, 'admin_dashboard/lapangan_form.html', {
                    'lapangan': lapangan,
                    'jenis_choices': [('Futsal', 'Futsal'), ('Bulutangkis', 'Bulutangkis'), ('Basket', 'Basket')],
                    'pending_bookings': get_pending_bookings_count(request.user),
                })
            
            # Update Fields
            lapangan.nama_lapangan = nama
            lapangan.jenis_olahraga = jenis
            lapangan.lokasi = lokasi
            lapangan.harga_per_jam = harga_int
            lapangan.deskripsi = data.get('deskripsi', lapangan.deskripsi).strip()
            lapangan.fasilitas = data.get('fasilitas', lapangan.fasilitas).strip()

            # Helper Image
            def update_image(files_key, json_key, target_field_name):
                if request.FILES.get(files_key):
                    file_obj = request.FILES.get(files_key)
                    if not is_mobile_api: # Web Validation
                         if file_obj.size > 5 * 1024 * 1024: raise ValueError(f"Ukuran {files_key} max 5MB")
                         if file_obj.content_type not in ['image/jpeg', 'image/jpg', 'image/png']: raise ValueError(f"Format {files_key} salah")
                    setattr(lapangan, target_field_name, file_obj)
                
                elif data.get(json_key): # JSON Base64
                    image_data = data.get(json_key)
                    try:
                        if ";base64," in image_data:
                            format, imgstr = image_data.split(';base64,') 
                            ext = format.split('/')[-1] 
                        else:
                            imgstr = image_data
                            ext = "jpg"
                        file_name = f"{request.user.username}_{uuid.uuid4()}.{ext}"
                        data_img = ContentFile(base64.b64decode(imgstr), name=file_name)
                        setattr(lapangan, target_field_name, data_img)
                    except Exception as e:
                        print(f"Error update {json_key}: {e}")

            try:
                update_image('foto_utama', 'foto_utama', 'foto_utama')
                update_image('foto_2', 'foto_2', 'foto_2')
                update_image('foto_3', 'foto_3', 'foto_3')
            except ValueError as ve:
                if is_mobile_api: return JsonResponse({'status': False, 'message': str(ve)}, status=400)
                messages.error(request, str(ve))
                return render(request, 'admin_dashboard/lapangan_form.html', {
                    'lapangan': lapangan,
                    'jenis_choices': [('Futsal', 'Futsal'), ('Bulutangkis', 'Bulutangkis'), ('Basket', 'Basket')],
                    'pending_bookings': get_pending_bookings_count(request.user),
                })

            lapangan.save()
            
            if is_mobile_api:
                return JsonResponse({'status': True, 'message': 'Lapangan berhasil diupdate!'})

            messages.success(request, 'Lapangan berhasil diupdate!')
            return redirect('admin_dashboard:lapangan_list')
            
        except Exception as e:
            if is_mobile_api: return JsonResponse({'status': False, 'message': str(e)}, status=500)
            messages.error(request, f'Terjadi kesalahan: {str(e)}')
            # Fallback render
    
    # GET Request
    if is_mobile_api: return JsonResponse({'status': False, 'message': 'Method not allowed'}, status=405)

    jenis_choices = [
        ('Futsal', 'Futsal'),
        ('Bulutangkis', 'Bulutangkis'),
        ('Basket', 'Basket'),
    ]
    
    context = {
        'lapangan': lapangan,
        'jenis_choices': jenis_choices,
        'pending_bookings': get_pending_bookings_count(request.user),
    }
    return render(request, 'admin_dashboard/lapangan_form.html', context)


@csrf_exempt
def lapangan_delete(request, pk):
    """Hapus lapangan (Hybrid Request)"""
    
    is_mobile_api = request.content_type == 'application/json' or request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.GET.get('format') == 'json'

    # 1. Auth Check
    if not request.user.is_authenticated:
        if is_mobile_api: return JsonResponse({'status': False, 'message': 'Authentication required'}, status=401)
        return redirect('login')
    
    # 2. Role Check
    if not is_pemilik(request.user):
        if is_mobile_api: return JsonResponse({'status': False, 'message': 'Unauthorized'}, status=403)
        return redirect('dashboard_home')
    
    lapangan = get_object_or_404(Lapangan, pk=pk, pengelola=request.user.profile)
    
    if request.method == 'POST':
        active_bookings = Booking.objects.filter(
            slot__lapangan=lapangan,
            status_pembayaran__in=['PENDING', 'PAID']
        ).exists()
        
        if active_bookings:
            error_msg = 'Tidak dapat menghapus lapangan yang masih memiliki booking aktif!'
            if is_mobile_api: return JsonResponse({'status': False, 'message': error_msg}, status=400)
            messages.error(request, error_msg)
            return redirect('admin_dashboard:lapangan_list')
        
        lapangan.is_active = False # Soft delete
        lapangan.save()
        if is_mobile_api: return JsonResponse({'status': True, 'message': 'Lapangan berhasil dihapus!'})
        
        messages.success(request, 'Lapangan berhasil dihapus!')
        return redirect('admin_dashboard:lapangan_list')
    
    # GET Request (Web only for confirmation page)
    if is_mobile_api: return JsonResponse({'status': False, 'message': 'Method not allowed. Use POST to delete.'}, status=405)

    context = {
        'lapangan': lapangan,
        'pending_bookings': get_pending_bookings_count(request.user),
    }
    return render(request, 'admin_dashboard/lapangan_confirm_delete.html', context)


# ==================== BOOKING MANAGEMENT ====================
def booking_pending_list(request):
    """Menampilkan daftar booking PENDING untuk di-approve/reject (Hybrid)"""
    
    is_mobile_api = request.content_type == 'application/json' or request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.GET.get('format') == 'json'

    # 1. Auth Check
    if not request.user.is_authenticated:
        if is_mobile_api: return JsonResponse({'status': False, 'message': 'Authentication required'}, status=401)
        return redirect('login')
    
    # 2. Role Check
    if not is_pemilik(request.user):
        if is_mobile_api: return JsonResponse({'status': False, 'message': 'Unauthorized'}, status=403)
        return redirect('dashboard_home')

    # Filter booking PENDING untuk lapangan milik pemilik yang login
    pending_bookings = Booking.objects.filter(
        slot__lapangan__pengelola=request.user.profile,
        status_pembayaran='PENDING'
    ).select_related('user', 'slot', 'slot__lapangan').order_by('-tanggal_booking')
    
    # === JSON RESPONSE ===
    if is_mobile_api:
        data = []
        for b in pending_bookings:
            data.append({
                'id': b.id,
                'user': b.user.username,
                'lapangan': b.slot.lapangan.nama_lapangan,
                'tanggal': b.slot.tanggal.strftime('%Y-%m-%d'),
                'jam': f"{b.slot.jam_mulai.strftime('%H:%M')} - {b.slot.jam_akhir.strftime('%H:%M')}",
                'total_bayar': b.total_bayar,
                'bukti_transfer': b.bukti_transfer.url if b.bukti_transfer else None,
                'tanggal_booking': b.tanggal_booking.strftime('%Y-%m-%d %H:%M')
            })
        return JsonResponse({'status': True, 'data': data})

    context = {
        'pending_bookings': pending_bookings,
    }
    return render(request, 'admin_dashboard/booking_pending_list.html', context)


@csrf_exempt
def booking_approve(request, pk):
    """Approve booking (PENDING → PAID, slot jadi BOOKED) (Hybrid)"""
    
    is_mobile_api = request.content_type == 'application/json' or request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.GET.get('format') == 'json'

    # Auth & Role Check
    if not request.user.is_authenticated:
        if is_mobile_api: return JsonResponse({'status': False, 'message': 'Authentication required'}, status=401)
        return redirect('login')
    if not is_pemilik(request.user):
        if is_mobile_api: return JsonResponse({'status': False, 'message': 'Unauthorized'}, status=403)
        return redirect('dashboard_home')

    booking = get_object_or_404(
        Booking, 
        pk=pk, 
        slot__lapangan__pengelola=request.user.profile,
        status_pembayaran='PENDING'
    )
    
    if request.method == 'POST':
        try:
            if booking.status_pembayaran != 'PENDING':
                msg = 'Booking ini sudah diproses!'
                if is_mobile_api: return JsonResponse({'status': False, 'message': msg}, status=400)
                messages.error(request, msg)
                return redirect('admin_dashboard:booking_pending')
            
            # Update status booking jadi PAID
            booking.status_pembayaran = 'PAID'
            booking.save()
            
            # Update slot jadi BOOKED (is_available = False)
            slot = booking.slot
            slot.is_available = False
            slot.pending_booking = None  # Clear pending
            slot.save()
            
            if is_mobile_api: return JsonResponse({'status': True, 'message': 'Booking approved successfully'})

            messages.success(request, f'Booking #{booking.id} berhasil di-approve!')
            return redirect('admin_dashboard:booking_pending')
            
        except Exception as e:
            if is_mobile_api: return JsonResponse({'status': False, 'message': str(e)}, status=500)
            messages.error(request, f'Terjadi kesalahan: {str(e)}')
            return redirect('admin_dashboard:booking_pending')
    
    # GET Request
    if is_mobile_api: return JsonResponse({'status': False, 'message': 'Method not allowed'}, status=405)

    context = {
        'booking': booking,
        'pending_bookings': get_pending_bookings_count(request.user),
    }
    return render(request, 'admin_dashboard/booking_approve_confirm.html', context)


@csrf_exempt
def booking_reject(request, pk):
    """Reject booking (PENDING → CANCELLED, slot jadi AVAILABLE) (Hybrid)"""
    
    is_mobile_api = request.content_type == 'application/json' or request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.GET.get('format') == 'json'

    # Auth & Role Check
    if not request.user.is_authenticated:
        if is_mobile_api: return JsonResponse({'status': False, 'message': 'Authentication required'}, status=401)
        return redirect('login')
    if not is_pemilik(request.user):
        if is_mobile_api: return JsonResponse({'status': False, 'message': 'Unauthorized'}, status=403)
        return redirect('dashboard_home')

    booking = get_object_or_404(
        Booking, 
        pk=pk, 
        slot__lapangan__pengelola=request.user.profile,
        status_pembayaran='PENDING'
    )
    
    if request.method == 'POST':
        try:
            if booking.status_pembayaran != 'PENDING':
                msg = 'Booking ini sudah diproses!'
                if is_mobile_api: return JsonResponse({'status': False, 'message': msg}, status=400)
                messages.error(request, msg)
                return redirect('admin_dashboard:booking_pending')
            
            # Update status booking jadi CANCELLED
            booking.status_pembayaran = 'CANCELLED'
            booking.save()
            
            # Update slot jadi AVAILABLE lagi
            slot = booking.slot
            slot.is_available = True
            slot.pending_booking = None  # Clear pending
            slot.save()
            
            if is_mobile_api: return JsonResponse({'status': True, 'message': 'Booking rejected successfully'})

            messages.success(request, f'Booking #{booking.id} berhasil ditolak!')
            return redirect('admin_dashboard:booking_pending')
            
        except Exception as e:
            if is_mobile_api: return JsonResponse({'status': False, 'message': str(e)}, status=500)
            messages.error(request, f'Terjadi kesalahan: {str(e)}')
            return redirect('admin_dashboard:booking_pending')
    
    # GET Request
    if is_mobile_api: return JsonResponse({'status': False, 'message': 'Method not allowed'}, status=405)

    context = {
        'booking': booking,
        'pending_bookings': get_pending_bookings_count(request.user),
    }
    return render(request, 'admin_dashboard/booking_reject_confirm.html', context)


def transaksi_list(request):
    """Menampilkan daftar transaksi (PAID/CANCELLED) (Hybrid)"""
    
    is_mobile_api = request.content_type == 'application/json' or request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.GET.get('format') == 'json'

    # Auth & Role Check
    if not request.user.is_authenticated:
        if is_mobile_api: return JsonResponse({'status': False, 'message': 'Authentication required'}, status=401)
        return redirect('login')
    if not is_pemilik(request.user):
        if is_mobile_api: return JsonResponse({'status': False, 'message': 'Unauthorized'}, status=403)
        return redirect('dashboard_home')

    status_filter = request.GET.get('status', '')

    # 1. Dapatkan SEMUA transaksi yang relevan (Filter by OWNER!)
    all_transactions_base = Booking.objects.filter(
        status_pembayaran__in=['PAID', 'CANCELLED'],
        slot__lapangan__pengelola=request.user.profile # Fix: Scope to owner
    )

    # 2. Hitung jumlah untuk kartu summary SEBELUM memfilter untuk tabel
    paid_count = all_transactions_base.filter(status_pembayaran='PAID').count()
    cancelled_count = all_transactions_base.filter(status_pembayaran='CANCELLED').count()

    # 3. Filter daftar untuk ditampilkan
    table_transactions = all_transactions_base
    if status_filter:
        table_transactions = table_transactions.filter(status_pembayaran=status_filter)
    
    table_transactions = table_transactions.order_by('-tanggal_booking')

    # === JSON RESPONSE ===
    if is_mobile_api:
        data = []
        for t in table_transactions:
            data.append({
                'id': t.id,
                'user': t.user.username,
                'lapangan': t.slot.lapangan.nama_lapangan,
                'tanggal': t.slot.tanggal.strftime('%Y-%m-%d'),
                'jam': f"{t.slot.jam_mulai.strftime('%H:%M')} - {t.slot.jam_akhir.strftime('%H:%M')}",
                'total_bayar': t.total_bayar,
                'status': t.status_pembayaran,
                'tanggal_booking': t.tanggal_booking.strftime('%Y-%m-%d %H:%M')
            })
        return JsonResponse({
            'status': True, 
            'data': data,
            'summary': {
                'paid': paid_count,
                'cancelled': cancelled_count
            }
        })

    context = {
        'transaksi': table_transactions, 
        'paid_count': paid_count,
        'cancelled_count': cancelled_count,
        'status_filter': status_filter,
    }
    
    return render(request, 'admin_dashboard/transaksi_list.html', context)


@pemilik_required
def booking_sessions_list(request):
    """Menampilkan dan mengelola booking sessions (SlotTersedia)"""
    # Filter lapangan milik pemilik yang login
    lapangan_list = Lapangan.objects.filter(pengelola=request.user.profile)
    
    # Filter berdasarkan lapangan yang dipilih
    selected_lapangan_id = request.GET.get('lapangan_id')
    selected_date_str = request.GET.get('date')
    
    # Tentukan lapangan yang dipilih
    if selected_lapangan_id:
        
        selected_lapangan = get_object_or_404(lapangan_list, pk=selected_lapangan_id)
    else:
        selected_lapangan = lapangan_list.first() if lapangan_list.exists() else None
    
    # Tentukan tanggal
    if selected_date_str:
        try:
            selected_date = date.fromisoformat(selected_date_str)
        except (ValueError, TypeError):
            selected_date = date.today()
    else:
        selected_date = date.today()
    
    # Ambil slots untuk lapangan dan tanggal yang dipilih
    slots = []
    if selected_lapangan:
        slots = SlotTersedia.objects.filter(
            lapangan=selected_lapangan,
            tanggal=selected_date
        ).order_by('jam_mulai').select_related('pending_booking')
    
    context = {
        'lapangan_list': lapangan_list,
        'selected_lapangan': selected_lapangan,
        'selected_date': selected_date,
        'selected_date_str': selected_date.strftime('%Y-%m-%d'),
        'slots': slots,
        'pending_bookings': get_pending_bookings_count(request.user),
    }
    return render(request, 'admin_dashboard/booking_sessions_list.html', context)


@pemilik_required
@require_http_methods(["GET", "POST"])  
def booking_sessions_create(request):
    """Membuat booking sessions (slots) untuk lapangan tertentu"""
    if request.method == 'POST':
        try:
            lapangan_id = request.POST.get('lapangan_id')
            start_date_str = request.POST.get('start_date')
            end_date_str = request.POST.get('end_date')
            jam_mulai_str = request.POST.get('jam_mulai')
            jam_akhir_str = request.POST.get('jam_akhir')
            
            
            lapangan = get_object_or_404(
                Lapangan, 
                pk=lapangan_id, 
                pengelola=request.user.profile
            )
            
            # Parse tanggal
            start_date = date.fromisoformat(start_date_str)
            end_date = date.fromisoformat(end_date_str)
            
            # Parse waktu
            jam_mulai = time.fromisoformat(jam_mulai_str)
            jam_akhir = time.fromisoformat(jam_akhir_str)
            
            
            if end_date < start_date:
                messages.error(request, 'Tanggal akhir tidak boleh lebih awal dari tanggal mulai!')
                return redirect('admin_dashboard:booking_sessions_create')
            
            
            if (end_date - start_date).days > 90:
                messages.error(request, 'Rentang tanggal maksimal 90 hari!')
                return redirect('admin_dashboard:booking_sessions_create')
            
            
            if jam_akhir <= jam_mulai:
                messages.error(request, 'Jam akhir harus lebih besar dari jam mulai!')
                return redirect('admin_dashboard:booking_sessions_create')
            
            
            if jam_mulai.hour < 6 or jam_akhir.hour > 23:
                messages.error(request, 'Jam operasional: 06:00 - 23:00')
                return redirect('admin_dashboard:booking_sessions_create')
            
            # Buat slots
            created_count = 0
            current_date = start_date
            
            while current_date <= end_date:
                # Cek apakah slot sudah ada
                existing = SlotTersedia.objects.filter(
                    lapangan=lapangan,
                    tanggal=current_date,
                    jam_mulai=jam_mulai
                ).exists()
                
                if not existing:
                    SlotTersedia.objects.create(
                        lapangan=lapangan,
                        tanggal=current_date,
                        jam_mulai=jam_mulai,
                        jam_akhir=jam_akhir,
                        is_available=True
                    )
                    created_count += 1
                
                current_date += timedelta(days=1)
            
            messages.success(request, f'Berhasil membuat {created_count} booking session!')
            return redirect('admin_dashboard:booking_sessions_list')
            
        except ValueError as e:
            messages.error(request, 'Format tanggal atau waktu tidak valid!')
            return redirect('admin_dashboard:booking_sessions_create')
        except Exception as e:
            messages.error(request, f'Terjadi kesalahan: {str(e)}')
            return redirect('admin_dashboard:booking_sessions_create')
    
    # GET request - tampilkan form
    lapangan_list = Lapangan.objects.filter(pengelola=request.user.profile)
    
    context = {
        'lapangan_list': lapangan_list,
        'today': date.today().strftime('%Y-%m-%d'),
        'pending_bookings': get_pending_bookings_count(request.user),
    }
    return render(request, 'admin_dashboard/booking_sessions_create.html', context)


@pemilik_required
@require_http_methods(["GET", "POST"])  
def booking_session_delete(request, pk):
    """Hapus booking session tertentu"""
    
    slot = get_object_or_404(
        SlotTersedia, 
        pk=pk, 
        lapangan__pengelola=request.user.profile
    )
    
    if request.method == 'POST':
        
        if not slot.is_available or slot.pending_booking:
            messages.error(request, 'Tidak dapat menghapus slot yang sudah dibooking!')
            return redirect('admin_dashboard:booking_sessions_list')
        
        slot.delete()
        messages.success(request, 'Booking session berhasil dihapus!')
        return redirect('admin_dashboard:booking_sessions_list')
    
    context = {
        'slot': slot,
        'pending_bookings': get_pending_bookings_count(request.user),
    }
    return render(request, 'admin_dashboard/booking_session_confirm_delete.html', context)

# ============================================================
# API 1: Admin Login
# ============================================================
@csrf_exempt
def api_admin_login(request):
    if request.method != 'POST':
        return JsonResponse({'status': False, 'message': 'Method not allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        username = data.get('username')
        password = data.get('password')
        
        user = authenticate(username=username, password=password)
        
        if user is None:
            return JsonResponse({'status': False, 'message': 'Invalid credentials'}, status=401)
        
        # Cek apakah user adalah PEMILIK
        if not hasattr(user, 'profile') or user.profile.role != 'PEMILIK':
            return JsonResponse({'status': False, 'message': 'Unauthorized. Only field owners allowed.'}, status=403)
        
        # Set session
        from django.contrib.auth import login
        login(request, user)
        
        return JsonResponse({
            'status': True,
            'message': 'Login successful',
            'data': {
                'username': user.username,
                'role': user.profile.role,
                'nomor_whatsapp': user.profile.nomor_whatsapp,
                'nomor_rekening': user.profile.nomor_rekening,
            }
        })
        
    except Exception as e:
        return JsonResponse({'status': False, 'message': str(e)}, status=500)


# ============================================================
# API 2: Dashboard Stats
# ============================================================
@pemilik_required
def api_dashboard_stats(request):
    try:
        total_lapangan = Lapangan.objects.filter(pengelola=request.user.profile).count()
        pending_bookings = Booking.objects.filter(
            slot__lapangan__pengelola=request.user.profile,
            status_pembayaran='PENDING'
        ).count()
        total_komunitas = Community.objects.filter(created_by=request.user).count()
        
        return JsonResponse({
            'status': 'success',
            'data': {
                'total_lapangan': total_lapangan,
                'pending_bookings': pending_bookings,
                'total_komunitas': total_komunitas,
            }
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


# ============================================================
# API 3: Get Pending Bookings
# ============================================================
@pemilik_required
def api_pending_bookings(request):
    try:
        bookings = Booking.objects.filter(
            slot__lapangan__pengelola=request.user.profile,
            status_pembayaran='PENDING'
        ).select_related('user', 'slot', 'slot__lapangan').order_by('-tanggal_booking')
        
        data = []
        for booking in bookings:
            data.append({
                'id': booking.id,
                'user': {
                    'username': booking.user.username,
                    'email': booking.user.email,
                },
                'lapangan': {
                    'id': booking.slot.lapangan.id,
                    'nama': booking.slot.lapangan.nama_lapangan,
                    'jenis_olahraga': booking.slot.lapangan.jenis_olahraga,
                    'lokasi': booking.slot.lapangan.lokasi,
                },
                'slot': {
                    'tanggal': booking.slot.tanggal.strftime('%Y-%m-%d'),
                    'jam_mulai': booking.slot.jam_mulai.strftime('%H:%M'),
                    'jam_akhir': booking.slot.jam_akhir.strftime('%H:%M'),
                },
                'total_bayar': float(booking.total_bayar),
                'tanggal_booking': booking.tanggal_booking.strftime('%Y-%m-%d %H:%M:%S'),
            })
        
        return JsonResponse({'status': 'success', 'data': data})
        
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


# ============================================================
# API 4: Approve Booking
# ============================================================
@csrf_exempt
@pemilik_required
def api_approve_booking(request, booking_id):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Method not allowed'}, status=405)
    
    try:
        booking = get_object_or_404(
            Booking,
            pk=booking_id,
            slot__lapangan__pengelola=request.user.profile,
            status_pembayaran='PENDING'
        )
        
        if booking.status_pembayaran != 'PENDING':
            return JsonResponse({'status': 'error', 'message': 'Booking already processed'}, status=400)
        
        booking.status_pembayaran = 'PAID'
        booking.save()
        
        slot = booking.slot
        slot.is_available = False
        slot.pending_booking = None
        slot.save()
        
        return JsonResponse({
            'status': 'success',
            'message': f'Booking #{booking.id} approved successfully'
        })
        
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


# ============================================================
# API 5: Reject Booking
# ============================================================
@csrf_exempt
@pemilik_required
def api_reject_booking(request, booking_id):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Method not allowed'}, status=405)
    
    try:
        booking = get_object_or_404(
            Booking,
            pk=booking_id,
            slot__lapangan__pengelola=request.user.profile,
            status_pembayaran='PENDING'
        )
        
        if booking.status_pembayaran != 'PENDING':
            return JsonResponse({'status': 'error', 'message': 'Booking already processed'}, status=400)
        
        booking.status_pembayaran = 'CANCELLED'
        booking.save()
        
        slot = booking.slot
        slot.is_available = True
        slot.pending_booking = None
        slot.save()
        
        return JsonResponse({
            'status': 'success',
            'message': f'Booking #{booking.id} rejected successfully'
        })
        
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


# ============================================================
# API 6: Get Lapangan List
# ============================================================
@pemilik_required
def api_lapangan_list(request):
    try:
        lapangan_list = Lapangan.objects.filter(
            pengelola=request.user.profile
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
            })
        
        return JsonResponse({'status': 'success', 'data': data})
        
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)