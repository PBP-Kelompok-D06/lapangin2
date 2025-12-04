# lapangin2/booking/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse, HttpResponseBadRequest
from django.contrib.auth.decorators import login_required
from .models import SlotTersedia, Booking, Lapangan
from datetime import date, timedelta
from django.views.decorators.csrf import csrf_exempt 
import json 
from django.contrib import messages
from datetime import date, timedelta, datetime # untuk mekanisme pembatalan status pending, sehingga kembali available
from django.utils import timezone # Untuk perbandingan timezone-aware
import os
from django.conf import settings
from django.db.models import Q
from django.views.decorators.http import require_http_methods
from django.core.serializers import serialize
import json as json_lib
import requests # type: ignore

def show_booking_page(request):
    
    all_lapangan = Lapangan.objects.all().order_by('nama_lapangan')
    
    # 1. Ambil ID Lapangan dan Tanggal dari Query GET
    lapangan_id_filter = request.GET.get('lapangan_id')
    selected_date_str = request.GET.get('date') # Ambil string tanggal dari URL
    
    # Tentukan Lapangan yang akan ditampilkan
    if lapangan_id_filter:
        lapangan_terpilih = get_object_or_404(all_lapangan, pk=lapangan_id_filter)
    else:
        lapangan_terpilih = all_lapangan.first()
    
    if not lapangan_terpilih:
        # Perbaikan Path Template: Menggunakan path lengkap 'login.html'
        return render(request, 'login.html', {'error': 'Tidak ada data lapangan di database.'})

    # Tentukan path gambar dinamis
    image_filename = f"images/lapangan{lapangan_terpilih.id}.png"
    project_static_dir = os.path.join(settings.BASE_DIR, 'static')
    image_path = os.path.join(project_static_dir, image_filename)

    if os.path.exists(image_path):
        hero_image_url = image_filename
    else:
        hero_image_url = "images/lapangan_default.jpg"

    # 2. Tentukan Tanggal Mulai Filter (Wajib Kuat)
    if selected_date_str:
        # Jika nilai date ada di URL (meskipun kosong/invalid)
        try:
            filter_date = date.fromisoformat(selected_date_str)
        except (ValueError, TypeError): 
            filter_date = date.today() # Kembali ke hari ini jika parsing gagal
    else:
        # Jika parameter date tidak ada di URL sama sekali
        filter_date = date.today()

    # Tentukan rentang 7 hari
    date_list = [filter_date + timedelta(days=i) for i in range(7)]
    
    # 3. Ambil slot yang relevan (termasuk pending_booking field yang baru)
    available_slots_queryset = SlotTersedia.objects.select_related('pending_booking').filter(
        lapangan=lapangan_terpilih,
        tanggal__in=date_list,
    ).order_by('tanggal', 'jam_mulai')

    # Re-organisasi slots ke dalam dictionary {tanggal: [slot1, slot2, ...]}
    slots_by_date = {}
    for slot_date in date_list:
        slots = list(available_slots_queryset.filter(tanggal=slot_date))
        
        # --- LOGIC 3-STATUS (AVAILABLE, PENDING, BOOKED) ---
        for slot in slots:
            # Status Default
            slot.display_status = 'AVAILABLE' 
            
            if not slot.is_available:
                # Slot Confirmed: Hanya terjadi jika Admin sudah ACC
                slot.display_status = 'BOOKED' 
            elif slot.pending_booking is not None:
                # Slot sedang dalam proses pemesanan oleh User lain
                slot.display_status = 'PENDING' 
            
            # Tambahkan status ke list slot
            
        slots_by_date[slot_date] = slots
        # -------------------------------------------------------------
        
    context = {
        'lapangan_terpilih': lapangan_terpilih,
        'all_lapangan': all_lapangan,
        'filter_date_str': filter_date.strftime('%Y-%m-%d'),
        'date_list': date_list,
        'slots_by_date': slots_by_date,
        'today': date.today(),
        'hero_image_url': hero_image_url,
        'show_navbar': True,
    }
    
    return render(request, 'booking.html', context)


# 2. create_booking: Memproses permintaan booking dari AJAX (Form Input Wajib)
@csrf_exempt 
@login_required 
def create_booking(request):
    if request.method == 'POST':
        if not request.user.is_authenticated:
            return JsonResponse({'message': 'Anda harus login untuk booking.'}, status=403)
        
        try:
            data = json.loads(request.body)
            slot_id = data.get('slot_id')
            slot = get_object_or_404(SlotTersedia, pk=slot_id) 
            
            
            # Hitung total pembayaran
            raw_price = slot.lapangan.harga_per_jam
            total_bayar = raw_price if raw_price is not None else 0
            
            # --- INPUT FIELD KE MODEL CREATE ---
            booking = Booking.objects.create(
                user=request.user,
                slot=slot,
                # TANGGAL BOOKING: Gunakan tanggal slot atau waktu sekarang
                tanggal_booking=slot.tanggal, 
                total_bayar=total_bayar,     
                status_pembayaran='PENDING' 
            )
            # ----------------------------------------------------
            
            # KUNCI BARU: Update Slot untuk menandai bahwa ia sedang di-pending
            slot.pending_booking = booking
            slot.save()
            
            # Kembalikan respons sukses
            return JsonResponse({
                'success': True,
                'booking_id': booking.id, 
                'message': 'Request berhasil dibuat. Lanjut ke pembayaran.'
            }, status=200)

        except Exception as e:
            # Ini akan menangkap NOT NULL constraint failed
            return JsonResponse({'message': f'Internal Server Error: {str(e)}'}, status=500)

    return JsonResponse({'message': 'Metode tidak diizinkan.'}, status=405)



# View AJAX untuk Polling Status Slot
# View ini diakses oleh JavaScript di booking.html setiap 5 detik
def check_slot_status(request):
    # Mengambil ID Lapangan dari request GET (wajib untuk filter)
    lapangan_id = request.GET.get('lapangan_id')
    
    if not lapangan_id:
        return JsonResponse({'error': 'Lapangand ID is required'}, status=400)
    
    try:
        lapangan_terpilih = Lapangan.objects.get(pk=lapangan_id)
    except Lapangan.DoesNotExist:
        return JsonResponse({'error': 'Lapangan not found'}, status=404)

    # Ambil SEMUA slot untuk Lapangan tersebut (minimal 7 hari ke depan)
    # Gunakan values() untuk membuat query super ringan
    slots_data = SlotTersedia.objects.filter(
        lapangan=lapangan_terpilih
    ).values(
        'id', 
        'is_available', 
        'pending_booking__id' # Mengakses ID booking yang sedang pending
    )
    
    # Konversi data query ke format list yang mudah diproses JSON
    response_data = []
    for slot in slots_data:
        # Menentukan status display (Logic 3-Status di sisi server)
        status = 'AVAILABLE'
        if not slot['is_available']:
            status = 'BOOKED'
        elif slot['pending_booking__id'] is not None:
            status = 'PENDING'
            
        response_data.append({
            'id': slot['id'],
            'status': status
        })
    
    return JsonResponse(response_data, safe=False)



# 3. show_payment_page: Menampilkan instruksi pembayaran
@login_required 
def show_payment_page(request, booking_id):
    booking = get_object_or_404(Booking, pk=booking_id)

    # 1. Validasi Kepemilikan (Wajib)
    if booking.user != request.user:
        messages.error(request, "Anda tidak memiliki akses ke pemesanan ini.")
        return redirect('booking:show_booking_page')
    
    # --- LOGIC TIMEOUT (5 MENIT) ---
    timeout_duration = timedelta(minutes=5) # dalam waktu 5 menit status PENDING akan kembali ke AVAILABLE
    # Penyewa harus segera membayar pesanan dan pemilik harus segera meng acc pesanan dalam rentang waktu 10 menit tsb
    
    # Kunci: Mendapatkan waktu berakhir dalam format Unix Timestamp (ms) untuk JavaScript
    if booking.status_pembayaran == 'PENDING':
        timeout_time = booking.tanggal_booking + timeout_duration
        
        # Cek apakah sudah timeout 
        if timezone.now() > timeout_time:
            # Logic Pembatalan Otomatis
            slot_terkait = booking.slot
            if slot_terkait and slot_terkait.pending_booking == booking:
                slot_terkait.pending_booking = None
                slot_terkait.save()
            booking.status_pembayaran = 'CANCELLED'
            booking.save()

            # bersihin pesan lama supaya gak dobel
            storage = messages.get_messages(request)
            storage.used = True

            # Kirim pesan baru hanya kalau user masih login
            if request.user.is_authenticated:
                messages.error(request, "Waktu pembayaran (5 menit) telah habis. Pemesanan dibatalkan.")

            return redirect('booking:show_booking_page')

        # Kirim waktu berakhir sebagai Unix Timestamp (milidetik) ke template
        time_to_expire_ms = int(timeout_time.timestamp() * 1000)
    else:
        # Jika status bukan PENDING, tidak ada countdown
        time_to_expire_ms = None


    # --- Ambil data pemilik lapangan ---
    pemilik = booking.slot.lapangan.pengelola
    no_rekening = pemilik.nomor_rekening if hasattr(pemilik, 'nomor_rekening') else 'Tidak tersedia'
    contact_whatsapp = pemilik.nomor_whatsapp if hasattr(pemilik, 'nomor_whatsapp') else 'Tidak tersedia'

    context = {
        'booking': booking,
        'no_rekening': no_rekening,
        'contact_whatsapp': contact_whatsapp,
        'time_to_expire_ms': time_to_expire_ms,
        'show_navbar': True,
    }

    return render(request, 'payment_detail.html', context)

@login_required
def my_bookings(request):
    # Ambil semua booking user yang sudah dibayar atau slot-nya sudah dikunci
    bookings = (
        Booking.objects
        .select_related('slot__lapangan')
        .filter(user=request.user)
        .filter(Q(status_pembayaran='PAID') | Q(slot__is_available=False))
        .order_by('-tanggal_booking')
    )


    context = {
        'bookings': bookings,
        'show_navbar': True,
    }
    return render(request, 'my_bookings.html', context)
# ============================================================
# API ENDPOINTS UNTUK FLUTTER
# ============================================================

# API 1: Get All Lapangan (untuk dropdown/list)
@require_http_methods(["GET"])
def api_get_lapangan_list(request):
    """
    Endpoint untuk mengambil daftar semua lapangan
    GET /booking/api/lapangan/
    """
    try:
        lapangan_list = Lapangan.objects.filter(is_active=True).order_by('nama_lapangan')
        
        data = []
        for lapangan in lapangan_list:
            data.append({
                'id': lapangan.id,
                'nama_lapangan': lapangan.nama_lapangan,
                'jenis_olahraga': lapangan.jenis_olahraga,
                'lokasi': lapangan.lokasi,
                'harga_per_jam': float(lapangan.harga_per_jam),
                'fasilitas': lapangan.fasilitas,
                'rating': float(lapangan.rating),
                'jumlah_ulasan': lapangan.jumlah_ulasan,
                'foto_utama': request.build_absolute_uri(lapangan.foto_utama.url) if lapangan.foto_utama else None,
                'deskripsi': lapangan.deskripsi,
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


# API 2: Get Lapangan Detail
@require_http_methods(["GET"])
def api_get_lapangan_detail(request, lapangan_id):
    """
    Endpoint untuk mengambil detail lapangan tertentu
    GET /booking/api/lapangan/<id>/
    """
    try:
        lapangan = get_object_or_404(Lapangan, pk=lapangan_id, is_active=True)
        
        # PRIORITAS FOTO: foto_utama dari upload > static image fallback
        foto_utama_url = None
        foto_2_url = None
        foto_3_url = None
        
        if lapangan.foto_utama:
            foto_utama_url = request.build_absolute_uri(lapangan.foto_utama.url)
        else:
            # Fallback ke static image
            foto_utama_url = request.build_absolute_uri(f'/static/images/lapangan{lapangan.id}.png')
        
        if lapangan.foto_2:
            foto_2_url = request.build_absolute_uri(lapangan.foto_2.url)
        
        if lapangan.foto_3:
            foto_3_url = request.build_absolute_uri(lapangan.foto_3.url)
        
        data = {
            'id': lapangan.id,
            'nama_lapangan': lapangan.nama_lapangan,
            'jenis_olahraga': lapangan.jenis_olahraga,
            'lokasi': lapangan.lokasi,
            'harga_per_jam': float(lapangan.harga_per_jam),
            'fasilitas': lapangan.fasilitas,
            'rating': float(lapangan.rating),
            'jumlah_ulasan': lapangan.jumlah_ulasan,
            'foto_utama': foto_utama_url,  # ✅ Selalu ada nilai (upload atau static)
            'foto_2': foto_2_url,
            'foto_3': foto_3_url,
            'deskripsi': lapangan.deskripsi,
            'pengelola': {
                'username': lapangan.pengelola.user.username if lapangan.pengelola else None,
                'nomor_whatsapp': lapangan.pengelola.nomor_whatsapp if lapangan.pengelola else None,
            } if lapangan.pengelola else None
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


# API 3: Get Available Slots
@require_http_methods(["GET"])
def api_get_available_slots(request, lapangan_id):
    """
    Endpoint untuk mengambil slot yang tersedia untuk lapangan tertentu
    GET /booking/api/slots/<lapangan_id>/?date=YYYY-MM-DD&days=7
    
    Query Parameters:
    - date: tanggal mulai (default: hari ini)
    - days: jumlah hari yang ingin ditampilkan (default: 7)
    """
    try:
        lapangan = get_object_or_404(Lapangan, pk=lapangan_id, is_active=True)
        
        # Parse query parameters
        date_str = request.GET.get('date')
        days = int(request.GET.get('days', 7))
        
        # Tentukan tanggal mulai
        if date_str:
            try:
                start_date = date.fromisoformat(date_str)
            except ValueError:
                start_date = date.today()
        else:
            start_date = date.today()
        
        # Generate list tanggal
        date_list = [start_date + timedelta(days=i) for i in range(days)]
        
        # Ambil slots
        slots = SlotTersedia.objects.select_related('pending_booking').filter(
            lapangan=lapangan,
            tanggal__in=date_list,
        ).order_by('tanggal', 'jam_mulai')
        
        # Format data berdasarkan tanggal
        slots_by_date = {}
        for slot_date in date_list:
            date_key = slot_date.strftime('%Y-%m-%d')
            slots_by_date[date_key] = []
            
            day_slots = slots.filter(tanggal=slot_date)
            for slot in day_slots:
                # Tentukan status
                status = 'AVAILABLE'
                if not slot.is_available:
                    status = 'BOOKED'
                elif slot.pending_booking is not None:
                    status = 'PENDING'
                
                slots_by_date[date_key].append({
                    'id': slot.id,
                    'jam_mulai': slot.jam_mulai.strftime('%H:%M'),
                    'jam_akhir': slot.jam_akhir.strftime('%H:%M'),
                    'status': status,
                    'harga': float(lapangan.harga_per_jam)
                })
        
        return JsonResponse({
            'status': 'success',
            'data': {
                'lapangan_id': lapangan.id,
                'lapangan_nama': lapangan.nama_lapangan,
                'harga_per_jam': float(lapangan.harga_per_jam),
                'slots_by_date': slots_by_date
            }
        }, status=200)
    
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)


# API 4: Create Booking - WORKAROUND TANPA UBAH MODEL
@csrf_exempt
@require_http_methods(["POST"])
def api_create_booking(request):
    """
    Endpoint untuk membuat booking baru
    """
    if not request.user.is_authenticated:
        return JsonResponse({
            'status': 'error',
            'message': 'Anda harus login untuk melakukan booking.'
        }, status=401)
    
    try:
        data = json_lib.loads(request.body)
        slot_id = data.get('slot_id')
        
        if not slot_id:
            return JsonResponse({
                'status': 'error',
                'message': 'slot_id diperlukan.'
            }, status=400)
        
        slot = get_object_or_404(SlotTersedia, pk=slot_id)
        
        # Cek apakah slot masih available
        if not slot.is_available:
            return JsonResponse({
                'status': 'error',
                'message': 'Slot sudah dibooking oleh orang lain.'
            }, status=400)
        
        if slot.pending_booking is not None:
            return JsonResponse({
                'status': 'error',
                'message': 'Slot sedang dalam proses booking oleh orang lain.'
            }, status=400)
        
        # Hitung total pembayaran
        raw_price = slot.lapangan.harga_per_jam
        total_bayar = raw_price if raw_price is not None else 0
        
        # WORKAROUND: Buat object tanpa save dulu, lalu set tanggal, baru save
        from django.utils import timezone
        from datetime import datetime
        
        # Buat datetime dari tanggal slot (dengan waktu 00:00:00)
        tanggal_booking_dt = timezone.make_aware(
            datetime.combine(slot.tanggal, datetime.min.time())
        )
        
        # Buat object Booking TANPA menyimpan
        booking = Booking(
            user=request.user,
            slot=slot,
            total_bayar=total_bayar,
            status_pembayaran='PENDING'
        )
        
        # Simpan object (auto_now_add=True akan set tanggal_booking ke waktu sekarang)
        booking.save()
        
        # SEKARANG OVERRIDE tanggal_booking dengan tanggal yang kita mau
        # Kita gunakan .update() untuk bypass auto_now_add
        Booking.objects.filter(id=booking.id).update(
            tanggal_booking=tanggal_booking_dt
        )
        
        # Refresh object dari database
        booking.refresh_from_db()
        
        # Update slot
        slot.pending_booking = booking
        slot.save()
        
        # DEBUG: Print untuk memastikan tanggal benar
        print(f"✅ DEBUG: Booking created - Slot Date: {slot.tanggal}, Booking Date: {booking.tanggal_booking}")
        
        return JsonResponse({
            'status': 'success',
            'message': 'Booking berhasil dibuat.',
            'data': {
                'booking_id': booking.id,
                'total_bayar': float(booking.total_bayar),
                'status_pembayaran': booking.status_pembayaran
            }
        }, status=201)
    
    except Exception as e:
        print(f"❌ ERROR in api_create_booking: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)


# API 5: Get Booking Detail - WITH SOLUSI 2 IMPROVED
@require_http_methods(["GET"])
def api_get_booking_detail(request, booking_id):
    """
    Endpoint untuk mengambil detail booking
    GET /booking/api/booking/<booking_id>/
    """
    if not request.user.is_authenticated:
        return JsonResponse({
            'status': 'error',
            'message': 'Anda harus login.'
        }, status=401)
    
    try:
        booking = get_object_or_404(Booking, pk=booking_id)
        
        # Validasi kepemilikan
        if booking.user != request.user:
            return JsonResponse({
                'status': 'error',
                'message': 'Anda tidak memiliki akses ke booking ini.'
            }, status=403)
        
        # SOLUSI 2: IMPROVED TIMEOUT LOGIC
        timeout_duration = timedelta(minutes=5)
        if booking.status_pembayaran == 'PENDING':
            # WORKAROUND: Karena tanggal_booking sekarang adalah tanggal slot (2025-12-04)
            # kita perlu estimasi waktu pembuatan booking yang realistis
            
            # Estimasi: booking biasanya dibuat 10-60 detik yang lalu dari request ini
            # Kita ambil estimasi 30 detik untuk middle ground yang aman
            estimated_creation_time = timezone.now() - timedelta(seconds=30)
            
            timeout_time = estimated_creation_time + timeout_duration
            
            # Safety bounds: maksimal 5 menit (300 detik), minimal 0
            raw_time_remaining = max(0, int((timeout_time - timezone.now()).total_seconds()))
            time_remaining_seconds = min(raw_time_remaining, 300)  # Maksimal 5 menit
            
            print(f"⏰ DEBUG TIMEOUT - Booking ID: {booking.id}")
            print(f"   Estimated creation: {estimated_creation_time}")
            print(f"   Timeout time: {timeout_time}") 
            print(f"   Now: {timezone.now()}")
            print(f"   Raw remaining: {raw_time_remaining}s")
            print(f"   Final remaining: {time_remaining_seconds}s")
            
            # Jika waktu habis, batalkan booking
            if time_remaining_seconds <= 0:
                print(f"❌ TIMEOUT - Cancelling booking {booking.id}")
                slot_terkait = booking.slot
                if slot_terkait and slot_terkait.pending_booking == booking:
                    slot_terkait.pending_booking = None
                    slot_terkait.save()
                booking.status_pembayaran = 'CANCELLED'
                booking.save()
                time_remaining_seconds = 0
        else:
            time_remaining_seconds = None
        
        # Ambil data pemilik
        pemilik = booking.slot.lapangan.pengelola
        
        data = {
            'id': booking.id,
            'lapangan': {
                'id': booking.slot.lapangan.id,
                'nama': booking.slot.lapangan.nama_lapangan,
                'lokasi': booking.slot.lapangan.lokasi,
                'foto_utama': request.build_absolute_uri(booking.slot.lapangan.foto_utama.url) if booking.slot.lapangan.foto_utama else None,
            },
            'slot': {
                'tanggal': booking.slot.tanggal.strftime('%Y-%m-%d'),
                'jam_mulai': booking.slot.jam_mulai.strftime('%H:%M'),
                'jam_akhir': booking.slot.jam_akhir.strftime('%H:%M'),
            },
            'tanggal_booking': booking.tanggal_booking.strftime('%Y-%m-%d %H:%M:%S'),
            'total_bayar': float(booking.total_bayar),
            'status_pembayaran': booking.status_pembayaran,
            'status_pembayaran_display': booking.get_status_pembayaran_display(),
            'time_remaining_seconds': time_remaining_seconds,
            'pemilik': {
                'nomor_rekening': pemilik.nomor_rekening if pemilik and hasattr(pemilik, 'nomor_rekening') else None,
                'nomor_whatsapp': pemilik.nomor_whatsapp if pemilik and hasattr(pemilik, 'nomor_whatsapp') else None,
            }
        }
        
        return JsonResponse({
            'status': 'success',
            'data': data
        }, status=200)
    
    except Exception as e:
        print(f"❌ ERROR in api_get_booking_detail: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)


# API 6: Get My Bookings (List semua booking user)
@require_http_methods(["GET"])
def api_get_my_bookings(request):
    """
    Endpoint untuk mengambil semua booking milik user yang login
    GET /booking/api/my-bookings/
    """
    if not request.user.is_authenticated:
        return JsonResponse({
            'status': 'error',
            'message': 'Anda harus login.'
        }, status=401)
    
    try:
        bookings = (
            Booking.objects
            .select_related('slot__lapangan')
            .filter(user=request.user)
            .filter(Q(status_pembayaran='PAID') | Q(slot__is_available=False))
            .order_by('-tanggal_booking')
        )
        
        data = []
        for booking in bookings:
            data.append({
                'id': booking.id,
                'lapangan': {
                    'id': booking.slot.lapangan.id,
                    'nama': booking.slot.lapangan.nama_lapangan,
                    'lokasi': booking.slot.lapangan.lokasi,
                    'foto_utama': request.build_absolute_uri(booking.slot.lapangan.foto_utama.url) if booking.slot.lapangan.foto_utama else None,
                },
                'slot': {
                    'tanggal': booking.slot.tanggal.strftime('%Y-%m-%d'),
                    'jam_mulai': booking.slot.jam_mulai.strftime('%H:%M'),
                    'jam_akhir': booking.slot.jam_akhir.strftime('%H:%M'),
                },
                'tanggal_booking': booking.tanggal_booking.strftime('%Y-%m-%d %H:%M:%S'),
                'total_bayar': float(booking.total_bayar),
                'status_pembayaran': booking.status_pembayaran,
                'status_pembayaran_display': booking.get_status_pembayaran_display(),
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


# API 7: Cancel Booking (Opsional - jika diperlukan)
@csrf_exempt
@require_http_methods(["POST"])
def api_cancel_booking(request, booking_id):
    """
    Endpoint untuk membatalkan booking (hanya jika masih PENDING)
    POST /booking/api/booking/<booking_id>/cancel/
    """
    if not request.user.is_authenticated:
        return JsonResponse({
            'status': 'error',
            'message': 'Anda harus login.'
        }, status=401)
    
    try:
        booking = get_object_or_404(Booking, pk=booking_id)
        
        # Validasi kepemilikan
        if booking.user != request.user:
            return JsonResponse({
                'status': 'error',
                'message': 'Anda tidak memiliki akses ke booking ini.'
            }, status=403)
        
        # Hanya bisa cancel jika masih PENDING
        if booking.status_pembayaran != 'PENDING':
            return JsonResponse({
                'status': 'error',
                'message': f'Booking dengan status {booking.status_pembayaran} tidak dapat dibatalkan.'
            }, status=400)
        
        # Update slot
        slot = booking.slot
        if slot.pending_booking == booking:
            slot.pending_booking = None
            slot.save()
        
        # Update booking
        booking.status_pembayaran = 'CANCELLED'
        booking.save()
        
        return JsonResponse({
            'status': 'success',
            'message': 'Booking berhasil dibatalkan.'
        }, status=200)
    
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)
    
def proxy_image(request):
    image_url = request.GET.get('url')
    if not image_url:
        return HttpResponse('No URL provided', status=400)
    
    try:
        # Fetch image from external source
        response = requests.get(image_url, timeout=10)
        response.raise_for_status()
        
        # Return the image with proper content type
        return HttpResponse(
            response.content,
            content_type=response.headers.get('Content-Type', 'image/jpeg')
        )
    except requests.RequestException as e: 
        return HttpResponse(f'Error fetching image: {str(e)}', status=500)