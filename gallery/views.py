from django.shortcuts import render, get_object_or_404
from booking.models import Lapangan
from review.models import Review  # Import model Review
import re
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from booking.models import Lapangan
from review.models import Review

def show_gallery(request, lap_id):
    lapangan = get_object_or_404(Lapangan, pk=lap_id)
    fasilitas_list = [f.strip() for f in lapangan.fasilitas.split(',')] if lapangan.fasilitas else []

    # tiga gambar statis berdasarkan id lapangan
    hero_images = [
        f'images/lapangan{lapangan.id}.png',
        f'images/lapangan{lapangan.id}_2.png',
        f'images/lapangan{lapangan.id}_3.png',
    ]
    # pakai semuanya juga untuk thumbnail
    gallery_images = hero_images

    nomor_whatsapp = None
    if lapangan.pengelola and lapangan.pengelola.nomor_whatsapp:
        nomor_whatsapp = re.sub(r'\D', '', lapangan.pengelola.nomor_whatsapp)
        # konversi 08... -> 628...
        if nomor_whatsapp.startswith('0'):
            nomor_whatsapp = '62' + nomor_whatsapp[1:]

    # ===== TAMBAHAN: Ambil 4 review teratas =====
    reviews = Review.objects.filter(field=lapangan).order_by('-created_at')[:4]
    
    # Tandai ownership untuk setiap review
    for review in reviews:
        review.is_owner = review.user.user == request.user if request.user.is_authenticated else False
    # ============================================

    context = {
        'lapangan': lapangan,
        'fasilitas_list': fasilitas_list,
        'hero_images': hero_images,
        'gallery_images': gallery_images,
        'nomor_whatsapp': nomor_whatsapp,
        'reviews': reviews,  # Tambahkan ini
        'field': lapangan,    # Untuk kompatibilitas dengan template reviews.html
        'show_navbar': True,
    }
    return render(request, 'gallery_detail.html', context)

def _absolute_url(request, field):
    return request.build_absolute_uri(field.url) if field else None

def get_lapangan_list(request):
    qs = Lapangan.objects.filter(is_active=True)
    data = []
    for lap in qs:
        data.append({
            "id": lap.id,
            "nama_lapangan": lap.nama_lapangan,
            "lokasi": lap.lokasi,
            "harga_per_jam": int(lap.harga_per_jam),
            "rating": float(lap.rating),
            "thumbnail_url": _absolute_url(request, lap.foto_utama),
        })
    return JsonResponse(data, safe=False)

def get_lapangan_detail(request, lap_id):
    lap = get_object_or_404(Lapangan, pk=lap_id, is_active=True)
    fasilitas_list = [f.strip() for f in lap.fasilitas.split(',') if f.strip() and f.strip() != '-']

    gallery = [u for u in (
        _absolute_url(request, lap.foto_utama),
        _absolute_url(request, lap.foto_2),
        _absolute_url(request, lap.foto_3),
    ) if u]

    reviews_qs = Review.objects.filter(field=lap).order_by('-created_at')[:10]
    reviews = [{
        "user": r.user.username,
        "rating": float(r.rating),
        "content": r.content,
        "created_at": r.created_at.strftime("%Y-%m-%d")
    } for r in reviews_qs]

    data = {
        "id": lap.id,
        "nama_lapangan": lap.nama_lapangan,
        "jenis_olahraga": lap.jenis_olahraga,
        "lokasi": lap.lokasi,
        "harga_per_jam": int(lap.harga_per_jam),
        "rating": float(lap.rating),
        "jumlah_ulasan": lap.jumlah_ulasan,
        "deskripsi": lap.deskripsi,
        "fasilitas": fasilitas_list,
        "gallery_images": gallery,
        "reviews": reviews,
    }
    return JsonResponse(data)