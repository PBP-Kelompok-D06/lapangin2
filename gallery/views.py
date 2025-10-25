from django.shortcuts import render, get_object_or_404
from booking.models import Lapangan
from review.models import Review  # Import model Review
import re

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