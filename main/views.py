from django.http import HttpResponse
from django.shortcuts import render
from django.core.paginator import Paginator
from booking.models import Lapangan
from django.templatetags.static import static
from django.contrib.staticfiles.finders import find
import os
import requests # type: ignore
from django.http import JsonResponse
from urllib.parse import urlparse

def show_landing_page(request):
    jenis_filter = request.GET.get('jenis', 'all')
    rating_filter = request.GET.get('rating', 'all')

    lapangan_queryset = Lapangan.objects.all().order_by('pk')

    if jenis_filter != 'all':
        lapangan_queryset = lapangan_queryset.filter(jenis_olahraga__iexact=jenis_filter)

    if rating_filter != 'all':
        if rating_filter == '0':
            lapangan_queryset = lapangan_queryset.filter(jumlah_ulasan=0)
        else:
            try:
                rating_val = float(rating_filter)
                lapangan_queryset = lapangan_queryset.filter(rating__gte=rating_val)
            except ValueError:
                pass

    lapangan_list_processed = []
    for lapangan in lapangan_queryset:
        # LANGSUNG set path statis berdasarkan pk, tanpa find()
        lapangan.static_image_path = f"images/lapangan{lapangan.pk}.png"
        lapangan_list_processed.append(lapangan)

    paginator = Paginator(lapangan_list_processed, 16)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    jenis_list = (
        Lapangan.objects.values_list('jenis_olahraga', flat=True)
        .distinct()
        .order_by('jenis_olahraga')
    )

    context = {
        "page_obj": page_obj,
        "jenis_list": jenis_list,
        "selected_jenis": jenis_filter,
        "selected_rating": rating_filter,
        "show_navbar": True,
    }
    return render(request, "landing_page.html", context)

def proxy_image(request):
    image_url = request.GET.get('url')
    if not image_url:
        return HttpResponse('No URL provided', status=400)

    #  SANITIZE: ambil URL terakhir kalau double protocol
    if "http://" in image_url[1:] or "https://" in image_url[1:]:
        # ambil protocol terakhir
        idx = max(image_url.rfind("http://"), image_url.rfind("https://"))
        image_url = image_url[idx:]

    # VALIDASI URL
    parsed = urlparse(image_url)
    if not parsed.scheme or not parsed.netloc:
        return HttpResponse('Invalid image URL', status=400)

    try:
        response = requests.get(image_url, timeout=10)
        response.raise_for_status()

        return HttpResponse(
            response.content,
            content_type=response.headers.get('Content-Type', 'image/png')
        )

    except requests.RequestException as e:
        return HttpResponse(
            f'Error fetching image: {str(e)}',
            status=502  #  lebih tepat daripada 500
        )
    
def get_lapangan_list(request):
    lapangan_queryset = Lapangan.objects.all().order_by('pk')
    
    data = []
    
    for field in lapangan_queryset:
        possible_png = f'static/images/lapangan{field.pk}.png'
        
        image_url = possible_png

        if field.foto_utama:
            image_url = field.foto_utama.url

        data.append({
            "id": field.pk,
            "name": field.nama_lapangan,        
            "type": field.jenis_olahraga,      
            "location": field.lokasi,           
            "price": int(field.harga_per_jam),  
            "rating": float(field.rating),      
            "image": image_url,
            "review_count": field.jumlah_ulasan 
        })

    return JsonResponse(data, safe=False)