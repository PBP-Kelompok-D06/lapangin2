from django.test import TestCase, Client
from django.contrib.auth.models import User
from booking.models import Booking, Lapangan, SlotTersedia
from datetime import date, time, timedelta
from django.urls import reverse
import json

class BookingTests(TestCase):
    def setUp(self):
        self.client = Client()

        # Buat user dan login
        self.user = User.objects.create_user(username='user1', password='password123')
        self.client.login(username='user1', password='password123')

        # Buat lapangan
        self.lapangan = Lapangan.objects.create(
            nama_lapangan='Lapangan Futsal A',
            jenis_olahraga='Futsal',
            lokasi='Jakarta',
            harga_per_jam=100000,
            fasilitas='Toilet, Kantin',
            rating=4.5,
            jumlah_ulasan=10,
        )

        # Buat slot
        self.slot = SlotTersedia.objects.create(
            lapangan=self.lapangan,
            tanggal=date.today(),
            jam_mulai=time(9, 0),
            jam_akhir=time(10, 0),
            is_available=True
        )

        # Buat booking
        self.booking = Booking.objects.create(
            user=self.user,
            slot=self.slot,
            total_bayar=100000,
            status_pembayaran='PENDING'
        )

    # ---------- Model Tests ----------
    def test_booking_model_str(self):
        self.assertEqual(str(self.booking), f'Booking #{self.booking.id} oleh {self.user.username}')

    def test_booking_is_linked_to_user_and_slot(self):
        self.assertEqual(self.booking.user.username, 'user1')
        self.assertEqual(self.booking.slot.lapangan.nama_lapangan, 'Lapangan Futsal A')

    def test_slot_unique_constraint(self):
        with self.assertRaises(Exception):
            SlotTersedia.objects.create(
                lapangan=self.lapangan,
                tanggal=self.slot.tanggal,
                jam_mulai=self.slot.jam_mulai,
                jam_akhir=self.slot.jam_akhir,
            )

    # ---------- View Tests ----------
    def test_show_booking_page_view(self):
        """Cek halaman booking bisa diakses"""
        url = reverse('booking:show_booking_page')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'booking.html')

    def test_create_booking_view_success(self):
        """Cek booking baru berhasil dibuat"""
        url = reverse('booking:create_booking')
        payload = {'slot_id': self.slot.id}
        response = self.client.post(url, json.dumps(payload), content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertIn('success', response.json())

    def test_create_booking_view_unauthenticated(self):
        """Cek user belum login ditolak"""
        self.client.logout()
        url = reverse('booking:create_booking')
        payload = {'slot_id': self.slot.id}
        response = self.client.post(url, json.dumps(payload), content_type='application/json')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login', response.url)  # diarahkan ke login


    def test_check_slot_status_valid(self):
        """Cek polling status slot"""
        url = reverse('booking:check_slot_status') + f'?lapangan_id={self.lapangan.id}'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.json(), list)

    def test_check_slot_status_invalid_lapangan(self):
        """Lapangan ID tidak ditemukan"""
        url = reverse('booking:check_slot_status') + '?lapangan_id=9999'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_show_payment_page_owner_access(self):
        """Cek halaman payment bisa diakses oleh pemilik booking"""
        url = reverse('booking:show_payment_page', args=[self.booking.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'payment_detail.html')

    def test_show_payment_page_wrong_user(self):
        """User lain tidak bisa akses booking orang lain"""
        other_user = User.objects.create_user(username='user2', password='password123')
        self.client.login(username='user2', password='password123')
        url = reverse('booking:show_payment_page', args=[self.booking.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)  # redirect karena tidak berhak
