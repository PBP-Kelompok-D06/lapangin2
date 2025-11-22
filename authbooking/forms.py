#  ini lapangin2/authbooking/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Profile

# Custom form untuk registrasi user (turunan dari UserCreationForm bawaan Django)
class CustomUserCreationForm(UserCreationForm):
    # Tambahan field yang tidak ada di User default
    role = forms.ChoiceField(choices=Profile.ROLES, label="Role selection")  
    # dropdown berisi daftar role dari model Profile

    nomor_rekening = forms.CharField(max_length=50, required=False, label="Account number")  
    # field opsional untuk nomor rekening (bisa dikosongkan)

    nomor_whatsapp = forms.CharField(max_length=20, required=False, label="WhatsApp number")  
    # field opsional untuk nomor WhatsApp

    class Meta:
        model = User  
        # Form ini tetap pakai model User bawaan Django
        fields = ('username', 'password1', 'password2', 'role', 'nomor_rekening', 'nomor_whatsapp')  
        # daftar field yang akan ditampilkan di form

    def __init__(self, *args, **kwargs):
        # Method ini otomatis dipanggil saat form dibuat
        super().__init__(*args, **kwargs)
        # Loop semua field untuk menambahkan placeholder dan style CSS
        for field_name, field in self.fields.items():
            # Default placeholder: "Enter your [nama field]"
            placeholder_text = f"Enter your {field.label.lower()}"

            # Ganti placeholder untuk field tertentu biar lebih spesifik
            if field_name == 'nomor_rekening':
                placeholder_text = "contoh: 1234567890 - a.n. Budi Santoso"
            elif field_name == 'nomor_whatsapp':
                placeholder_text = "contoh: +6281234567890"
            elif field_name == 'role':
                placeholder_text = "Pilih role Anda"  # karena role adalah dropdown

            # Tambahkan atribut HTML seperti CSS class dan placeholder
            field.widget.attrs.update({
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-md focus:outline-none focus:border-[#839556] transition-colors',
                # class di atas dipakai buat styling (Tailwind)
                'placeholder': placeholder_text,
            })
    
    # Validasi custom untuk field nomor_whatsapp
    def clean_nomor_whatsapp(self):
        role = self.cleaned_data.get('role', '')  
        # ambil role yang dipilih user

        if role == 'PENYEWA':
            # kalau usernya penyewa, nomor WA boleh dikosongkan
            return

        nomor = self.cleaned_data.get('nomor_whatsapp', '').strip()
        # ambil input nomor WA dan hapus spasi di awal/akhir

        # Kalau nomor dimulai dengan '0', ubah jadi format internasional '+62...'
        if nomor.startswith('0'):
            nomor = '+62' + nomor[1:]
        elif not nomor.startswith('+62'):
            # kalau user lupa nulis '+', tambahin otomatis
            nomor = '+62' + nomor

        # Cek apakah setelah tanda '+' semua karakter berupa angka
        if not nomor[1:].replace('+', '').isdigit():
            raise forms.ValidationError("Nomor WhatsApp hanya boleh berisi angka setelah tanda '+'.")

        # Cek panjang nomor (harus antara 10 dan 15 digit)
        if len(nomor) < 10 or len(nomor) > 15:
            raise forms.ValidationError("Nomor WhatsApp tampaknya tidak valid.")

        return nomor  
        # kalau lolos semua validasi, nomor dikembalikan dalam format '+62...'
