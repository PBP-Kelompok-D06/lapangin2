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
            
            # Ambil role dari Profile
            try:
                profile = Profile.objects.get(user=user)
                role = profile.role  # 'PEMILIK' atau 'PENYEWA'
                nomor_whatsapp = profile.nomor_whatsapp if role == 'PEMILIK' else None
                nomor_rekening = profile.nomor_rekening if role == 'PEMILIK' else None
            except Profile.DoesNotExist:
                # Jika profile tidak ada, default ke PENYEWA
                role = 'PENYEWA'
                nomor_whatsapp = None
                nomor_rekening = None
            
            # Return dengan field role
            return JsonResponse({
                "username": user.username,
                "status": True,
                "message": "Login successful!",
                "role": role,
                "nomor_whatsapp": nomor_whatsapp,
                "nomor_rekening": nomor_rekening,
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
        try:
            data = json.loads(request.body)
            username = data.get('username', '').strip()
            password1 = data.get('password1', '')
            password2 = data.get('password2', '')
            role = data.get('role', 'PENYEWA')
            nomor_whatsapp = data.get('nomor_whatsapp', '').strip()
            nomor_rekening = data.get('nomor_rekening', '').strip()

            # Validasi username
            if not username:
                return JsonResponse({
                    "status": False,
                    "message": "Username cannot be empty."
                }, status=400)

            # Validasi password match
            if password1 != password2:
                return JsonResponse({
                    "status": False,
                    "message": "Passwords do not match."
                }, status=400)
            
            # Cek username sudah ada
            if User.objects.filter(username=username).exists():
                return JsonResponse({
                    "status": False,
                    "message": "Username already exists."
                }, status=400)
            
            # Validasi panjang password
            if len(password1) < 8:
                return JsonResponse({
                    "status": False,
                    "message": "Password must be at least 8 characters."
                }, status=400)
            
            # Validasi khusus untuk PEMILIK
            if role == 'PEMILIK':
                if not nomor_whatsapp:
                    return JsonResponse({
                        "status": False,
                        "message": "WhatsApp number is required for Field Owners."
                    }, status=400)
                
                if not nomor_rekening:
                    return JsonResponse({
                        "status": False,
                        "message": "Account number is required for Field Owners."
                    }, status=400)
                
                # Validasi format WhatsApp
                if not nomor_whatsapp.startswith('+62'):
                    return JsonResponse({
                        "status": False,
                        "message": "WhatsApp number must start with +62."
                    }, status=400)
                
                digits_only = nomor_whatsapp[1:].replace('+', '')
                if not digits_only.isdigit():
                    return JsonResponse({
                        "status": False,
                        "message": "WhatsApp number must contain only digits after '+'."
                    }, status=400)

            # Buat user baru
            user = User.objects.create_user(username=username, password=password1)
            user.save()
            
            # Buat Profile
            Profile.objects.create(
                user=user,
                role=role,
                nomor_whatsapp=nomor_whatsapp if role == 'PEMILIK' and nomor_whatsapp else None,
                nomor_rekening=nomor_rekening if role == 'PEMILIK' and nomor_rekening else None
            )
            
            # PENTING: Return dengan status True
            return JsonResponse({
                "username": user.username,
                "status": True,  # ← HARUS True (boolean)
                "message": f"Account created successfully! Welcome, {username}!"
            }, status=200)
        
        except Exception as e:
            print(f"🔴 Registration error: {str(e)}")
            return JsonResponse({
                "status": False,
                "message": f"Registration failed: {str(e)}"
            }, status=500)
    
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