from django.db import models
from django.contrib.auth.models import User

class Profile(models.Model):
    # Definisi 2 Roles yang Diperlukan
    ROLES = [
        ('PENYEWA', 'Penyewa Lapangan'),
        ('PEMILIK', 'Pemilik Lapangan'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=7, choices=ROLES, default='PENYEWA')
    nomor_rekening = models.CharField(max_length=50, blank=True, null=True)
    nomor_whatsapp = models.CharField(max_length=20, blank=True, null=True)


    def __str__(self):
        return f'{self.user.username} ({self.get_role_display()})'