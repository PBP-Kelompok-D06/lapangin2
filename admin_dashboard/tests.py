from django.test import TestCase, Client, override_settings
from django.urls import reverse, path, include
from unittest.mock import patch, MagicMock
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.http import Http404
from datetime import date, time, timedelta, datetime
import threading
from django.core.files.uploadedfile import SimpleUploadedFile

# Import Models
from booking.models import Lapangan, SlotTersedia, Booking
from authbooking.models import Profile 
from community.models import Community, CommunityRequest 


# --- COUNTER GLOBAL UNTUK UNIQUE TIME ---
_test_counter_lock = threading.Lock()
_test_counter = 0

def get_unique_test_id():
    """Generate unique ID untuk setiap test run"""
    global _test_counter
    with _test_counter_lock:
        _test_counter += 1
        return _test_counter


# --- BASE CLASS UNTUK INJEKSI DATA & CLEANUP ---
class DataSetupMixin(TestCase):
    """Kelas Mixin yang hanya berisi setup data statis dan patching."""
    
    @classmethod
    def setUpTestData(cls):
        # 1. User dan Profile
        cls.owner_user = User.objects.create_user(username='owner', password='pass', email='owner@test.com')
        cls.owner_profile = Profile.objects.create(user=cls.owner_user, role='PEMILIK', nomor_whatsapp='08123456789')
        cls.reg_user = User.objects.create_user(username='reguler', password='pass', email='reguler@test.com')
        cls.reg_profile = Profile.objects.create(user=cls.reg_user, role='PENYEWA')
        cls.no_profile_user = User.objects.create_user(username='noprofile', password='pass')
        
        # 2. Data Komunitas (statis)
        Community.objects.create(community_name='Liga Malam', created_by=cls.owner_user, max_member=10)
        CommunityRequest.objects.create(requester=cls.reg_user, community_name='Req Bola', description='d', sports_type='s', location_preference='l', status='pending')
        
        cls.home_url = reverse('admin_dashboard:dashboard_home')
        cls.client = Client()

    def setUp(self):
        # -----------------------------------------------------------
        # FIX INTEGRITY ERROR: PATCH Lapangan.save()
        self.original_lapangan_save = Lapangan.save
        
        def mock_save(self, *args, **kwargs):
            self.save_base(*args, **kwargs)

        self.lapangan_save_patch = patch('booking.models.Lapangan.save', side_effect=mock_save, autospec=True)
        self.lapangan_save_patch.start()
        # -----------------------------------------------------------

        # 4. Data Lapangan Dasar (Dibuat di setUp, agar instance fresh)
        test_id = self.id().split('.')[-1]
        
        self.lapangan1 = Lapangan.objects.create(
            nama_lapangan=f'Futsal A {test_id}', jenis_olahraga='Futsal', lokasi='Pusat', 
            harga_per_jam=50000, pengelola=self.owner_profile, deskripsi='Futsal'
        )
        self.lapangan2 = Lapangan.objects.create(
            nama_lapangan=f'Badminton B {test_id}', jenis_olahraga='Bulutangkis', lokasi='Barat', 
            harga_per_jam=40000, pengelola=self.owner_profile, deskripsi='Badminton'
        )
        
        # Hentikan patch sebelum membuat slot manual
        self.lapangan_save_patch.stop()
        Lapangan.save = self.original_lapangan_save 
        
        # 5. Data Dasar Booking (Slot Dibuat Manual & UNIK)
        # SOLUSI: Gunakan counter global + test ID untuk memastikan unique time
        unique_id = get_unique_test_id()
        
        # Gunakan tanggal yang berbeda untuk setiap test
        base_date = date.today() + timedelta(days=unique_id)
        
        # Generate unique time berdasarkan counter
        hour_offset = (unique_id * 2) % 10  # 0-18 (max 18 untuk hindari overflow)
        minute_offset = (unique_id * 7) % 60  # 0-59
        
        start_hour = 6 + hour_offset
        start_minute = minute_offset
        unique_time = time(start_hour, start_minute, 0)
        end_time = time((start_hour + 1) % 24, start_minute, 0)
        
        self.slot_pending = SlotTersedia.objects.create(
            lapangan=self.lapangan1, 
            tanggal=base_date, 
            jam_mulai=unique_time, 
            jam_akhir=end_time, 
            is_available=True
        )
        self.booking_pending = Booking.objects.create(
            user=self.reg_user, 
            slot=self.slot_pending, 
            total_bayar=50000, 
            status_pembayaran='PENDING'
        )
        self.slot_pending.pending_booking = self.booking_pending
        self.slot_pending.save()
        
        # Slot kedua dengan tanggal dan waktu yang berbeda
        unique_time_2 = time(start_hour, (start_minute + 15) % 60, 0)
        end_time_2 = time((start_hour + 1) % 24, (start_minute + 15) % 60, 0)
        
        self.slot_paid = SlotTersedia.objects.create(
            lapangan=self.lapangan2, 
            tanggal=base_date + timedelta(days=1),  # Tanggal berbeda
            jam_mulai=unique_time_2, 
            jam_akhir=end_time_2, 
            is_available=False
        )
        self.booking_paid = Booking.objects.create(
            user=self.reg_user, 
            slot=self.slot_paid, 
            total_bayar=40000, 
            status_pembayaran='PAID'
        )
        
    def tearDown(self):
        # Tidak perlu menghentikan patch yang sudah dihentikan di setUp
        pass

# ------------------------------------------------------------------------------------------------

class PermissionTests(DataSetupMixin):
    """Menguji otorisasi, diisolasi dari tes logika."""

    def test_pemilik_required_rejects_non_owner(self): 
        self.client.login(username='reguler', password='pass')
        response = self.client.get(self.home_url, follow=True)
        self.assertTrue(response.redirect_chain[0][0].startswith('/accounts/login/')) 
        
    def test_pemilik_required_rejects_no_profile_user(self):
        self.client.login(username='noprofile', password='pass')
        response = self.client.get(self.home_url, follow=True)
        self.assertTrue(response.redirect_chain[0][0].startswith('/accounts/login/'))

# ------------------------------------------------------------------------------------------------

class DashboardHomeTests(DataSetupMixin):
    
    @patch('admin_dashboard.views.render')
    def test_dashboard_home_success(self, mock_render):
        """Test dashboard home dapat diakses oleh pemilik"""
        from django.http import HttpResponse
        # Mock render untuk return HttpResponse yang proper
        mock_render.return_value = HttpResponse('OK')
        
        self.client.force_login(self.owner_user)
        response = self.client.get(self.home_url)
        
        # Verifikasi view dipanggil dengan sukses
        self.assertEqual(response.status_code, 200)
        self.assertTrue(mock_render.called)
        
        # Verifikasi context yang dikirim ke template
        call_args = mock_render.call_args
        context = call_args[0][2]  # render(request, template, context)
        
        # Pastikan context berisi data yang diperlukan (sesuai dengan key yang sebenarnya)
        self.assertIn('total_lapangan', context)
        self.assertIn('total_komunitas', context)
        self.assertIn('pending_requests', context)
        self.assertIn('pending_bookings', context)
        
        # Verifikasi nilai context
        self.assertEqual(context['total_lapangan'], 2)
        self.assertEqual(context['total_komunitas'], 1)
        self.assertEqual(context['pending_requests'], 1)
        self.assertEqual(context['pending_bookings'], 1)

# ------------------------------------------------------------------------------------------------

class LapanganListTests(DataSetupMixin):
    
    @patch('admin_dashboard.views.find')
    def test_lapangan_list_no_filter_success_and_static_path_png(self, mock_find):
        self.client.force_login(self.owner_user)
        mock_find.side_effect = lambda x: x if x.endswith(f'lapangan{self.lapangan1.pk}.png') else None
        response = self.client.get(reverse('admin_dashboard:lapangan_list'))
        self.assertEqual(response.status_code, 200)

# ------------------------------------------------------------------------------------------------

class LapanganCreateTests(DataSetupMixin):
    
    def get_valid_data(self, **kwargs):
        data = {
            'nama': 'Baru C', 'jenis': 'Basket', 'lokasi': 'Timur',
            'harga': '60000', 'deskripsi': 'Deskripsi Test', 'fasilitas': 'AC',
            'foto_utama': '' 
        }
        data.update(kwargs)
        if 'foto_utama' in kwargs and kwargs['foto_utama'] and not isinstance(kwargs['foto_utama'], str):
            del data['foto_utama']
        elif 'foto_utama' in data and data['foto_utama'] is None:
             data['foto_utama'] = ''
        return data

    def test_lapangan_create_POST_success(self):
        self.client.force_login(self.owner_user)
        data = self.get_valid_data()
        data['foto_utama'] = SimpleUploadedFile("test.png", b"file_content", content_type="image/png")
        response = self.client.post(reverse('admin_dashboard:lapangan_create'), data, follow=True)
        self.assertEqual(response.status_code, 200)

    def test_create_photo_size_too_large_error(self):
        self.client.force_login(self.owner_user)
        data = self.get_valid_data()
        data['foto_utama'] = SimpleUploadedFile("large.png", b"a" * (6 * 1024 * 1024), content_type="image/png")
        response = self.client.post(reverse('admin_dashboard:lapangan_create'), data, follow=True)
        self.assertContains(response, 'Ukuran foto maksimal 5MB!')

# ------------------------------------------------------------------------------------------------

class LapanganEditTests(DataSetupMixin):
    
    def get_valid_edit_data(self, **kwargs):
        data = {
            'nama': 'Futsal A Edited', 'jenis': 'Bulutangkis', 'lokasi': 'Timur',
            'harga': '75000', 'deskripsi': 'Deskripsi Edit', 'fasilitas': 'Wi-Fi',
            'foto_utama': '' 
        }
        data.update(kwargs)
        return data

    def test_lapangan_edit_POST_success(self):
        self.client.force_login(self.owner_user)
        url = reverse('admin_dashboard:lapangan_edit', kwargs={'pk': self.lapangan1.pk})
        data = self.get_valid_edit_data(lokasi='UPDATE')
        response = self.client.post(url, data, follow=True)
        self.assertEqual(response.status_code, 200)

    # FIX Error 404 pada tes edit form yang gagal (karena tidak ada 'lapangan' di context)
    def test_lapangan_edit_missing_fields_renders_error(self):
        self.client.force_login(self.owner_user)
        url = reverse('admin_dashboard:lapangan_edit', kwargs={'pk': self.lapangan1.pk})
        data = self.get_valid_edit_data(lokasi='') 
        
        response = self.client.post(url, data) # TIDAK follow=True
        
        self.assertContains(response, 'Semua field wajib diisi!') 
        self.assertEqual(response.status_code, 200) # Harus 200 OK karena render ulang form

# ------------------------------------------------------------------------------------------------

class LapanganDeleteTests(DataSetupMixin):
    
    def test_lapangan_delete_POST_has_active_booking_pending(self):
        self.client.force_login(self.owner_user)
        url = reverse('admin_dashboard:lapangan_delete', kwargs={'pk': self.lapangan1.pk})
        response = self.client.post(url, follow=True)
        self.assertContains(response, 'Tidak dapat menghapus lapangan yang masih memiliki booking aktif!')
        
# ------------------------------------------------------------------------------------------------

class BookingApproveRejectTests(DataSetupMixin):
    
    def test_booking_approve_POST_success(self):
        self.client.force_login(self.owner_user)
        url = reverse('admin_dashboard:booking_approve', kwargs={'pk': self.booking_pending.pk})
        response = self.client.post(url, follow=True)
        self.assertEqual(response.status_code, 200)

    @patch('admin_dashboard.views.get_object_or_404')
    def test_booking_approve_POST_already_processed_error(self, mock_get_object_or_404):
        self.client.force_login(self.owner_user)
        mock_booking = MagicMock(pk=self.booking_pending.pk, status_pembayaran='PAID')
        mock_booking.slot.lapangan.pengelola = self.owner_profile 
        mock_get_object_or_404.return_value = mock_booking
        
        url = reverse('admin_dashboard:booking_approve', kwargs={'pk': self.booking_pending.pk})
        response = self.client.post(url, follow=True)
        
        self.assertEqual(response.status_code, 200) 
        self.assertContains(response, 'Booking ini sudah diproses!')

# ------------------------------------------------------------------------------------------------

class TransaksiSessionsTests(DataSetupMixin):

    def test_booking_sessions_list_no_lapangan_selected(self):
        self.client.force_login(self.owner_user)
        url = reverse('admin_dashboard:booking_sessions_list')
        response = self.client.get(url)
        self.assertEqual(response.context['selected_lapangan'].pk, self.lapangan1.pk) 

    def test_slot_create_end_time_before_start_time_error(self):
        self.client.force_login(self.owner_user)
        data = {
            'lapangan_id': self.lapangan1.pk, 'start_date': date.today().strftime('%Y-%m-%d'),
            'end_date': date.today().strftime('%Y-%m-%d'), 'jam_mulai': '15:00', 'jam_akhir': '14:00',
            'foto_utama': ''
        }
        response = self.client.post(reverse('admin_dashboard:booking_sessions_create'), data, follow=True)
        self.assertContains(response, 'Jam akhir harus lebih besar dari jam mulai!')

# ------------------------------------------------------------------------------------------------

class LapanganMultiplePhotosTests(DataSetupMixin):
    """Test untuk fitur 3 foto lapangan"""
    
    def test_lapangan_create_with_three_photos(self):
        """Test create lapangan dengan 3 foto sekaligus"""
        self.client.force_login(self.owner_user)
        
        foto1 = SimpleUploadedFile("foto1.jpg", b"foto1_content", content_type="image/jpeg")
        foto2 = SimpleUploadedFile("foto2.jpg", b"foto2_content", content_type="image/jpeg")
        foto3 = SimpleUploadedFile("foto3.jpg", b"foto3_content", content_type="image/jpeg")
        
        data = {
            'nama': 'Lapangan 3 Foto',
            'jenis': 'Futsal',
            'lokasi': 'Jakarta',
            'harga': '100000',
            'deskripsi': 'Test',
            'fasilitas': 'AC',
            'foto_utama': foto1,
            'foto_2': foto2,
            'foto_3': foto3
        }
        
        response = self.client.post(reverse('admin_dashboard:lapangan_create'), data, follow=True)
        self.assertEqual(response.status_code, 200)
        
        # Verify lapangan created with 3 photos
        lapangan = Lapangan.objects.filter(nama_lapangan='Lapangan 3 Foto').first()
        self.assertIsNotNone(lapangan)
        self.assertTrue(lapangan.foto_utama)
        self.assertTrue(lapangan.foto_2)
        self.assertTrue(lapangan.foto_3)
    
    def test_lapangan_edit_add_foto_2_only(self):
        """Test edit: tambah foto 2 saja (foto utama dan 3 kosong)"""
        self.client.force_login(self.owner_user)
        url = reverse('admin_dashboard:lapangan_edit', kwargs={'pk': self.lapangan1.pk})
        
        foto2 = SimpleUploadedFile("foto2.jpg", b"foto2_content", content_type="image/jpeg")
        
        data = {
            'nama': 'Updated Lapangan',
            'jenis': 'Futsal',
            'lokasi': 'Jakarta',
            'harga': '150000',
            'deskripsi': 'Updated',
            'fasilitas': 'AC',
            'foto_2': foto2  # Only foto 2
        }
        
        response = self.client.post(url, data, follow=True)
        self.assertEqual(response.status_code, 200)
        
        # Verify foto 2 added
        self.lapangan1.refresh_from_db()
        self.assertTrue(self.lapangan1.foto_2)
    
    def test_lapangan_edit_add_foto_3_only(self):
        """Test edit: tambah foto 3 saja"""
        self.client.force_login(self.owner_user)
        url = reverse('admin_dashboard:lapangan_edit', kwargs={'pk': self.lapangan1.pk})
        
        foto3 = SimpleUploadedFile("foto3.jpg", b"foto3_content", content_type="image/jpeg")
        
        data = {
            'nama': 'Updated Lapangan',
            'jenis': 'Futsal',
            'lokasi': 'Jakarta',
            'harga': '150000',
            'deskripsi': 'Updated',
            'fasilitas': 'AC',
            'foto_3': foto3  # Only foto 3
        }
        
        response = self.client.post(url, data, follow=True)
        self.assertEqual(response.status_code, 200)
        
        # Verify foto 3 added
        self.lapangan1.refresh_from_db()
        self.assertTrue(self.lapangan1.foto_3)
    
    def test_lapangan_edit_update_all_three_photos(self):
        """Test edit: update semua 3 foto sekaligus"""
        self.client.force_login(self.owner_user)
        url = reverse('admin_dashboard:lapangan_edit', kwargs={'pk': self.lapangan1.pk})
        
        foto1 = SimpleUploadedFile("new1.jpg", b"new1_content", content_type="image/jpeg")
        foto2 = SimpleUploadedFile("new2.jpg", b"new2_content", content_type="image/jpeg")
        foto3 = SimpleUploadedFile("new3.jpg", b"new3_content", content_type="image/jpeg")
        
        data = {
            'nama': 'Updated Lapangan',
            'jenis': 'Futsal',
            'lokasi': 'Jakarta',
            'harga': '150000',
            'deskripsi': 'Updated',
            'fasilitas': 'AC',
            'foto_utama': foto1,
            'foto_2': foto2,
            'foto_3': foto3
        }
        
        response = self.client.post(url, data, follow=True)
        self.assertEqual(response.status_code, 200)
        
        # Verify all photos updated
        self.lapangan1.refresh_from_db()
        self.assertTrue(self.lapangan1.foto_utama)
        self.assertTrue(self.lapangan1.foto_2)
        self.assertTrue(self.lapangan1.foto_3)
    
    def test_lapangan_edit_foto_2_too_large(self):
        """Test edit: foto 2 terlalu besar (>5MB)"""
        self.client.force_login(self.owner_user)
        url = reverse('admin_dashboard:lapangan_edit', kwargs={'pk': self.lapangan1.pk})
        
        large_foto = SimpleUploadedFile("large2.jpg", b"a" * (6 * 1024 * 1024), content_type="image/jpeg")
        
        data = {
            'nama': 'Updated Lapangan',
            'jenis': 'Futsal',
            'lokasi': 'Jakarta',
            'harga': '150000',
            'deskripsi': 'Updated',
            'fasilitas': 'AC',
            'foto_2': large_foto
        }
        
        response = self.client.post(url, data, follow=True)
        self.assertContains(response, 'Ukuran foto 2 maksimal 5MB')
    
    def test_lapangan_edit_foto_3_too_large(self):
        """Test edit: foto 3 terlalu besar (>5MB)"""
        self.client.force_login(self.owner_user)
        url = reverse('admin_dashboard:lapangan_edit', kwargs={'pk': self.lapangan1.pk})
        
        large_foto = SimpleUploadedFile("large3.jpg", b"a" * (6 * 1024 * 1024), content_type="image/jpeg")
        
        data = {
            'nama': 'Updated Lapangan',
            'jenis': 'Futsal',
            'lokasi': 'Jakarta',
            'harga': '150000',
            'deskripsi': 'Updated',
            'fasilitas': 'AC',
            'foto_3': large_foto
        }
        
        response = self.client.post(url, data, follow=True)
        self.assertContains(response, 'Ukuran foto 3 maksimal 5MB')
    
    def test_lapangan_edit_foto_2_invalid_type(self):
        """Test edit: foto 2 dengan tipe file invalid"""
        self.client.force_login(self.owner_user)
        url = reverse('admin_dashboard:lapangan_edit', kwargs={'pk': self.lapangan1.pk})
        
        invalid_foto = SimpleUploadedFile("file2.txt", b"text_content", content_type="text/plain")
        
        data = {
            'nama': 'Updated Lapangan',
            'jenis': 'Futsal',
            'lokasi': 'Jakarta',
            'harga': '150000',
            'deskripsi': 'Updated',
            'fasilitas': 'AC',
            'foto_2': invalid_foto
        }
        
        response = self.client.post(url, data, follow=True)
        self.assertContains(response, 'Format foto 2 harus JPG atau PNG')
    
    def test_lapangan_edit_foto_3_invalid_type(self):
        """Test edit: foto 3 dengan tipe file invalid"""
        self.client.force_login(self.owner_user)
        url = reverse('admin_dashboard:lapangan_edit', kwargs={'pk': self.lapangan1.pk})
        
        invalid_foto = SimpleUploadedFile("file3.txt", b"text_content", content_type="text/plain")
        
        data = {
            'nama': 'Updated Lapangan',
            'jenis': 'Futsal',
            'lokasi': 'Jakarta',
            'harga': '150000',
            'deskripsi': 'Updated',
            'fasilitas': 'AC',
            'foto_3': invalid_foto
        }
        
        response = self.client.post(url, data, follow=True)
        self.assertContains(response, 'Format foto 3 harus JPG atau PNG')
    
    def test_lapangan_edit_scenario_first_edit_foto_1_only(self):
        """Test skenario real: edit pertama - upload foto 1 saja"""
        self.client.force_login(self.owner_user)
        url = reverse('admin_dashboard:lapangan_edit', kwargs={'pk': self.lapangan1.pk})
        
        foto1 = SimpleUploadedFile("foto1.jpg", b"foto1_content", content_type="image/jpeg")
        
        data = {
            'nama': 'Lapangan Edit 1',
            'jenis': 'Futsal',
            'lokasi': 'Jakarta',
            'harga': '100000',
            'deskripsi': 'First edit',
            'fasilitas': 'AC',
            'foto_utama': foto1
        }
        
        response = self.client.post(url, data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'berhasil diupdate')
    
    def test_lapangan_edit_scenario_second_edit_add_foto_2_and_3(self):
        """Test skenario real: edit kedua - tambah foto 2 dan 3 (foto 1 kosong)"""
        self.client.force_login(self.owner_user)
        url = reverse('admin_dashboard:lapangan_edit', kwargs={'pk': self.lapangan1.pk})
        
        # First edit - add foto 1
        foto1 = SimpleUploadedFile("foto1.jpg", b"foto1_content", content_type="image/jpeg")
        data = {
            'nama': 'Lapangan Skenario',
            'jenis': 'Futsal',
            'lokasi': 'Jakarta',
            'harga': '100000',
            'deskripsi': 'Test',
            'fasilitas': 'AC',
            'foto_utama': foto1
        }
        self.client.post(url, data)
        
        # Second edit - add foto 2 and 3 without foto 1
        foto2 = SimpleUploadedFile("foto2.jpg", b"foto2_content", content_type="image/jpeg")
        foto3 = SimpleUploadedFile("foto3.jpg", b"foto3_content", content_type="image/jpeg")
        
        data2 = {
            'nama': 'Lapangan Skenario Updated',
            'jenis': 'Futsal',
            'lokasi': 'Jakarta',
            'harga': '120000',
            'deskripsi': 'Second edit',
            'fasilitas': 'AC, Parking',
            'foto_2': foto2,
            'foto_3': foto3
            # foto_utama tidak di-upload lagi
        }
        
        response = self.client.post(url, data2, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'berhasil diupdate')
        
        # Verify all 3 photos exist
        self.lapangan1.refresh_from_db()
        self.assertTrue(self.lapangan1.foto_utama)  # From first edit
        self.assertTrue(self.lapangan1.foto_2)      # From second edit
        self.assertTrue(self.lapangan1.foto_3)      # From second edit
    
    def test_lapangan_create_foto_2_too_large(self):
        """Test create: foto 2 terlalu besar"""
        self.client.force_login(self.owner_user)
        
        # Note: lapangan_create belum ada validasi untuk foto_2 dan foto_3
        # Jika ingin comprehensive, perlu update lapangan_create juga
        # Test ini untuk dokumentasi bahwa create mungkin perlu update
        pass
    
    def test_lapangan_edit_mixed_valid_invalid_photos(self):
        """Test edit: kombinasi foto valid dan invalid"""
        self.client.force_login(self.owner_user)
        url = reverse('admin_dashboard:lapangan_edit', kwargs={'pk': self.lapangan1.pk})
        
        valid_foto = SimpleUploadedFile("valid.jpg", b"valid_content", content_type="image/jpeg")
        invalid_foto = SimpleUploadedFile("invalid.txt", b"text", content_type="text/plain")
        
        data = {
            'nama': 'Updated Lapangan',
            'jenis': 'Futsal',
            'lokasi': 'Jakarta',
            'harga': '150000',
            'deskripsi': 'Updated',
            'fasilitas': 'AC',
            'foto_utama': valid_foto,
            'foto_2': invalid_foto  # Invalid
        }
        
        response = self.client.post(url, data, follow=True)
        # Should show error for foto 2
        self.assertContains(response, 'Format foto 2 harus JPG atau PNG')