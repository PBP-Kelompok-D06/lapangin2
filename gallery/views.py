# gallery/views.py
import re
from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, JsonResponse
import requests
from booking.models import Lapangan
from review.models import Review

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


def show_gallery(request, lap_id):
    lapangan = get_object_or_404(Lapangan, pk=lap_id)
    fasilitas_list = [f.strip() for f in lapangan.fasilitas.split(',')] if lapangan.fasilitas else []

    # tiga gambar statis berdasarkan id lapangan (untuk template lama)
    hero_images = [
        f'images/lapangan{lapangan.id}.png',
        f'images/lapangan{lapangan.id}_2.png',
        f'images/lapangan{lapangan.id}_3.png',
    ]
    
    gallery_images = hero_images

    nomor_whatsapp = None
    if lapangan.pengelola and getattr(lapangan.pengelola, 'nomor_whatsapp', None):
        nomor_whatsapp = re.sub(r'\D', '', lapangan.pengelola.nomor_whatsapp)
        if nomor_whatsapp.startswith('0'):
            nomor_whatsapp = '62' + nomor_whatsapp[1:]

    # Ambil 4 review teratas (untuk template)
    reviews = Review.objects.filter(field=lapangan).order_by('-created_at')[:4]

    # Tandai ownership untuk setiap review (untuk template)
    for review in reviews:
        review.is_owner = review.user.user == request.user if request.user.is_authenticated else False


    context = {
        'lapangan': lapangan,
        'fasilitas_list': fasilitas_list,
        'hero_images': hero_images,
        'gallery_images': gallery_images,
        'nomor_whatsapp': nomor_whatsapp,
        'reviews': reviews,
        'field': lapangan,
        'show_navbar': True,
    }
    return render(request, 'gallery_detail.html', context)


def _absolute_url(request, field):
    """Return absolute URL for ImageField or None."""
    try:
        return request.build_absolute_uri(field.url) if field else None
    except Exception:
        return None


def get_lapangan_list(request):
    """
    JSON list compatible with LapanganEntry model.
    Fields: id, name, type, location, price, rating, image, review_count
    """
    qs = Lapangan.objects.filter(is_active=True)
    data = []
    for lap in qs:
        data.append({
            "id": lap.id,
            "name": lap.nama_lapangan,
            "type": lap.jenis_olahraga,                    # enum string expected by Dart
            "location": lap.lokasi,
            "price": int(lap.harga_per_jam),
            "rating": float(lap.rating),
            "image": f'static/images/lapangan{lap.id}.png',
            "review_count": lap.jumlah_ulasan,
        })
    return JsonResponse(data, safe=False)


def get_lapangan_detail(request, lap_id):
    """
    JSON detail compatible with LapanganEntry (plus gallery_images & reviews).
    Returns a dict (not list).
    """
    lap = get_object_or_404(Lapangan, pk=lap_id, is_active=True)


    # gallery images (absolute urls)
    gallery = [
        f'static/images/lapangan{lap.id}.png',
        f'static/images/lapangan{lap.id}_2.png',
        f'static/images/lapangan{lap.id}_3.png',
    ]

    # reviews serialized
    reviews_qs = Review.objects.filter(field=lap).order_by('-created_at')
    reviews = [{
        "id": r.id,
        "user": r.user.user.username,
        "rating": float(r.rating),
        "content": r.content,
        "created_at": r.created_at.strftime("%Y-%m-%d"),
        "is_owner": r.user.user == request.user,
    } for r in reviews_qs]

    data = {
        "id": lap.id,
        "name": lap.nama_lapangan,
        "type": lap.jenis_olahraga,
        "location": lap.lokasi,
        "price": int(lap.harga_per_jam),
        "rating": float(lap.rating),
        "image": f'static/images/lapangan{lap.id}.png',
        "review_count": lap.jumlah_ulasan,
        # tambahan berguna untuk detail view di app
        "deskripsi": lap.deskripsi,
        "fasilitas": [f.strip() for f in (lap.fasilitas or '').split(',') if f.strip() and f.strip() != '-'],
        "gallery_images": gallery,
        "reviews": reviews,
    }
    return JsonResponse(data)
