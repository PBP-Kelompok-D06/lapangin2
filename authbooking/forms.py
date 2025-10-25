from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Profile

class CustomUserCreationForm(UserCreationForm):
    role = forms.ChoiceField(choices=Profile.ROLES, label="Role selection")
    nomor_rekening = forms.CharField(max_length=50, required=False, label="Account number")
    nomor_whatsapp = forms.CharField(max_length=20, required=False, label="WhatsApp number")

    class Meta:
        model = User
        fields = ('username', 'password1', 'password2', 'role', 'nomor_rekening', 'nomor_whatsapp')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            placeholder_text = f"Enter your {field.label.lower()}"  # default

            #  placeholder custom untuk field tertentu
            if field_name == 'nomor_rekening':
                placeholder_text = "contoh: 1234567890 - a.n. Budi Santoso"
            elif field_name == 'nomor_whatsapp':
                placeholder_text = "contoh: +6281234567890"
            elif field_name == 'role':
                placeholder_text = "Pilih role Anda"  # untuk dropdown

            field.widget.attrs.update({
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-md focus:outline-none focus:border-[#839556] transition-colors',
                'placeholder': placeholder_text,
            })
    
    def clean_nomor_whatsapp(self): # validasi format no wa
        role = self.cleaned_data.get('role','') # handle kasus ketika no wa ga diisi (in case PENYEWA)
        if (role == 'PENYEWA'):
            return

        nomor = self.cleaned_data.get('nomor_whatsapp', '').strip()

        # Jika user isi 0812..., ubah ke +62812...
        if nomor.startswith('0'):
            nomor = '+62' + nomor[1:]
        elif not nomor.startswith('+62'):
            nomor = '+62' + nomor  # jaga-jaga kalau lupa nulis '+'

        # Validasi isi dan panjang nomor
        if not nomor[1:].replace('+', '').isdigit():
            raise forms.ValidationError("Nomor WhatsApp hanya boleh berisi angka setelah tanda '+'.")
        if len(nomor) < 10 or len(nomor) > 15:
            raise forms.ValidationError("Nomor WhatsApp tampaknya tidak valid.")

        
        return nomor