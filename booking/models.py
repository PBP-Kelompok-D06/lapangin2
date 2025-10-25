from django.db import models
from django.contrib.auth.models import User
from authbooking.models import Profile 


# 1. Model untuk Lapangan (Data Statis dari CSV)
class Lapangan(models.Model):
    pengelola = models.ForeignKey(
        Profile, 
        on_delete=models.CASCADE,
        related_name='lapangan_dikelola',
        limit_choices_to={'role': 'PEMILIK'},
        null=True, 
        blank=True
    )
    # --------------------------------------------------------

    # Kolom dari CSV:
    nama_lapangan = models.CharField(max_length=100, unique=True)
    jenis_olahraga = models.CharField(max_length=50)
    lokasi = models.CharField(max_length=100)
    harga_per_jam = models.DecimalField(max_digits=10, decimal_places=0)
    fasilitas = models.TextField(default='-') 
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.00) 
    jumlah_ulasan = models.IntegerField(default=0)
    
    # TAMBAHKAN KEMBALI FIELD INI
    foto_utama = models.ImageField(upload_to='lapangan/', null=True, blank=True)
    deskripsi = models.TextField(blank=True, default='')
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f'{self.nama_lapangan} ({self.jenis_olahraga})'
    
    def update_rating(self):
        from review.models import Review
        from django.db.models import Avg
        
        reviews = Review.objects.filter(field=self)
        jumlah = reviews.count()
        rata_rata = reviews.aggregate(Avg('rating'))['rating__avg'] or 0.00
        
        self.jumlah_ulasan = jumlah
        self.rating = round(rata_rata, 2)
        self.save()

# 2. Model Slot Tersedia (Initial Dataset 100+)
class SlotTersedia(models.Model):
    lapangan = models.ForeignKey(
        Lapangan, 
        on_delete=models.CASCADE, 
        related_name='slots'
    )
    tanggal = models.DateField()
    jam_mulai = models.TimeField()
    jam_akhir = models.TimeField()
    is_available = models.BooleanField(default=True)

    # Untuk menampung Foreign Key ke Booking yang sedang pending
    # Ini adalah kunci untuk menampilkan status PENDING di card user lain
    pending_booking = models.OneToOneField(
        'Booking',
        on_delete=models.SET_NULL,
        related_name='slot_reserved_by_pending',
        null=True,
        blank=True
    )

    def __str__(self):
        return f'{self.lapangan.nama_lapangan} - {self.tanggal} {self.jam_mulai.strftime("%H:%M")}'
    
    class Meta:
        unique_together = ('lapangan', 'tanggal', 'jam_mulai')

# 3. Model Booking (Transaksi - Membutuhkan Filter Login Wajib)
class Booking(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE) 
    slot = models.ForeignKey(
        SlotTersedia, 
        on_delete=models.PROTECT
    ) 
    tanggal_booking = models.DateTimeField(auto_now_add=True)
    total_bayar = models.DecimalField(max_digits=10, decimal_places=0)
    
    STATUS_CHOICES = [
        ('PENDING', 'Menunggu Pembayaran'),
        ('PAID', 'Sudah Dibayar'),
        ('CANCELLED', 'Dibatalkan'),
    ]
    status_pembayaran = models.CharField(
        max_length=10, 
        choices=STATUS_CHOICES, 
        default='PENDING'
    )

    def __str__(self):
        return f'Booking #{self.id} oleh {self.user.username}'