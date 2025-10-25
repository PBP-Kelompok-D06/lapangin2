from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponseBadRequest
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
            slot = get_object_or_404(SlotTersedia, pk=slot_id) # <-- Baris ini harus aman
            
            # ... (Tahap 1: Validasi Status Pending tetap sama) ...
            
            # Hitung total pembayaran (Perbaikan: Memastikan nilai tidak NULL)
            raw_price = slot.lapangan.harga_per_jam
            total_bayar = raw_price if raw_price is not None else 0
            
            # --- PERBAIKAN KRITIS: INPUT FIELD KE MODEL CREATE ---
            booking = Booking.objects.create(
                user=request.user,
                slot=slot,
                # TANGGAL BOOKING: Gunakan tanggal slot atau waktu sekarang
                # Asumsi di Model Anda memiliki auto_now_add=True atau field tidak wajib. 
                # Jika wajib, kita gunakan tanggal dari slot:
                tanggal_booking=slot.tanggal, # <--- TAMBAHKAN INI
                total_bayar=total_bayar,     # <--- TAMBAHKAN INI
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