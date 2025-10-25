from django.shortcuts import render
from django.core.paginator import Paginator
from booking.models import Lapangan
from django.templatetags.static import static
from django.contrib.staticfiles.finders import find
import os

def show_landing_page(request):
    """Menampilkan Landing Page Lapang.in dengan daftar lapangan dan pagination."""
    jenis_filter = request.GET.get('jenis', 'all')
    rating_filter = request.GET.get('rating', 'all')

    # Ambil queryset awal dan PASTIKAN ADA URUTAN (misal berdasarkan ID)
    # Ini juga mengatasi UnorderedObjectListWarning
    lapangan_queryset = Lapangan.objects.all().order_by('pk') # <-- TAMBAHKAN .order_by('pk')

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