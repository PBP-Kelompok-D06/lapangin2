# pbp-kelompok-d06/lapangin/lapangin-feat-admin-dashboard/community/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import HttpResponse, JsonResponse # ✅ TAMBAHKAN JsonResponse
from django.core import serializers
from django.db.models import Q, Count
from .models import Community, CommunityMember, CommunityPost, PostComment, CommunityRequest
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

    # Kirim data yang sudah difilter ke template
    context = {
        'community_list': community_list
        # Kita tidak perlu mengirim 'jenis_filter' dan 'lokasi_filter' 
        # karena template sudah membacanya dari 'request.GET'
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
def admin_community_edit(request, pk):
    """Edit komunitas"""
    community = get_object_or_404(Community, pk=pk, created_by=request.user)
    
    if request.method == 'POST':
        try:
            community.community_name = request.POST.get('community_name')
            community.description = request.POST.get('description')
            community.location = request.POST.get('location')
            community.sports_type = request.POST.get('sports_type')
            community.max_member = request.POST.get('max_member', 50)
            community.contact_person_name = request.POST.get('contact_person_name', request.user.username)
            community.contact_phone = request.POST.get('contact_phone', '')
            
            if request.FILES.get('community_image'):
                community.community_image = request.FILES['community_image']
            
            community.save()
            
            messages.success(request, 'Komunitas berhasil diupdate!')
            return redirect('community:admin_community_list')
            
        except Exception as e:
            messages.error(request, f'Terjadi kesalahan: {str(e)}')
    
    context = {'community': community}
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