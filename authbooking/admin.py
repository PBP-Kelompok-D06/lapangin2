from django.contrib import admin
from .models import Profile

# Custom admin tampilan Profile
@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'nomor_rekening', 'nomor_whatsapp')
    list_filter = ('role',)
    search_fields = ('user__username', 'nomor_whatsapp')