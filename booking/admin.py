from django.contrib import admin
from .models import Lapangan, SlotTersedia, Booking

@admin.register(Lapangan)
class LapanganAdmin(admin.ModelAdmin):
    list_display = ('nama_lapangan', 'jenis_olahraga', 'lokasi', 'harga_per_jam', 'pengelola')
    list_filter = ('jenis_olahraga',)
    search_fields = ('nama_lapangan', 'lokasi')

@admin.register(SlotTersedia)
class SlotTersediaAdmin(admin.ModelAdmin):
    list_display = ('lapangan', 'tanggal', 'jam_mulai', 'jam_akhir', 'is_available', 'pending_booking')
    list_filter = ('tanggal', 'is_available')
    search_fields = ('lapangan__nama_lapangan',)

@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ('user', 'slot', 'tanggal_booking', 'total_bayar', 'status_pembayaran')
    list_filter = ('status_pembayaran',)
    search_fields = ('user__username',)
