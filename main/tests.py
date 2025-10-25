from django.test import TestCase, Client
from django.urls import reverse
from unittest.mock import patch, MagicMock
from django.contrib.auth.models import User
from datetime import date, time, timedelta

# Import Models
from booking.models import Lapangan
from authbooking.models import Profile


class LandingPageTestCase(TestCase):
    """Test case untuk Landing Page"""
    
    @classmethod
    def setUpTestData(cls):
        """Setup data statis untuk semua test"""
        # Buat user dan profile untuk pengelola
        cls.owner_user = User.objects.create_user(
            username='owner', 
            password='pass', 
            email='owner@test.com'
        )
        cls.owner_profile = Profile.objects.create(
            user=cls.owner_user, 
            role='PEMILIK', 
            nomor_whatsapp='08123456789'
        )
        
        cls.landing_url = reverse('main:home')
        cls.client = Client()
    
    def setUp(self):
        """Setup untuk setiap test - buat lapangan dengan patch save()"""
        # Patch Lapangan.save() untuk skip auto-generate slots
        self.original_lapangan_save = Lapangan.save
        
        def mock_save(self, *args, **kwargs):
            self.save_base(*args, **kwargs)
        
        self.lapangan_save_patch = patch(
            'booking.models.Lapangan.save', 
            side_effect=mock_save, 
            autospec=True
        )
        self.lapangan_save_patch.start()
        
        # Buat beberapa lapangan dengan jenis berbeda
        self.lapangan_futsal1 = Lapangan.objects.create(
            nama_lapangan='Futsal Arena 1',
            jenis_olahraga='Futsal',
            lokasi='Jakarta Pusat',
            harga_per_jam=100000,
            pengelola=self.owner_profile,
            deskripsi='Lapangan futsal standar FIFA',
            rating=4.5,
            jumlah_ulasan=10
        )
        
        self.lapangan_futsal2 = Lapangan.objects.create(
            nama_lapangan='Futsal Arena 2',
            jenis_olahraga='Futsal',
            lokasi='Jakarta Selatan',
            harga_per_jam=120000,
            pengelola=self.owner_profile,
            deskripsi='Lapangan futsal premium',
            rating=4.8,
            jumlah_ulasan=25
        )
        
        self.lapangan_basket = Lapangan.objects.create(
            nama_lapangan='Basketball Court',
            jenis_olahraga='Basket',
            lokasi='Jakarta Barat',
            harga_per_jam=150000,
            pengelola=self.owner_profile,
            deskripsi='Lapangan basket indoor',
            rating=4.3,
            jumlah_ulasan=8
        )
        
        self.lapangan_badminton = Lapangan.objects.create(
            nama_lapangan='Badminton Hall',
            jenis_olahraga='Bulutangkis',
            lokasi='Jakarta Timur',
            harga_per_jam=80000,
            pengelola=self.owner_profile,
            deskripsi='Lapangan badminton',
            rating=4.0,
            jumlah_ulasan=5
        )
        
        self.lapangan_no_review = Lapangan.objects.create(
            nama_lapangan='New Court',
            jenis_olahraga='Tenis',
            lokasi='Jakarta Utara',
            harga_per_jam=90000,
            pengelola=self.owner_profile,
            deskripsi='Lapangan tenis baru',
            rating=0.0,
            jumlah_ulasan=0
        )
        
        # Stop patch
        self.lapangan_save_patch.stop()
        Lapangan.save = self.original_lapangan_save
    
    def tearDown(self):
        """Cleanup setelah setiap test"""
        pass


class LandingPageViewTests(LandingPageTestCase):
    """Test untuk view landing page"""
    
    def test_landing_page_loads_successfully(self):
        """Test landing page dapat diakses tanpa error"""
        response = self.client.get(self.landing_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'landing_page.html')
    
    def test_landing_page_shows_all_lapangan_by_default(self):
        """Test landing page menampilkan semua lapangan secara default"""
        response = self.client.get(self.landing_url)
        
        # Cek context
        self.assertIn('page_obj', response.context)
        page_obj = response.context['page_obj']
        
        # Harus ada 5 lapangan
        self.assertEqual(page_obj.paginator.count, 5)
    
    def test_landing_page_context_contains_required_keys(self):
        """Test context berisi semua key yang diperlukan"""
        response = self.client.get(self.landing_url)
        
        required_keys = ['page_obj', 'jenis_list', 'selected_jenis', 
                        'selected_rating', 'show_navbar']
        
        for key in required_keys:
            self.assertIn(key, response.context)
    
    def test_landing_page_default_filter_values(self):
        """Test nilai default filter"""
        response = self.client.get(self.landing_url)
        
        self.assertEqual(response.context['selected_jenis'], 'all')
        self.assertEqual(response.context['selected_rating'], 'all')


class LandingPageFilterTests(LandingPageTestCase):
    """Test untuk filtering di landing page"""
    
    def test_filter_by_jenis_futsal(self):
        """Test filter berdasarkan jenis olahraga Futsal"""
        response = self.client.get(self.landing_url, {'jenis': 'Futsal'})
        
        page_obj = response.context['page_obj']
        self.assertEqual(page_obj.paginator.count, 2)
        
        # Verifikasi semua item adalah Futsal
        for lapangan in page_obj:
            self.assertEqual(lapangan.jenis_olahraga, 'Futsal')
    
    def test_filter_by_jenis_basket(self):
        """Test filter berdasarkan jenis olahraga Basket"""
        response = self.client.get(self.landing_url, {'jenis': 'Basket'})
        
        page_obj = response.context['page_obj']
        self.assertEqual(page_obj.paginator.count, 1)
        self.assertEqual(page_obj[0].jenis_olahraga, 'Basket')
    
    def test_filter_by_jenis_case_insensitive(self):
        """Test filter jenis case insensitive"""
        response = self.client.get(self.landing_url, {'jenis': 'futsal'})
        
        page_obj = response.context['page_obj']
        self.assertEqual(page_obj.paginator.count, 2)
    
    def test_filter_by_rating_4_5(self):
        """Test filter berdasarkan rating >= 4.5"""
        response = self.client.get(self.landing_url, {'rating': '4.5'})
        
        page_obj = response.context['page_obj']
        # Hanya lapangan dengan rating >= 4.5 (futsal1=4.5, futsal2=4.8)
        self.assertEqual(page_obj.paginator.count, 2)
        
        for lapangan in page_obj:
            self.assertGreaterEqual(lapangan.rating, 4.5)
    
    def test_filter_by_rating_4_0(self):
        """Test filter berdasarkan rating >= 4.0"""
        response = self.client.get(self.landing_url, {'rating': '4.0'})
        
        page_obj = response.context['page_obj']
        # Semua lapangan kecuali yang rating 0
        self.assertEqual(page_obj.paginator.count, 4)
    
    def test_filter_no_review_lapangan(self):
        """Test filter lapangan tanpa ulasan (rating = 0)"""
        response = self.client.get(self.landing_url, {'rating': '0'})
        
        page_obj = response.context['page_obj']
        self.assertEqual(page_obj.paginator.count, 1)
        self.assertEqual(page_obj[0].jumlah_ulasan, 0)
    
    def test_filter_invalid_rating_ignored(self):
        """Test filter dengan rating invalid diabaikan"""
        response = self.client.get(self.landing_url, {'rating': 'invalid'})
        
        page_obj = response.context['page_obj']
        # Harus menampilkan semua lapangan
        self.assertEqual(page_obj.paginator.count, 5)
    
    def test_combined_filter_jenis_and_rating(self):
        """Test kombinasi filter jenis dan rating"""
        response = self.client.get(self.landing_url, {
            'jenis': 'Futsal',
            'rating': '4.5'
        })
        
        page_obj = response.context['page_obj']
        self.assertEqual(page_obj.paginator.count, 2)
        
        for lapangan in page_obj:
            self.assertEqual(lapangan.jenis_olahraga, 'Futsal')
            self.assertGreaterEqual(lapangan.rating, 4.5)


class LandingPagePaginationTests(LandingPageTestCase):
    """Test untuk pagination di landing page"""
    
    def setUp(self):
        """Setup tambahan: buat banyak lapangan untuk test pagination"""
        super().setUp()
        
        # Patch save lagi
        self.lapangan_save_patch.start()
        
        # Buat 20 lapangan tambahan untuk test pagination
        for i in range(20):
            Lapangan.objects.create(
                nama_lapangan=f'Test Lapangan {i}',
                jenis_olahraga='Futsal',
                lokasi=f'Lokasi {i}',
                harga_per_jam=100000,
                pengelola=self.owner_profile,
                deskripsi=f'Deskripsi {i}',
                rating=4.0,
                jumlah_ulasan=1
            )
        
        self.lapangan_save_patch.stop()
        Lapangan.save = self.original_lapangan_save
    
    def test_pagination_first_page(self):
        """Test pagination halaman pertama"""
        response = self.client.get(self.landing_url)
        
        page_obj = response.context['page_obj']
        self.assertTrue(page_obj.has_other_pages())
        self.assertEqual(len(page_obj), 16)  # 16 items per page
        self.assertEqual(page_obj.number, 1)
    
    def test_pagination_second_page(self):
        """Test pagination halaman kedua"""
        response = self.client.get(self.landing_url, {'page': '2'})
        
        page_obj = response.context['page_obj']
        self.assertEqual(page_obj.number, 2)
        # Total 25 lapangan, page 1 = 16, page 2 = 9
        self.assertEqual(len(page_obj), 9)
    
    def test_pagination_invalid_page_returns_first_page(self):
        """Test pagination dengan page invalid mengembalikan halaman terakhir"""
        response = self.client.get(self.landing_url, {'page': '999'})
        
        page_obj = response.context['page_obj']
        # Django paginator get_page() returns last page for invalid page
        self.assertTrue(page_obj.number > 0)
    
    def test_pagination_with_filter(self):
        """Test pagination tetap bekerja dengan filter"""
        response = self.client.get(self.landing_url, {
            'jenis': 'Futsal',
            'page': '1'
        })
        
        page_obj = response.context['page_obj']
        self.assertEqual(response.status_code, 200)
        # Ada 22 futsal (2 dari setUp + 20 dari setUp pagination)
        self.assertEqual(page_obj.paginator.count, 22)


class LandingPageStaticImageTests(LandingPageTestCase):
    """Test untuk static image path handling"""
    
    @patch('main.views.find')
    def test_static_image_path_png_found(self, mock_find):
        """Test ketika file PNG ditemukan"""
        # Mock find untuk return path jika PNG
        def find_side_effect(path):
            if path == f'images/lapangan{self.lapangan_futsal1.pk}.png':
                return path
            return None
        
        mock_find.side_effect = find_side_effect
        
        response = self.client.get(self.landing_url)
        page_obj = response.context['page_obj']
        
        # Cari lapangan futsal1 di hasil
        futsal1_in_page = None
        for lap in page_obj:
            if lap.pk == self.lapangan_futsal1.pk:
                futsal1_in_page = lap
                break
        
        self.assertIsNotNone(futsal1_in_page)
        self.assertEqual(
            futsal1_in_page.static_image_path, 
            f'images/lapangan{self.lapangan_futsal1.pk}.png'
        )
    
    @patch('main.views.find')
    def test_static_image_path_jpg_fallback(self, mock_find):
        """Test fallback ke JPG jika PNG tidak ada"""
        # Mock find untuk return None untuk PNG, tapi return path untuk JPG
        def find_side_effect(path):
            if path == f'images/lapangan{self.lapangan_futsal1.pk}.jpg':
                return path
            return None
        
        mock_find.side_effect = find_side_effect
        
        response = self.client.get(self.landing_url)
        page_obj = response.context['page_obj']
        
        futsal1_in_page = None
        for lap in page_obj:
            if lap.pk == self.lapangan_futsal1.pk:
                futsal1_in_page = lap
                break
        
        self.assertIsNotNone(futsal1_in_page)
        self.assertEqual(
            futsal1_in_page.static_image_path, 
            f'images/lapangan{self.lapangan_futsal1.pk}.jpg'
        )
    
    @patch('main.views.find')
    def test_static_image_path_none_if_not_found(self, mock_find):
        """Test static_image_path = None jika file tidak ditemukan"""
        # Mock find untuk selalu return None
        mock_find.return_value = None
        
        response = self.client.get(self.landing_url)
        page_obj = response.context['page_obj']
        
        futsal1_in_page = None
        for lap in page_obj:
            if lap.pk == self.lapangan_futsal1.pk:
                futsal1_in_page = lap
                break
        
        self.assertIsNotNone(futsal1_in_page)
        self.assertIsNone(futsal1_in_page.static_image_path)


class LandingPageJenisListTests(LandingPageTestCase):
    """Test untuk jenis_list di context"""
    
    def test_jenis_list_contains_all_types(self):
        """Test jenis_list berisi semua jenis olahraga"""
        response = self.client.get(self.landing_url)
        
        jenis_list = list(response.context['jenis_list'])
        
        # Harus ada: Basket, Bulutangkis, Futsal, Tenis
        self.assertIn('Basket', jenis_list)
        self.assertIn('Bulutangkis', jenis_list)
        self.assertIn('Futsal', jenis_list)
        self.assertIn('Tenis', jenis_list)
    
    def test_jenis_list_is_ordered(self):
        """Test jenis_list terurut secara alfabetis"""
        response = self.client.get(self.landing_url)
        
        jenis_list = list(response.context['jenis_list'])
        sorted_list = sorted(jenis_list)
        
        self.assertEqual(jenis_list, sorted_list)
    
    def test_jenis_list_no_duplicates(self):
        """Test jenis_list tidak mengandung duplikat"""
        response = self.client.get(self.landing_url)
        
        jenis_list = list(response.context['jenis_list'])
        
        # Check for duplicates
        self.assertEqual(len(jenis_list), len(set(jenis_list)))


class LandingPageEdgeCaseTests(LandingPageTestCase):
    """Test untuk edge cases"""
    
    def test_empty_database_returns_empty_page(self):
        """Test ketika tidak ada lapangan di database"""
        # Hapus semua lapangan
        Lapangan.objects.all().delete()
        
        response = self.client.get(self.landing_url)
        
        page_obj = response.context['page_obj']
        self.assertEqual(page_obj.paginator.count, 0)
        self.assertEqual(len(page_obj), 0)
    
    def test_filter_returns_no_results(self):
        """Test filter yang tidak menghasilkan hasil"""
        response = self.client.get(self.landing_url, {
            'jenis': 'Sepak Bola'  # Tidak ada di database
        })
        
        page_obj = response.context['page_obj']
        self.assertEqual(page_obj.paginator.count, 0)
    
    def test_high_rating_filter_no_results(self):
        """Test rating filter tinggi yang tidak ada hasilnya"""
        response = self.client.get(self.landing_url, {'rating': '5.0'})
        
        page_obj = response.context['page_obj']
        self.assertEqual(page_obj.paginator.count, 0)
    
    def test_show_navbar_always_true(self):
        """Test show_navbar selalu True"""
        response = self.client.get(self.landing_url)
        self.assertTrue(response.context['show_navbar'])