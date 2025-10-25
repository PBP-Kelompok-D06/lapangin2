from django.test import TestCase, Client
from django.urls import reverse
from unittest.mock import patch, MagicMock
from django.http import Http404
from datetime import datetime
from django.contrib.auth.models import User 

# --- Custom Mock Classes untuk Rendering Template ---

class MockUserProfile:
    """Mock untuk model Profile/authbooking.models.Profile."""
    def __init__(self, user_instance):
        # Ini adalah User nyata dari Django
        self.user = user_instance 

class MockReview:
    """Mock untuk model Review yang lebih realistis untuk rendering template."""
    def __init__(self, user_instance, content, rating, created_at):
        # Foreign Key ke MockUserProfile
        self.user = MockUserProfile(user_instance)
        
        # Atribut nyata
        self.content = content
        self.rating = rating
        self.created_at = created_at
        
        # Tambahkan atribut is_owner agar tidak perlu di-set di view.
        # Catatan: View Anda set is_owner setelah QuerySet diambil, jadi kita biarkan view yang mengaturnya.
        self.is_owner = False 


# --- Mocking Helper Functions ---

def create_mock_lapangan(lap_id, fasilitas_str, nomor_wa):
    mock_pengelola = MagicMock(nomor_whatsapp=nomor_wa) 
    lapangan = MagicMock(
        pk=lap_id,
        id=lap_id,
        fasilitas=fasilitas_str,
        pengelola=mock_pengelola,
        DoesNotExist=object(),
        nama_lapangan='Lapangan Test', 
        harga_per_jam=100000 
    )
    return lapangan

def create_mock_review(user_instance, content, rating, created_at):
    # Menggunakan kelas MockReview sebagai ganti MagicMock
    return MockReview(user_instance, content, rating, created_at)

# -------------------------------


class GalleryViewTest(TestCase):
    
    def setUp(self):
        self.client = Client() 
        self.lap_id = 1
        self.url = reverse('gallery:show_gallery', kwargs={'lap_id': self.lap_id})
        
        # FIX JSON ERROR: Gunakan objek User nyata yang dibuat di test database
        # self.user1 dan self.user2 sekarang adalah objek User yang dapat di-serialize.
        self.user1 = User.objects.create_user(username='testuser1', password='password')
        self.user2 = User.objects.create_user(username='testuser2', password='password')
        
        self.anon_user = MagicMock(is_authenticated=False)

    # Mock Lapangan dan Reviews
    def get_mock_lapangan_and_reviews(self):
        mock_lapangan = create_mock_lapangan(
            lap_id=self.lap_id,
            fasilitas_str='Wifi, Toilet, Kantin',
            nomor_wa='08123456789' 
        )
        
        # Reviews menggunakan objek MockReview (bukan MagicMock)
        reviews_data = [
            (self.user1, 'Bagus sekali!', 5, datetime(2025, 10, 25, 10, 0, 0)), 
            (self.user2, 'Bersih', 4, datetime(2025, 10, 24, 10, 0, 0)),
            (self.user1, 'Pelayanan ramah', 5, datetime(2025, 10, 23, 10, 0, 0)),
            (self.user2, 'Agak mahal', 3, datetime(2025, 10, 22, 10, 0, 0)),
        ]
        mock_reviews = [
            create_mock_review(user_instance, content, rating, created_at)
            for user_instance, content, rating, created_at in reviews_data
        ]
        
        # Mock QuerySet
        mock_queryset = MagicMock()
        mock_queryset.order_by.return_value = mock_queryset 
        # PENTING: return value dari __getitem__ sekarang adalah list of MockReview objects
        mock_queryset.__getitem__.return_value = mock_reviews 
        mock_queryset.filter.return_value = mock_queryset 
        
        return mock_lapangan, mock_reviews, mock_queryset

    
    # TEST CASE 1: Pengguna terautentikasi (Diharapkan sukses)
    @patch('gallery.views.get_object_or_404')
    @patch('gallery.views.Review.objects')
    def test_show_gallery_success_authenticated_owner(self, mock_review_manager, mock_get_object_or_404):
        mock_lapangan, mock_reviews, mock_queryset = self.get_mock_lapangan_and_reviews()
        mock_get_object_or_404.return_value = mock_lapangan
        mock_review_manager.filter.return_value = mock_queryset
        
        self.client.force_login(self.user1) 
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, 200)
        
        context_reviews = response.context['reviews']
        
        # Assertion is_owner
        self.assertTrue(context_reviews[0].is_owner) 
        self.assertFalse(context_reviews[1].is_owner)
        self.assertTrue(context_reviews[2].is_owner)

    # TEST CASE 2: Pengguna anonim (Diharapkan sukses setelah perbaikan mock data)

    @patch('gallery.views.get_object_or_404')
    @patch('gallery.views.Review.objects')
    def test_show_gallery_success_anonymous(self, mock_review_manager, mock_get_object_or_404):
        mock_lapangan, mock_reviews, mock_queryset = self.get_mock_lapangan_and_reviews()
        mock_get_object_or_404.return_value = mock_lapangan
        mock_review_manager.filter.return_value = mock_queryset
        
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, 200)
        
        context_reviews = response.context['reviews']
        for review in context_reviews:
            self.assertFalse(review.is_owner)
            

    # TEST CASE 3: Lapangan tidak ditemukan (404)
    @patch('gallery.views.get_object_or_404')
    def test_show_gallery_lapangan_not_found(self, mock_get_object_or_404):
        mock_get_object_or_404.side_effect = Http404
        
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, 404)


    # TEST CASE 4: Konversi WA dari 08...
    @patch('gallery.views.get_object_or_404')
    @patch('gallery.views.Review.objects')
    def test_whatsapp_conversion_zero_start(self, mock_review_manager, mock_get_object_or_404):
        mock_lapangan = create_mock_lapangan(
            lap_id=2,
            fasilitas_str='',
            nomor_wa='(081) 234-567-890'
        )
        mock_get_object_or_404.return_value = mock_lapangan
        mock_review_manager.filter.return_value = MagicMock(order_by=MagicMock(return_value=MagicMock(__getitem__=MagicMock(return_value=[])))) 
        
        url_2 = reverse('gallery:show_gallery', kwargs={'lap_id': 2})
        response = self.client.get(url_2)
        
        self.assertEqual(response.context['nomor_whatsapp'], '6281234567890')


    # TEST CASE 5: Pengelola tidak ada atau tidak punya nomor WA
    
    @patch('gallery.views.get_object_or_404')
    @patch('gallery.views.Review.objects')
    def test_whatsapp_none_or_empty(self, mock_review_manager, mock_get_object_or_404):
        mock_review_manager.filter.return_value = MagicMock(order_by=MagicMock(return_value=MagicMock(__getitem__=MagicMock(return_value=[]))))
        
        # Case 1: Nomor WA None
        mock_lapangan_none = create_mock_lapangan(lap_id=3, fasilitas_str='', nomor_wa=None)
        mock_get_object_or_404.return_value = mock_lapangan_none
        
        url_3 = reverse('gallery:show_gallery', kwargs={'lap_id': 3})
        response_none = self.client.get(url_3)
        self.assertIsNone(response_none.context['nomor_whatsapp'])
        
        # Case 2: Pengelola None
        mock_lapangan_no_pengelola = MagicMock(id=4, pk=4, fasilitas='AC', pengelola=None, nama_lapangan='Lap 4', harga_per_jam=50000)
        mock_get_object_or_404.return_value = mock_lapangan_no_pengelola
        
        url_4 = reverse('gallery:show_gallery', kwargs={'lap_id': 4})
        response_no_pengelola = self.client.get(url_4)
        self.assertIsNone(response_no_pengelola.context['nomor_whatsapp'])