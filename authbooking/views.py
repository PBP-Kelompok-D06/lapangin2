from django.shortcuts import render, redirect
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.http import JsonResponse
from .forms import CustomUserCreationForm
from .models import Profile


# --- REGISTER AJAX ---
def register_user(request):
    """Menangani registrasi user baru (AJAX + GET render)."""
    if request.method == 'POST' and request.headers.get('x-requested-with') == 'XMLHttpRequest':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.save()

            # Buat profile baru
            Profile.objects.create(
                user=user,
                role=form.cleaned_data.get('role'),
                nomor_rekening=form.cleaned_data.get('nomor_rekening'),
                nomor_whatsapp=form.cleaned_data.get('nomor_whatsapp')
            )

            login(request, user)

            profile = Profile.objects.get(user=user)
            # Redirect ke dashboard kalau PEMILIK
            redirect_url = '/dashboard/' if profile.role == 'PEMILIK' else '/'

            return JsonResponse({
                'success': True,
                'message': f"Akun {user.username} berhasil dibuat! Role: {profile.get_role_display()}.",
                'redirect_url': redirect_url
            })
        else:
            # Kembalikan error field
            errors = {field: [str(e) for e in errs] for field, errs in form.errors.items()}
            return JsonResponse({'success': False, 'errors': errors})
    else:
        # GET request → render halaman register
        form = CustomUserCreationForm()
        context = {
            'form': form,
            'show_navbar': False
        }
        return render(request, 'register.html', context)


# --- LOGIN AJAX ---
def login_user(request):
    """Menangani login user (AJAX + GET render)."""
    if request.method == 'POST' and request.headers.get('x-requested-with') == 'XMLHttpRequest':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)

            try:
                profile = Profile.objects.get(user=user)
            except Profile.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'errors': {'profile': ['Profil Anda belum lengkap. Silakan hubungi admin.']}
                })

            redirect_url = '/'
            if profile.role == 'PEMILIK':
                redirect_url = '/dashboard/'

            # Ambil next URL jika ada
            next_url = request.POST.get('next')
            if next_url:
                redirect_url = next_url

            return JsonResponse({
                'success': True,
                'message': f"Selamat datang kembali, {user.username}.",
                'redirect_url': redirect_url
            })
        else:
            errors = {field: [str(e) for e in errs] for field, errs in form.errors.items()}
            return JsonResponse({'success': False, 'errors': errors})
    else:
        # GET request → render halaman login
        form = AuthenticationForm(request)
        context = {
            'form': form,
            'show_navbar': False,
            'next': request.GET.get('next', '')
        }
        return render(request, 'login.html', context)


# --- LOGOUT ---
def logout_user(request):
    """Logout user dan redirect ke halaman utama."""
    logout(request)
    messages.info(request, "Anda telah berhasil logout.")
    return redirect('/')