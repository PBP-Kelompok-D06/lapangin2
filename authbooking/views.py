# ini lapangin2/authbooking/views.py
from django.shortcuts import render, redirect
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .forms import CustomUserCreationForm
from .models import Profile
from django.contrib.auth import authenticate, login as auth_login
from django.contrib.auth.models import User
import json
from django.contrib.auth import logout as auth_logout
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse

# --- REGISTER AJAX ---
def register_user(request):
    """Menangani registrasi user baru (AJAX + GET render)."""
    """ini bagian ajaxnya"""
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
            # Ambil data profil user untuk cek role-nya
            profile = Profile.objects.get(user=user)
            # Redirect ke dashboard kalau PEMILIK
            redirect_url = '/dashboard/' if profile.role == 'PEMILIK' else '/'

            return JsonResponse({
                'success': True,
                'message': f"Akun {user.username} berhasil dibuat! Role: {profile.get_role_display()}.",
                'redirect_url': redirect_url
            })
        else:
              # Kalau form tidak valid → kirim error-nya dalam bentuk JSON
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
    """ini bagian ajaxnya"""
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


@csrf_exempt
def login_flutter(request):
    username = request.POST['username']
    password = request.POST['password']
    user = authenticate(username=username, password=password)
    if user is not None:
        if user.is_active:
            auth_login(request, user)
            # Login status successful.
            return JsonResponse({
                "username": user.username,
                "status": True,
                "message": "Login successful!"
                # Add other data if you want to send data to Flutter.
            }, status=200)
        else:
            return JsonResponse({
                "status": False,
                "message": "Login failed, account is disabled."
            }, status=401)

    else:
        return JsonResponse({
            "status": False,
            "message": "Login failed, please check your username or password."
        }, status=401)


@csrf_exempt
def register_flutter(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        username = data['username']
        password1 = data['password1']
        password2 = data['password2']

        # Check if the passwords match
        if password1 != password2:
            return JsonResponse({
                "status": False,
                "message": "Passwords do not match."
            }, status=400)
        
        # Check if the username is already taken
        if User.objects.filter(username=username).exists():
            return JsonResponse({
                "status": False,
                "message": "Username already exists."
            }, status=400)
        
        # Create the new user
        user = User.objects.create_user(username=username, password=password1)
        user.save()
        
        return JsonResponse({
            "username": user.username,
            "status": 'success',
            "message": "User created successfully!"
        }, status=200)
    
    else:
        return JsonResponse({
            "status": False,
            "message": "Invalid request method."
        }, status=400)

@csrf_exempt
def logout_flutter(request):
    username = request.user.username
    try:
        auth_logout(request)
        return JsonResponse({
            "username": username,
            "status": True,
            "message": "Logged out successfully!"
        }, status=200)
    except:
        return JsonResponse({
            "status": False,
            "message": "Logout failed."
        }, status=401)