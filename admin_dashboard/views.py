from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count, Q
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods  # ✅ TAMBAH
from django.views.decorators.csrf import csrf_protect  # ✅ TAMBAH
from django.core.exceptions import PermissionDenied  # ✅ TAMBAH
from django.templatetags.static import static
from django.contrib.staticfiles.finders import find
import os
from django.core.paginator import Paginator


# Import dari BOOKING models (bukan admin_dashboard models)
from booking.models import Booking, SlotTersedia, Lapangan
from community.models import Community, CommunityRequest 
from datetime import date, time, timedelta

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
    lapangan_queryset = Lapangan.objects.filter(pengelola=request.user.profile).order_by('pk') # <-- Tambahkan order_by('pk')

    if jenis_filter:
        lapangan_queryset = lapangan_queryset.filter(jenis_olahraga=jenis_filter)
    if lokasi_filter:
        lapangan_queryset = lapangan_queryset.filter(lokasi__icontains=lokasi_filter)

    # Siapkan list lapangan untuk ditambahkan path gambar statis
    lapangan_list_with_static = []
    for lapangan in lapangan_queryset:
        # ASUMSI: Mencoba mencari gambar statis bernama 'images/lapangan<id>.png' atau 'images/lapangan<id>.jpg'
        possible_static_path_png = f'images/lapangan{lapangan.pk}.png'
        possible_static_path_jpg = f'images/lapangan{lapangan.pk}.jpg'
        
        # Cek apakah file statis tersebut benar-benar ada
        found_static_path = None
        if find(possible_static_path_png): # find() akan mencari di semua folder static
             found_static_path = possible_static_path_png
        elif find(possible_static_path_jpg):
             found_static_path = possible_static_path_jpg
             
        # Tambahkan path yang ditemukan (atau None) ke objek
        lapangan.static_image_path = found_static_path 
        lapangan_list_with_static.append(lapangan)

    # --- Bagian Paginator (Jika Anda ingin menambahkannya) ---
    items_per_page = 16 # Atau angka lain
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
        # Jika pakai paginator, ganti 'lapangan_list' dengan 'page_obj'
        'lapangan_list': lapangan_list_with_static, 
        # 'page_obj': page_obj, # Aktifkan jika pakai paginator
        'jenis_choices': jenis_choices,
        'pending_bookings': get_pending_bookings_count(request.user),
    }
    return render(request, 'admin_dashboard/lapangan_list.html', context)
    


@pemilik_required
@require_http_methods(["GET", "POST"])  
def lapangan_create(request):
    """Form untuk membuat lapangan baru"""
    if request.method == 'POST':
        try:
            
            nama = request.POST.get('nama', '').strip()
            jenis = request.POST.get('jenis', '').strip()
            lokasi = request.POST.get('lokasi', '').strip()
            harga = request.POST.get('harga', '').strip()
            
            if not all([nama, jenis, lokasi, harga]):
                messages.error(request, 'Semua field wajib diisi!')
                return redirect('admin_dashboard:lapangan_create')
            
            try:
                harga_int = int(harga)
                if harga_int <= 0:
                    raise ValueError
            except ValueError:
                messages.error(request, 'Harga harus berupa angka positif!')
                return redirect('admin_dashboard:lapangan_create')
            
            
            valid_jenis = ['Futsal', 'Bulutangkis', 'Basket']
            if jenis not in valid_jenis:
                messages.error(request, 'Jenis olahraga tidak valid!')
                return redirect('admin_dashboard:lapangan_create')
            
            
            foto = request.FILES.get('foto_utama')
            if foto:
                # Batasi ukuran file (5MB)
                if foto.size > 5 * 1024 * 1024:
                    messages.error(request, 'Ukuran foto maksimal 5MB!')
                    return redirect('admin_dashboard:lapangan_create')
                
                # Batasi tipe file
                allowed_types = ['image/jpeg', 'image/jpg', 'image/png']
                if foto.content_type not in allowed_types:
                    messages.error(request, 'Format foto harus JPG atau PNG!')
                    return redirect('admin_dashboard:lapangan_create')
            
            # Buat lapangan baru dengan pengelola = profile pemilik yang login
            lapangan = Lapangan.objects.create(
                nama_lapangan=nama,
                jenis_olahraga=jenis,
                lokasi=lokasi,
                harga_per_jam=harga_int,
                deskripsi=request.POST.get('deskripsi', '').strip(),
                fasilitas=request.POST.get('fasilitas', '').strip(),
                pengelola=request.user.profile
            )
            
            if foto:
                lapangan.foto_utama = foto
                lapangan.save()
            
            messages.success(request, 'Lapangan berhasil ditambahkan!')
            return redirect('admin_dashboard:lapangan_list')
            
        except Exception as e:
            messages.error(request, f'Terjadi kesalahan: {str(e)}')
            return redirect('admin_dashboard:lapangan_create')
    
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


@pemilik_required
@require_http_methods(["GET", "POST"])  
def lapangan_edit(request, pk):
    """Edit lapangan yang sudah ada"""
    
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
                if harga_int <= 0:
                    raise ValueError
            except ValueError:
                messages.error(request, 'Harga harus berupa angka positif!')
                return render(request, 'admin_dashboard/lapangan_form.html', {
                    'lapangan': lapangan,
                    'jenis_choices': [('Futsal', 'Futsal'), ('Bulutangkis', 'Bulutangkis'), ('Basket', 'Basket')],
                    'pending_bookings': get_pending_bookings_count(request.user),
                })
            
            valid_jenis = ['Futsal', 'Bulutangkis', 'Basket']
            if jenis not in valid_jenis:
                messages.error(request, 'Jenis olahraga tidak valid!')
                return render(request, 'admin_dashboard/lapangan_form.html', {
                    'lapangan': lapangan,
                    'jenis_choices': [('Futsal', 'Futsal'), ('Bulutangkis', 'Bulutangkis'), ('Basket', 'Basket')],
                    'pending_bookings': get_pending_bookings_count(request.user),
                })
            
            # Update lapangan
            lapangan.nama_lapangan = nama
            lapangan.jenis_olahraga = jenis
            lapangan.lokasi = lokasi
            lapangan.harga_per_jam = harga_int
            lapangan.deskripsi = request.POST.get('deskripsi', '').strip()
            lapangan.fasilitas = request.POST.get('fasilitas', '').strip()
            
            
            foto = request.FILES.get('foto_utama')
            if foto:
                if foto.size > 5 * 1024 * 1024:
                    messages.error(request, 'Ukuran foto maksimal 5MB!')
                    return render(request, 'admin_dashboard/lapangan_form.html', {
                        'lapangan': lapangan,
                        'jenis_choices': [('Futsal', 'Futsal'), ('Bulutangkis', 'Bulutangkis'), ('Basket', 'Basket')],
                        'pending_bookings': get_pending_bookings_count(request.user),
                    })
                
                allowed_types = ['image/jpeg', 'image/jpg', 'image/png']
                if foto.content_type not in allowed_types:
                    messages.error(request, 'Format foto harus JPG atau PNG!')
                    return render(request, 'admin_dashboard/lapangan_form.html', {
                        'lapangan': lapangan,
                        'jenis_choices': [('Futsal', 'Futsal'), ('Bulutangkis', 'Bulutangkis'), ('Basket', 'Basket')],
                        'pending_bookings': get_pending_bookings_count(request.user),
                    })
                
                lapangan.foto_utama = foto
            
            lapangan.save()
            
            messages.success(request, 'Lapangan berhasil diupdate!')
            return redirect('admin_dashboard:lapangan_list')
            
        except Exception as e:
            messages.error(request, f'Terjadi kesalahan: {str(e)}')
    
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


@pemilik_required
@require_http_methods(["GET", "POST"])  
def lapangan_delete(request, pk):
    """Hapus lapangan"""
    
    lapangan = get_object_or_404(Lapangan, pk=pk, pengelola=request.user.profile)
    
    if request.method == 'POST':
        
        active_bookings = Booking.objects.filter(
            slot__lapangan=lapangan,
            status_pembayaran__in=['PENDING', 'PAID']
        ).exists()
        
        if active_bookings:
            messages.error(request, 'Tidak dapat menghapus lapangan yang masih memiliki booking aktif!')
            return redirect('admin_dashboard:lapangan_list')
        
        lapangan.delete()
        messages.success(request, 'Lapangan berhasil dihapus!')
        return redirect('admin_dashboard:lapangan_list')
    
    context = {
        'lapangan': lapangan,
        'pending_bookings': get_pending_bookings_count(request.user),
    }
    return render(request, 'admin_dashboard/lapangan_confirm_delete.html', context)


# ==================== BOOKING MANAGEMENT ====================
@pemilik_required
def booking_pending_list(request):
    """Menampilkan daftar booking PENDING untuk di-approve/reject"""
    # Filter booking PENDING untuk lapangan milik pemilik yang login
    pending_bookings = Booking.objects.filter(
        slot__lapangan__pengelola=request.user.profile,
        status_pembayaran='PENDING'
    ).select_related('user', 'slot', 'slot__lapangan').order_by('-tanggal_booking')
    
    context = {
        'pending_bookings': pending_bookings,
    }
    return render(request, 'admin_dashboard/booking_pending_list.html', context)


@pemilik_required
@require_http_methods(["GET", "POST"])  
@csrf_protect  
def booking_approve(request, pk):
    """Approve booking (PENDING → PAID, slot jadi BOOKED)"""
    
    booking = get_object_or_404(
        Booking, 
        pk=pk, 
        slot__lapangan__pengelola=request.user.profile,
        status_pembayaran='PENDING'
    )
    
    if request.method == 'POST':
        try:
            
            if booking.status_pembayaran != 'PENDING':
                messages.error(request, 'Booking ini sudah diproses!')
                return redirect('admin_dashboard:booking_pending')
            
            # Update status booking jadi PAID
            booking.status_pembayaran = 'PAID'
            booking.save()
            
            # Update slot jadi BOOKED (is_available = False)
            slot = booking.slot
            slot.is_available = False
            slot.pending_booking = None  # Clear pending
            slot.save()
            
            messages.success(request, f'Booking #{booking.id} berhasil di-approve!')
            return redirect('admin_dashboard:booking_pending')
            
        except Exception as e:
            messages.error(request, f'Terjadi kesalahan: {str(e)}')
            return redirect('admin_dashboard:booking_pending')
    
    context = {
        'booking': booking,
        'pending_bookings': get_pending_bookings_count(request.user),
    }
    return render(request, 'admin_dashboard/booking_approve_confirm.html', context)


@pemilik_required
@require_http_methods(["GET", "POST"])  
@csrf_protect  
def booking_reject(request, pk):
    """Reject booking (PENDING → CANCELLED, slot jadi AVAILABLE)"""
    
    booking = get_object_or_404(
        Booking, 
        pk=pk, 
        slot__lapangan__pengelola=request.user.profile,
        status_pembayaran='PENDING'
    )
    
    if request.method == 'POST':
        try:
            
            if booking.status_pembayaran != 'PENDING':
                messages.error(request, 'Booking ini sudah diproses!')
                return redirect('admin_dashboard:booking_pending')
            
            # Update status booking jadi CANCELLED
            booking.status_pembayaran = 'CANCELLED'
            booking.save()
            
            # Update slot jadi AVAILABLE lagi
            slot = booking.slot
            slot.is_available = True
            slot.pending_booking = None  # Clear pending
            slot.save()
            
            messages.success(request, f'Booking #{booking.id} berhasil ditolak!')
            return redirect('admin_dashboard:booking_pending')
            
        except Exception as e:
            messages.error(request, f'Terjadi kesalahan: {str(e)}')
            return redirect('admin_dashboard:booking_pending')
    
    context = {
        'booking': booking,
        'pending_bookings': get_pending_bookings_count(request.user),
    }
    return render(request, 'admin_dashboard/booking_reject_confirm.html', context)


@pemilik_required
def transaksi_list(request):
    status_filter = request.GET.get('status', '')

    # 1. Dapatkan SEMUA transaksi yang relevan (mungkin perlu filter per user)
    # Ganti .all() dengan filter yang sesuai untuk pemilik ini
    all_transactions_base = Booking.objects.filter(
        status_pembayaran__in=['PAID', 'CANCELLED']
        # CONTOH: (sesuaikan dengan model Anda)
        # slot__lapangan__pemilik=request.user 
    )

    # 2. Hitung jumlah untuk kartu summary SEBELUM memfilter
    paid_count = all_transactions_base.filter(status_pembayaran='PAID').count()
    cancelled_count = all_transactions_base.filter(status_pembayaran='CANCELLED').count()

    # 3. SEKARANG, filter daftar untuk ditampilkan di tabel
    table_transactions = all_transactions_base
    if status_filter:
        table_transactions = table_transactions.filter(status_pembayaran=status_filter)

    context = {
        # 'transaksi' sekarang berisi daftar yang sudah difilter untuk tabel
        'transaksi': table_transactions.order_by('-tanggal_booking'), 
        
        # Kirim hasil hitungan ke template
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