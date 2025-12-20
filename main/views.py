from django.http import HttpResponse
from django.shortcuts import render
from django.core.paginator import Paginator
from booking.models import Lapangan
from django.templatetags.static import static
from django.contrib.staticfiles.finders import find
import os
import requests # type: ignore
from django.http import JsonResponse
from urllib.parse import urlparse, unquote
import logging

def show_landing_page(request):
    """Menampilkan Landing Page Lapang.in dengan daftar lapangan dan pagination."""
    jenis_filter = request.GET.get('jenis', 'all')
    rating_filter = request.GET.get('rating', 'all')

    # Ambil queryset awal dan PASTIKAN ADA URUTAN (misal berdasarkan ID)
    # Ini juga mengatasi UnorderedObjectListWarning
    lapangan_queryset = Lapangan.objects.all().order_by('pk') 

    # === Filter jenis olahraga ===
    if jenis_filter != 'all':
        lapangan_queryset = lapangan_queryset.filter(jenis_olahraga__iexact=jenis_filter)

    # === Filter rating ===
    if rating_filter != 'all':
        if rating_filter == '0':
            # Lapangan yang belum punya ulasan
            lapangan_queryset = lapangan_queryset.filter(jumlah_ulasan=0)
        else:
            try: # Tambahkan try-except untuk rating filter
                rating_val = float(rating_filter)
                lapangan_queryset = lapangan_queryset.filter(rating__gte=rating_val)
            except ValueError:
                # Abaikan filter rating jika nilainya tidak valid
                pass

    # --- LOGIKA TAMBAHAN UNTUK MENCARI GAMBAR STATIS ---
    lapangan_list_processed = []
    for lapangan in lapangan_queryset:
        # Coba cari path gambar statis spesifik berdasarkan ID
        possible_static_path_png = f'images/lapangan{lapangan.pk}.png'
        possible_static_path_jpg = f'images/lapangan{lapangan.pk}.jpg'

        found_static_path = None
        # Gunakan find() untuk memeriksa keberadaan file di semua direktori static
        if find(possible_static_path_png):
             found_static_path = possible_static_path_png
        elif find(possible_static_path_jpg):
             found_static_path = possible_static_path_jpg

        # Tambahkan path yang ditemukan (atau None) sebagai atribut baru ke objek
        lapangan.static_image_path = found_static_path
        lapangan_list_processed.append(lapangan)
    # ----------------------------------------------------

    # === Pagination (Gunakan list yang sudah diproses) ===
    paginator = Paginator(lapangan_list_processed, 16) # Gunakan lapangan_list_processed
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Ambil daftar jenis unik (bisa dari queryset awal sebelum diproses)
    jenis_list = Lapangan.objects.values_list('jenis_olahraga', flat=True).distinct().order_by('jenis_olahraga')

    context = {
        'page_obj': page_obj, # page_obj sekarang berisi lapangan dengan atribut static_image_path
        'jenis_list': jenis_list,
        'selected_jenis': jenis_filter,
        'selected_rating': rating_filter,
        'show_navbar':True,
    }
    return render(request, 'landing_page.html', context)

logger = logging.getLogger(__name__)
def proxy_image(request):
    """
    Proxy untuk load images dari external URLs dengan proper error handling
    """
    image_url = request.GET.get('url')
    
    if not image_url:
        logger.error("Proxy image: No URL provided")
        return HttpResponse('No URL provided', status=400)

    # Decode URL yang mungkin di-encode multiple times
    image_url = unquote(image_url)
    
    # DEBUG: Log URL yang diminta
    logger.info(f"Proxy image request: {image_url}")

    # SANITIZE: Handle double protocol
    if "http://" in image_url[1:] or "https://" in image_url[1:]:
        idx = max(image_url.rfind("http://"), image_url.rfind("https://"))
        image_url = image_url[idx:]
        logger.warning(f"Sanitized double protocol URL to: {image_url}")

    # VALIDASI URL
    try:
        parsed = urlparse(image_url)
        if not parsed.scheme or not parsed.netloc:
            logger.error(f"Invalid URL structure: {image_url}")
            return HttpResponse('Invalid image URL', status=400)
    except Exception as e:
        logger.error(f"URL parsing error: {e}")
        return HttpResponse('Malformed URL', status=400)

    # FETCH IMAGE
    try:
        # Set headers untuk mimic browser request
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
        }
        
        response = requests.get(
            image_url, 
            timeout=15,  # Increased timeout untuk deployment
            headers=headers,
            verify=True,  # Verify SSL certificates
        )
        response.raise_for_status()

        # Get content type
        content_type = response.headers.get('Content-Type', 'image/jpeg')
        
        # Validate it's actually an image
        if not content_type.startswith('image/'):
            logger.error(f"URL is not an image: {content_type}")
            return HttpResponse('URL does not point to an image', status=400)

        logger.info(f"Successfully proxied image: {image_url}")
        
        # Return image with proper headers
        http_response = HttpResponse(response.content, content_type=content_type)
        http_response['Cache-Control'] = 'public, max-age=86400'  # Cache for 24 hours
        return http_response

    except requests.Timeout:
        logger.error(f"Timeout fetching image: {image_url}")
        return HttpResponse('Image request timeout', status=504)
    
    except requests.ConnectionError as e:
        logger.error(f"Connection error: {e}")
        return HttpResponse('Cannot connect to image server', status=502)
    
    except requests.HTTPError as e:
        logger.error(f"HTTP error fetching image: {e}")
        return HttpResponse(f'Image not found: {e}', status=e.response.status_code)
    
    except Exception as e:
        logger.error(f"Unexpected error fetching image: {str(e)}")
        return HttpResponse(f'Error fetching image: {str(e)}', status=500)
    

def get_lapangan_list(request):
    """
    API endpoint untuk Flutter - return list lapangan dengan image path (relative path only)
    
    Response format:
    [
        {
            "id": 1,
            "name": "Futsal Arena Senayan",
            "type": "Futsal",
            "location": "Jakarta Pusat",
            "price": 150000,
            "rating": 4.5,
            "image": "/media/lapangan_images/foto.jpg",  # RELATIVE PATH
            "review_count": 10
        },
        ...
    ]
    """
    # Get all lapangan, ordered by primary key
    lapangan_queryset = Lapangan.objects.all().order_by('pk')
    
    data = []
    
    for field in lapangan_queryset:
        # ====================================
        # IMAGE PATH LOGIC - Return RELATIVE PATH only!
        # ====================================
        image_path = ""
        
        # Priority 1: Check if field has uploaded image (foto_utama)
        if field.foto_utama:
            # foto_utama.url returns relative path like "/media/lapangan_images/foto.jpg"
            image_path = field.foto_utama.url
            print(f"✅ Using foto_utama for {field.nama_lapangan}: {image_path}")
        
        else:
            # Priority 2: Fallback to static images
            # Check for PNG first, then JPG
            static_png = f'images/lapangan{field.pk}.png'
            static_jpg = f'images/lapangan{field.pk}.jpg'
            
            if find(static_png):
                image_path = f'/static/images/lapangan{field.pk}.png'
                print(f"✅ Using static PNG for {field.nama_lapangan}: {image_path}")
            
            elif find(static_jpg):
                image_path = f'/static/images/lapangan{field.pk}.jpg'
                print(f"✅ Using static JPG for {field.nama_lapangan}: {image_path}")
            
            else:
                # No image found - leave empty
                print(f"⚠️ No image found for {field.nama_lapangan} (ID: {field.pk})")
                image_path = ""
        
        # ====================================
        # BUILD RESPONSE DATA
        # ====================================
        data.append({
            "id": field.pk,
            "name": field.nama_lapangan,
            "type": field.jenis_olahraga,
            "location": field.lokasi,
            "price": int(field.harga_per_jam),
            "rating": float(field.rating),
            "image": image_path,  # ✅ ALWAYS RELATIVE PATH (e.g., "/media/..." or "/static/...")
            "review_count": field.jumlah_ulasan
        })
    
    print(f"📊 Returning {len(data)} lapangan entries")
    return JsonResponse(data, safe=False)