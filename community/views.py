# pbp-kelompok-d06/lapangin/lapangin-feat-admin-dashboard/community/views.py

import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse, JsonResponse # ✅ TAMBAHKAN JsonResponse
from django.core import serializers
from django.db.models import Q, Count
from .models import Community, CommunityMember, CommunityPost, PostComment, CommunityRequest
from django.views.decorators.csrf import csrf_exempt
import base64
import uuid
from django.core.files.base import ContentFile
# 🔽 (Hapus render_to_string jika ada, kita tidak membutuhkannya di sini)

def is_pemilik(user):
    """Cek apakah user adalah PEMILIK"""
    return hasattr(user, 'profile') and user.profile.role == 'PEMILIK'

# ==================== PUBLIC VIEWS ====================
# ... (view show_community_page, community_detail, join_community, leave_community tidak berubah) ...
def show_community_page(request):
    """Halaman utama community - tampilan public"""
    jenis_filter = request.GET.get('jenis', '')
    lokasi_filter = request.GET.get('lokasi', '')
    search = request.GET.get('search', '')
    
    communities = Community.objects.filter(is_active=True).annotate(
        total_members=Count('members', filter=Q(members__is_active=True))
    )
    
    if jenis_filter:
        communities = communities.filter(sports_type=jenis_filter)
    if lokasi_filter:
        communities = communities.filter(location__icontains=lokasi_filter)
    if search:
        communities = communities.filter(
            Q(community_name__icontains=search) | Q(description__icontains=search)
        )
    
    context = {
        'communities': communities,
        'show_navbar': True,
        'jenis_choices': Community.CATEGORY_CHOICES, 
        'current_jenis': jenis_filter,             
        'current_lokasi': lokasi_filter,           
        'current_search': search,                  
    }
    return render(request, 'community.html', context)


def community_detail(request, pk):
    """Detail komunitas dengan forum"""
    community = get_object_or_404(Community, pk=pk, is_active=True)
    
    # Cek apakah user sudah join
    is_member = False
    if request.user.is_authenticated:
        is_member = CommunityMember.objects.filter(
            community=community, 
            user=request.user,
            is_active=True
        ).exists()
    
    # Ambil posts
    posts = CommunityPost.objects.filter(community=community).select_related(
        'user'
    ).prefetch_related('comments__user')[:20]
    
    # Update member count (sinkronisasi)
    community.member_count = community.members.filter(is_active=True).count()
    community.save()
    
    # Komunitas lainnya
    other_communities = Community.objects.filter(
        is_active=True
    ).exclude(pk=pk)[:3]
    
    context = {
        'community': community,
        'is_member': is_member,
        'posts': posts,
        'communities': other_communities,
        'show_navbar': True,
    }
    return render(request, 'community_detail.html', context)


@login_required
def join_community(request, pk):
    """Join komunitas"""
    community = get_object_or_404(Community, pk=pk, is_active=True)
    
    # Cek apakah sudah full
    if community.member_count >= community.max_member:
        messages.error(request, 'Komunitas sudah penuh!')
        return redirect('community:show_detail_community', pk=pk)
    
    # Cek apakah sudah join
    member, created = CommunityMember.objects.get_or_create(
        community=community,
        user=request.user,
        defaults={'is_active': True}
    )
    
    if not created:
        if member.is_active:
            messages.info(request, 'Anda sudah menjadi anggota komunitas ini.')
        else:
            member.is_active = True
            member.save()
            # Update member count
            community.member_count = community.members.filter(is_active=True).count()
            community.save()
            messages.success(request, f'Selamat! Anda berhasil bergabung kembali dengan {community.community_name}')
    else:
        # Update member count
        community.member_count = community.members.filter(is_active=True).count()
        community.save()
        messages.success(request, f'Selamat! Anda berhasil bergabung dengan {community.community_name}')
    
    return redirect('community:show_detail_community', pk=pk)


@login_required
def leave_community(request, pk):
    """Leave komunitas"""
    community = get_object_or_404(Community, pk=pk)
    
    try:
        member = CommunityMember.objects.get(
            community=community,
            user=request.user
        )
        member.is_active = False
        member.save()
        
        # Update member count
        community.member_count = community.members.filter(is_active=True).count()
        community.save()
        
        messages.success(request, f'Anda telah keluar dari {community.community_name}')
    except CommunityMember.DoesNotExist:
        messages.error(request, 'Anda bukan anggota komunitas ini.')
    
    return redirect('community:show_community_page')

# ==================== FORUM FEATURES ====================

@login_required
def post_create(request, pk):
    """Buat post baru di komunitas (Handle AJAX)"""
    community = get_object_or_404(Community, pk=pk)
    # ✅ Cek apakah ini request AJAX
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    if not CommunityMember.objects.filter(community=community, user=request.user, is_active=True).exists():
        if is_ajax:
            return JsonResponse({'success': False, 'error': 'Anda harus menjadi anggota untuk membuat post.'}, status=403)
        messages.error(request, 'Anda harus menjadi anggota untuk membuat post.')
        return redirect('community:show_community_page', pk=pk)

    if request.method == 'POST':
        content = request.POST.get('content', '').strip()
        image = request.FILES.get('image')

        if not content:
            if is_ajax:
                return JsonResponse({'success': False, 'error': 'Konten post tidak boleh kosong.'}, status=400)
            messages.error(request, 'Konten post tidak boleh kosong.')
            return redirect('community:show_community_page', pk=pk)

        post = CommunityPost.objects.create(
            community=community,
            user=request.user,
            content=content,
            image=image
        )

        if is_ajax:
            # ✅ Kembalikan data JSON, bukan HTML
            return JsonResponse({
                'success': True,
                'post': {
                    'pk': post.pk,
                    'content': post.content,
                    'image_url': post.image.url if post.image else None,
                    'created_at': post.created_at.strftime("%d %b %Y, %H:%M"),
                    'user': {
                        'username': post.user.username,
                        'initial': post.user.username[0].upper()
                    },
                    'delete_url': f"/community/post/{post.pk}/delete/", # Asumsi dari urls.py
                    'comment_url': f"/community/post/{post.pk}/comment/" # Asumsi dari urls.py
                }
            })

        messages.success(request, 'Post berhasil dibuat!')
    
    return redirect('community:show_community_page', pk=pk)


@login_required
def post_delete(request, pk):
    """Hapus post"""
    post = get_object_or_404(CommunityPost, pk=pk)
    
    # Hanya pembuat post atau admin yang bisa hapus
    if post.user != request.user and not is_pemilik(request.user):
        messages.error(request, 'Anda tidak memiliki izin untuk menghapus post ini.')
        return redirect('community:show_detail_community', pk=post.community.pk)
    
    community_pk = post.community.pk
    post.delete()
    messages.success(request, 'Post berhasil dihapus.')
    
    return redirect('community:show_detail_community', pk=community_pk)


@login_required
def comment_create(request, pk):
    """Buat komentar pada post (Handle AJAX)"""
    post = get_object_or_404(CommunityPost, pk=pk)
    # ✅ Cek apakah ini request AJAX
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    if not CommunityMember.objects.filter(community=post.community, user=request.user, is_active=True).exists():
        if is_ajax:
            return JsonResponse({'success': False, 'error': 'Anda harus menjadi anggota untuk berkomentar.'}, status=403)
        messages.error(request, 'Anda harus menjadi anggota untuk berkomentar.')
        return redirect('community:show_detail_community', pk=post.community.pk)
    
    if request.method == 'POST':
        content = request.POST.get('content', '').strip()
        if content:
            comment = PostComment.objects.create(
                post=post,
                user=request.user,
                content=content
            )

            if is_ajax:
                # ✅ Kembalikan data JSON
                return JsonResponse({
                    'success': True,
                    'comment': {
                        'content': comment.content,
                        'created_at': comment.created_at.strftime("%d %b %Y, %H:%M"),
                        'user': {
                            'username': comment.user.username,
                            'initial': comment.user.username[0].upper()
                        }
                    }
                })

            messages.success(request, 'Komentar berhasil ditambahkan!')
        else:
            if is_ajax:
                return JsonResponse({'success': False, 'error': 'Komentar tidak boleh kosong.'}, status=400)
            messages.error(request, 'Komentar tidak boleh kosong.')
    
    return redirect('community:show_detail_community', pk=post.community.pk)


# ==================== REQUEST KOMUNITAS (MEMBER) ====================
# ... (sisa view tidak berubah) ...
@login_required
def request_community_create(request):
    """Member membuat request komunitas baru"""
    if request.method == 'POST':
        CommunityRequest.objects.create(
            requester=request.user,
            community_name=request.POST.get('community_name'),
            description=request.POST.get('description'),
            sports_type=request.POST.get('sports_type'),
            location_preference=request.POST.get('location_preference')
        )
        messages.success(request, 'Request komunitas berhasil dikirim! Tunggu persetujuan admin.')
        return redirect('my_community_requests')
    
    context = {'show_navbar': True}
    return render(request, 'community_request_create.html', context)


@login_required
def my_community_requests(request):
    """Daftar request komunitas user"""
    requests = CommunityRequest.objects.filter(requester=request.user)
    context = {
        'requests': requests,
        'show_navbar': True,
    }
    return render(request, 'my_community_requests.html', context)


# ==================== ADMIN VIEWS (untuk Admin Dashboard) ====================

@login_required
@user_passes_test(is_pemilik)
def admin_community_list(request):
    # Ambil nilai filter dari URL (request.GET)
    jenis_filter = request.GET.get('jenis', '')
    lokasi_filter = request.GET.get('lokasi', '')

    # Mulai dengan semua komunitas
    community_list = Community.objects.all() 

    # Terapkan filter jika ada
    if jenis_filter:
        community_list = community_list.filter(sports_type=jenis_filter)
    
    if lokasi_filter:
        # Gunakan __icontains untuk pencarian yang tidak case-sensitive
        community_list = community_list.filter(location__icontains=lokasi_filter)

    # === HANDLE MOBILE / JSON RESPONSE ===
    # Cek header Accept atau parameter format=json untuk mendeteksi request dari Flutter
    if request.headers.get('Accept') == 'application/json' or request.GET.get('format') == 'json':
        data = []
        for c in community_list:
            data.append({
                'pk': c.pk,
                'community_name': c.community_name,
                'description': c.description,
                'location': c.location,
                'sports_type': c.sports_type,
                'member_count': c.member_count,
                'max_member': c.max_member,
                # Handle image_url
                'image_url': c.community_image.url if c.community_image else "",
                'contact_person_name': c.contact_person_name,
                'contact_phone': c.contact_phone,
                'created_by': c.created_by.username,
                'created_at': c.date_added.strftime("%Y-%m-%d") if hasattr(c, 'date_added') else "",
            })
        return JsonResponse({'status': True, 'data': data})

    # Kirim data yang sudah difilter ke template (WEB)
    context = {
        'community_list': community_list
    }
    
    return render(request, 'admin_community_list.html', context)


@login_required
@user_passes_test(is_pemilik)
def admin_community_create(request):
    """Admin membuat komunitas baru"""
    if request.method == 'POST':
        try:
            community = Community.objects.create(
                community_name=request.POST.get('community_name'),
                description=request.POST.get('description'),
                location=request.POST.get('location'),
                sports_type=request.POST.get('sports_type'),
                max_member=request.POST.get('max_member', 50),
                contact_person_name=request.POST.get('contact_person_name', request.user.username),
                contact_phone=request.POST.get('contact_phone', ''),
                created_by=request.user
            )
            
            if request.FILES.get('community_image'):
                community.community_image = request.FILES['community_image']
                community.save()
            
            messages.success(request, 'Komunitas berhasil dibuat!')
            return redirect('community:admin_community_list')
            
        except Exception as e:
            messages.error(request, f'Terjadi kesalahan: {str(e)}')
    
    return render(request, 'admin_community_form.html')


@login_required
@user_passes_test(is_pemilik)
@csrf_exempt
def admin_community_edit(request, pk):
    """
    Unified Endpoint untuk Edit Komunitas
    - Handle Web Request (HTML Form) -> URL: /community/admin/<pk>/edit/
    - Handle Mobile Request (JSON/API) -> URL: /community/api/<pk>/edit-flutter/
    """
    # Deteksi apakah request berasal dari Mobile/API (biasanya ada header khusus atau content-type json)
    # Kita bisa cek content-type atau header X-Requested-With, atau sekadar asumsi dari path (tapi ini satu view)
    # Cara paling aman: Cek Accept header atau Content-Type
    is_mobile_api = request.content_type == 'application/json' or request.headers.get('X-Requested-With') == 'XMLHttpRequest' or 'api/' in request.path

    # 2. Validasi Authorization (Owner / Superuser)
    if community.created_by != request.user and not request.user.is_superuser:
        if is_mobile_api:
             return JsonResponse({'status': False, 'message': 'Anda tidak memiliki izin mengedit komunitas ini.'}, status=403)
        messages.error(request, 'Anda tidak memiliki izin mengedit komunitas ini.')
        return redirect('community:admin_community_list')

    # === HANDLE POST REQUEST (UPDATE DATA) ===
    if request.method == 'POST':
        try:
            # Init data container
            data = {}
            if request.content_type == 'application/json':
                data = json.loads(request.body)
            else:
                data = request.POST

            # Update Fields
            # Gunakan .get() dengan default value dari instance existing
            community.community_name = data.get('community_name', community.community_name)
            community.description = data.get('description', community.description)
            community.location = data.get('location', community.location)
            community.sports_type = data.get('sports_type', community.sports_type)
            
            # Handle max_member (perlu casting int)
            if 'max_member' in data:
                 try:
                    community.max_member = int(data.get('max_member'))
                 except ValueError:
                     pass # abaikan jika tidak valid

            community.contact_person_name = data.get('contact_person', data.get('contact_person_name', community.contact_person_name))
            community.contact_phone = data.get('contact_phone', community.contact_phone)
            
            # Handle Image Update
            # Prioritas 1: File Upload (Multipart via Web atau Mobile Multipart)
            if request.FILES.get('community_image') or request.FILES.get('image'):
                image_file = request.FILES.get('community_image') or request.FILES.get('image')
                community.community_image = image_file
            
            # Prioritas 2: Base64 String (Mobile JSON)
            elif data.get('image'):
                image_data = data.get('image')
                try:
                    if ";base64," in image_data:
                        format, imgstr = image_data.split(';base64,') 
                        ext = format.split('/')[-1] 
                    else:
                        imgstr = image_data
                        ext = "jpg"
                    file_name = f"{request.user.username}_{uuid.uuid4()}.{ext}"
                    data_img = ContentFile(base64.b64decode(imgstr), name=file_name)
                    community.community_image = data_img
                except Exception as e:
                    print(f"Error decoding image: {e}")

            community.save()

            if is_mobile_api:
                return JsonResponse({'status': True, 'message': 'Community updated successfully'})
            else:
                messages.success(request, 'Komunitas berhasil diperbarui!')
                return redirect('community:admin_community_list')
            
        except Exception as e:
            if is_mobile_api:
                return JsonResponse({'status': False, 'message': str(e)}, status=400)
            else:
                messages.error(request, f'Terjadi kesalahan: {str(e)}')
                # Fallthrough ke render form ulang

    # === HANDLE GET REQUEST (FORM DISPLAY) ===
    # Mobile API biasanya tidak minta GET form, tapi kalau minta detail bisa dihandle terpisah.
    # Di sini kita asumsikan GET adalah untuk Web Form.
    
    if is_mobile_api and request.method != 'POST':
         return JsonResponse({'status': False, 'message': 'Method not allowed for API'}, status=405)

    context = {
        'community': community,
        'is_edit': True
    }
    return render(request, 'admin_community_form.html', context)


@login_required
@user_passes_test(is_pemilik)
def admin_community_delete(request, pk):
    """Hapus komunitas"""
    community = get_object_or_404(Community, pk=pk)
    
    if request.method == 'POST':
        community.delete()
        messages.success(request, 'Komunitas berhasil dihapus!')
        return redirect('community:admin_community_list')
    
    return render(request, 'admin_community_confirm_delete.html', {'community': community})


@login_required
@user_passes_test(is_pemilik)
def admin_request_list(request):
    """Daftar request komunitas dari member"""
    requests = CommunityRequest.objects.filter(status='pending')
    
    context = {'requests': requests}
    return render(request, 'admin_request_list.html', context)


@login_required
@user_passes_test(is_pemilik)
def admin_request_approve(request, pk):
    """Approve request dan buat komunitas baru"""
    req = get_object_or_404(CommunityRequest, pk=pk)
    
    if request.method == 'POST':
        Community.objects.create(
            community_name=req.community_name,
            description=req.description,
            location=req.location_preference,
            sports_type=req.sports_type,
            max_member=50,
            contact_person_name=request.user.username,
            contact_phone='',
            created_by=request.user
        )
        
        req.status = 'approved'
        req.admin_notes = request.POST.get('admin_notes', '')
        req.save()
        
        messages.success(request, 'Request berhasil diapprove dan komunitas telah dibuat!')
        return redirect('admin_request_list')
    
    return render(request, 'admin_request_approve.html', {'request': req})


@login_required
@user_passes_test(is_pemilik)
def admin_request_reject(request, pk):
    """Reject request komunitas"""
    req = get_object_or_404(CommunityRequest, pk=pk)
    
    if request.method == 'POST':
        req.status = 'rejected'
        req.admin_notes = request.POST.get('admin_notes', '')
        req.save()
        
        messages.success(request, 'Request berhasil ditolak!')
        return redirect('admin_request_list')
    
    return render(request, 'admin_request_reject.html', {'request': req})


# ==================== EXISTING VIEWS  ====================

def delete_community(request, pk):
    community = get_object_or_404(Community, pk=pk)
    if request.method == 'POST':
        community.delete()
        return redirect('show_community_page')
    return render(request, 'delete_community.html', {'community': community})


def search_communities(request):
    query = request.GET.get('q')
    if query:
        communities = Community.objects.filter(community_name__icontains=query)
    else:
        communities = Community.objects.all()
    return render(request, 'community.html', {'communities': communities})


def filter_communities_by_sport(request, sport_type):
    communities = Community.objects.filter(sports_type=sport_type)
    return render(request, 'community.html', {'communities': communities})


def show_xml(request):
    data = serializers.serialize("xml", Community.objects.all())
    return HttpResponse(data, content_type="application/xml")


def show_json(request):
    data = serializers.serialize("json", Community.objects.all())
    return HttpResponse(data, content_type="application/json")


def show_xml_by_id(request, id):
    data = serializers.serialize("xml", Community.objects.filter(pk=id))
    return HttpResponse(data, content_type="application/xml")


def show_json_by_id(request, id):
    data = serializers.serialize("json", Community.objects.filter(pk=id))
    return HttpResponse(data, content_type="application/json")

def show_json_all_communities(request):
    """
    GET: Mengembalikan list semua komunitas dengan detail lengkap.
    URL: /community/api/communities/
    """
    communities = Community.objects.filter(is_active=True)
    data = []
    
    for c in communities:
        data.append({
            'pk': c.pk,
            'community_name': c.community_name,
            'description': c.description,
            'location': c.location,
            'sports_type': c.sports_type,
            'member_count': c.members.filter(is_active=True).count(), 
            'max_member': c.max_member,
            'image_url': c.community_image.url if c.community_image else "", # Handle gambar kosong
            'contact_person': c.contact_person_name,
            'contact_phone': c.contact_phone,
            'created_by': c.created_by.username,
            'date_added': c.date_added.strftime("%Y-%m-%d"), 
        })
    
    return JsonResponse(data, safe=False)

def show_json_community_posts(request, pk):
    """
    GET: Mengembalikan list post dalam satu komunitas BESERTA KOMENTARNYA.
    URL: /community/api/community/<pk>/posts/
    """
    community = get_object_or_404(Community, pk=pk)
    
    # Tambahkan prefetch_related('comments__user') agar query database efisien
    posts = CommunityPost.objects.filter(community=community)\
        .select_related('user')\
        .prefetch_related('comments__user')\
        .order_by('-created_at')
    
    data = []
    for post in posts:
        # --- 1. AMBIL LIST KOMENTAR ---
        comments_data = []
        for comment in post.comments.all().order_by('created_at'):
            comments_data.append({
                'pk': comment.pk,
                'username': comment.user.username, 
                'content': comment.content,
                'created_at': comment.created_at.strftime("%Y-%m-%d %H:%M")
            })
        
        # --- 2. MASUKKAN KE DATA POST ---
        data.append({
            'pk': post.pk,
            # Ubah struktur user jadi flat string biar gampang di Flutter
            'username': post.user.username, 
            'content': post.content,
            'image_url': post.image.url if post.image else None,
            'created_at': post.created_at.strftime("%Y-%m-%d %H:%M"),
            'comments_count': post.comments.count(),
            'comments': comments_data, # <--- INI WAJIB ADA
        })
        
    return JsonResponse({
        'community_pk': community.pk,
        'community_name': community.community_name,
        'posts': data
    })

def show_json_post_comments(request, post_id):
    """
    GET: Mengembalikan semua komentar di sebuah post.
    URL: /community/api/post/<post_id>/comments/
    """
    post = get_object_or_404(CommunityPost, pk=post_id)
    comments = PostComment.objects.filter(post=post).select_related('user').order_by('created_at')
    
    data = []
    for comment in comments:
        data.append({
            'pk': comment.pk,
            'user': {
                'username': comment.user.username,
            },
            'content': comment.content,
            'created_at': comment.created_at.strftime("%Y-%m-%d %H:%M")
        })
        
    return JsonResponse({'comments': data})

@login_required
def show_json_my_requests(request):
    """
    GET: Mengembalikan daftar request komunitas user (perlu login).
    URL: /community/api/my-requests/
    """
    requests = CommunityRequest.objects.filter(requester=request.user)
    data = []
    
    for req in requests:
        data.append({
            'community_name': req.community_name,
            'sports_type': req.sports_type,
            'status': req.status,
            'request_date': req.request_date.strftime("%d %b %Y"),
            'admin_notes': req.admin_notes
        })
        
    return JsonResponse(data, safe=False)

@csrf_exempt
def create_community_flutter(request):
    """
    Endpoint khusus untuk membuat komunitas dari Mobile (Flutter)
    Mendukung upload gambar via Base64 JSON.
    """
    if request.method == 'POST':
        try:
            # Handle JSON Body
            if request.content_type == 'application/json':
                data = json.loads(request.body)
            else:
                data = request.POST

            if not request.user.is_authenticated:
                 return JsonResponse({'status': False, 'message': 'Authentication required'}, status=401)

            # Ambil data text
            community_name = data.get('community_name')
            description = data.get('description')
            location = data.get('location')
            sports_type = data.get('sports_type', 'futsal')
            max_member = int(data.get('max_member', 50))
            
            # Key dari Flutter adalah 'contact_person', kita map ke 'contact_person_name'
            contact_person_name = data.get('contact_person', request.user.username) 
            contact_phone = data.get('contact_phone', '')
            image_data = data.get('image') # Base64 String

            # Validasi Dasar
            if not community_name or not description:
                 return JsonResponse({'status': False, 'message': 'Nama dan Deskripsi wajib diisi'}, status=400)

            # Buat Object Community (Tanpa Gambar Dulu)
            new_community = Community(
                community_name=community_name,
                description=description,
                location=location,
                sports_type=sports_type,
                max_member=max_member,
                contact_person_name=contact_person_name, 
                contact_phone=contact_phone,
                created_by=request.user,
                is_active=True,
                member_count=1 # Member pertama adalah creator
            )

            # Handle Gambar Base64
            if image_data:
                try:
                    # Bersihkan header data URI scheme jika ada
                    if ";base64," in image_data:
                        format, imgstr = image_data.split(';base64,') 
                        ext = format.split('/')[-1] 
                    else:
                        imgstr = image_data
                        ext = "jpg"

                    file_name = f"{request.user.username}_{uuid.uuid4()}.{ext}"
                    data_img = ContentFile(base64.b64decode(imgstr), name=file_name)
                    
                    # Simpan ke field image (sesuaikan nama field di model, sepertinya 'community_image')
                    new_community.community_image = data_img 
                except Exception as e:
                    print(f"Error decoding image: {e}")

            new_community.save()
            
            # Otomatis jadikan creator sebagai member
            CommunityMember.objects.create(
                community=new_community,
                user=request.user,
                is_active=True
            )
            
            # Return status True (boolean) agar terbaca sukses di flutter
            return JsonResponse({'status': True, 'message': 'Community created successfully', 'pk': new_community.pk})
        
        except Exception as e:
            return JsonResponse({'status': False, 'message': str(e)}, status=400)
            
    return JsonResponse({'status': False, 'message': 'Method not allowed'}, status=405)

@csrf_exempt
def join_community_flutter(request, pk):
    if request.method != "POST":
        return JsonResponse({"status": "error", "message": "Invalid method"}, status=405)

    try:
        if not request.user.is_authenticated:
            return JsonResponse({'status': 'error', 'message': 'Authentication required'}, status=401)

        community = get_object_or_404(Community, pk=pk, is_active=True)

        member, created = CommunityMember.objects.get_or_create(
            user=request.user,
            community=community,
            defaults={'is_active': True},
        )

        # Kalau sudah ada tapi is_active False → aktifkan lagi
        if not created and not member.is_active:
            member.is_active = True
            member.save()

        # Sinkron member_count
        community.member_count = community.members.filter(is_active=True).count()
        community.save()

        msg = "Berhasil join" if created or not member.is_active else "Kamu sudah terdaftar"
        return JsonResponse({"status": "success", "message": msg})

    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)

@csrf_exempt
def leave_community_flutter(request, pk):
    """
    Endpoint untuk leave komunitas via Mobile
    URL: /community/api/<pk>/leave-flutter/
    """
    if request.method == 'POST':
        try:
            if not request.user.is_authenticated:
                return JsonResponse({'status': 'error', 'message': 'Authentication required'}, status=401)

            community = get_object_or_404(Community, pk=pk)
            
            member = CommunityMember.objects.get(community=community, user=request.user)
            member.is_active = False
            member.save()

            # Update counter
            community.member_count = community.members.filter(is_active=True).count()
            community.save()

            return JsonResponse({'status': 'success', 'message': f'Anda telah keluar dari {community.community_name}'})

        except CommunityMember.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Anda bukan anggota komunitas ini.'}, status=404)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
            
    return JsonResponse({'status': 'error', 'message': 'Method not allowed'}, status=405)


@csrf_exempt
def delete_post_flutter(request, pk):
    """
    Endpoint untuk menghapus post sendiri via Mobile
    URL: /community/api/post/<pk>/delete-flutter/
    """
    if request.method == 'POST':
        try:
            if not request.user.is_authenticated:
                 return JsonResponse({'status': 'error', 'message': 'Authentication required'}, status=401)

            post = get_object_or_404(CommunityPost, pk=pk)

            # Validasi kepemilikan
            if post.user != request.user:
                return JsonResponse({'status': 'error', 'message': 'Anda tidak memiliki izin menghapus post ini.'}, status=403)

            post.delete()
            return JsonResponse({'status': 'success', 'message': 'Post berhasil dihapus'})

        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

    return JsonResponse({'status': 'error', 'message': 'Method not allowed'}, status=405)


@csrf_exempt
def create_request_flutter(request):
    """
    Endpoint untuk Member merequest komunitas baru (bukan langsung jadi)
    URL: /community/api/request-flutter/
    """
    if request.method == 'POST':
        try:
            if not request.user.is_authenticated:
                return JsonResponse({'status': 'error', 'message': 'Authentication required'}, status=401)

            if request.content_type == 'application/json':
                data = json.loads(request.body)
            else:
                data = request.POST

            # Buat Request Baru
            CommunityRequest.objects.create(
                requester=request.user,
                community_name=data.get('community_name'),
                description=data.get('description'),
                sports_type=data.get('sports_type'),
                location_preference=data.get('location_preference')
            )

            return JsonResponse({'status': 'success', 'message': 'Request komunitas berhasil dikirim!'})

        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

    return JsonResponse({'status': 'error', 'message': 'Method not allowed'}, status=405)


@csrf_exempt
def create_post_flutter(request, pk):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Method not allowed'}, status=405)

    try:
        if not request.user.is_authenticated:
            return JsonResponse({'status': 'error', 'message': 'Authentication required'}, status=401)

        community = get_object_or_404(Community, pk=pk, is_active=True)

        # WAJIB: cek member aktif
        is_member = CommunityMember.objects.filter(
            community=community,
            user=request.user,
            is_active=True,
        ).exists()
        if not is_member:
            return JsonResponse({'status': 'error', 'message': 'Anda harus menjadi anggota untuk membuat post.'}, status=403)

        # Terima JSON dari Flutter
        if request.content_type == 'application/json':
            data = json.loads(request.body)
        else:
            data = request.POST

        content = data.get('content', '').strip()
        image_b64 = data.get('image')

        if not content:
            return JsonResponse({'status': 'error', 'message': 'Konten tidak boleh kosong.'}, status=400)

        image_file = None
        if image_b64:
            try:
                if ';base64,' in image_b64:
                    fmt, imgstr = image_b64.split(';base64,')
                    ext = fmt.split('/')[-1]
                else:
                    imgstr = image_b64
                    ext = 'jpg'
                file_name = f"{request.user.username}_{uuid.uuid4()}.{ext}"
                image_file = ContentFile(base64.b64decode(imgstr), name=file_name)
            except Exception as e:
                print(f"Error decoding image: {e}")

        post = CommunityPost.objects.create(
            community=community,
            user=request.user,
            content=content,
            image=image_file,
        )

        return JsonResponse({
            'status': 'success',
            'message': 'Post berhasil dibuat!',
            'post': {
                'pk': post.pk,
                'username': post.user.username,
                'content': post.content,
                'image_url': post.image.url if post.image else None,
                'created_at': post.created_at.strftime("%Y-%m-%d %H:%M"),
                'comments_count': 0,
                'comments': [],
            }
        })

    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

@csrf_exempt
def create_comment_flutter(request, post_id):
    """
    Endpoint untuk membuat komentar pada post via Mobile
    URL: /community/api/post/<post_id>/comment-flutter/
    """
    if request.method == 'POST':
        try:
            if not request.user.is_authenticated:
                return JsonResponse({'status': 'error', 'message': 'Authentication required'}, status=401)

            post = get_object_or_404(CommunityPost, pk=post_id)

            # Cek apakah user adalah member komunitas
            if not CommunityMember.objects.filter(community=post.community, user=request.user, is_active=True).exists():
                return JsonResponse({'status': 'error', 'message': 'Anda harus menjadi anggota untuk berkomentar.'}, status=403)

            # Handle JSON or Form data
            content = ''
            if request.content_type == 'application/json':
                data = json.loads(request.body)
                content = data.get('content', '').strip()
            else:
                content = request.POST.get('content', '').strip()

            if not content:
                return JsonResponse({'status': 'error', 'message': 'Komentar tidak boleh kosong.'}, status=400)

            comment = PostComment.objects.create(
                post=post,
                user=request.user,
                content=content
            )

            return JsonResponse({
                'status': 'success', 
                'message': 'Komentar berhasil ditambahkan!',
                'comment': {
                    'pk': comment.pk,
                    'content': comment.content,
                    'created_at': comment.created_at.strftime("%d %b %Y, %H:%M"),
                    'user': {
                        'username': comment.user.username
                    }
                }
            })

        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

    return JsonResponse({'status': 'error', 'message': 'Method not allowed'}, status=405)

@csrf_exempt
def check_community_membership(request, pk):
    """
    Endpoint untuk mengecek apakah user sudah menjadi member komunitas ini.
    URL: /community/api/<pk>/check-membership/
    """
    if request.method == 'GET':
        try:
            if not request.user.is_authenticated:
                return JsonResponse({'status': 'error', 'message': 'Authentication required'}, status=401)

            community = get_object_or_404(Community, pk=pk)
            
            # Cek status member
            is_member = CommunityMember.objects.filter(
                community=community, 
                user=request.user, 
                is_active=True
            ).exists()

            return JsonResponse({
                'status': 'success', 
                'is_joined': is_member,
                'member_count': community.member_count # Kirim juga jumlah member terbaru
            })

        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

    return JsonResponse({'status': 'error', 'message': 'Method not allowed'}, status=405)