# review/tests.py
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from decimal import Decimal
import json

from authbooking.models import Profile
from booking.models import Lapangan
from review.models import Review


class ReviewModelTest(TestCase):
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.profile = Profile.objects.create(
            user=self.user,
            role='USER'
        )
        
        self.lapangan = Lapangan.objects.create(
            nama_lapangan='Test Futsal Arena',
            jenis_olahraga='Futsal',
            lokasi='Jakarta',
            harga_per_jam=150000,
            fasilitas='Parkir, Kantin',
            rating=0.00,
            jumlah_ulasan=0
        )
    
    def test_create_review(self):
        review = Review.objects.create(
            user=self.profile,
            field=self.lapangan,
            rating=5,
            content='Lapangan bagus sekali!'
        )
        
        self.assertEqual(review.rating, 5)
        self.assertEqual(review.content, 'Lapangan bagus sekali!')
        self.assertEqual(review.user, self.profile)
        self.assertEqual(review.field, self.lapangan)
    
    def test_review_str_method(self):
        review = Review.objects.create(
            user=self.profile,
            field=self.lapangan,
            rating=4,
            content='Bagus'
        )
        
        expected_str = f"Review by {self.user.username} for {self.lapangan.nama_lapangan} - Rating: 4"
        self.assertEqual(str(review), expected_str)


class ReviewViewsTest(TestCase):
    
    def setUp(self):
        self.client = Client()
        
        self.user1 = User.objects.create_user(
            username='user1',
            password='pass123'
        )
        self.profile1 = Profile.objects.create(
            user=self.user1,
            role='USER'
        )
        
        self.user2 = User.objects.create_user(
            username='user2',
            password='pass123'
        )
        self.profile2 = Profile.objects.create(
            user=self.user2,
            role='USER'
        )
        
        self.lapangan = Lapangan.objects.create(
            nama_lapangan='Test Arena',
            jenis_olahraga='Futsal',
            lokasi='Jakarta',
            harga_per_jam=100000,
            rating=0.00,
            jumlah_ulasan=0
        )
        
        self.review1 = Review.objects.create(
            user=self.profile1,
            field=self.lapangan,
            rating=5,
            content='Excellent!'
        )
        
        self.review2 = Review.objects.create(
            user=self.profile2,
            field=self.lapangan,
            rating=3,
            content='Average'
        )
    
    def test_review_list_view(self):
        self.client.login(username='user1', password='pass123')
        
        url = reverse('review:review_list', kwargs={'field_id': self.lapangan.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Ulasan untuk')
        self.assertContains(response, self.lapangan.nama_lapangan)
    
    def test_review_list_ajax(self):
        self.client.login(username='user1', password='pass123')
        
        url = reverse('review:review_list', kwargs={'field_id': self.lapangan.id})
        response = self.client.get(
            url,
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        
        self.assertIn('reviews', data)
        self.assertEqual(len(data['reviews']), 2)
    
    def test_add_review(self):
        self.client.login(username='user1', password='pass123')
        
        url = reverse('review:add_review', kwargs={'field_id': self.lapangan.id})
        data = {
            'content': 'Great place!',
            'rating': 5
        }
        
        response = self.client.post(
            url,
            data=json.dumps(data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        
        self.assertTrue(response_data['success'])
        self.assertEqual(Review.objects.count(), 3)
    
    def test_edit_review_owner(self):
        self.client.login(username='user1', password='pass123')
        
        url = reverse('review:review_edit', kwargs={'review_id': self.review1.id})
        data = {
            'content': 'Updated content',
            'rating': 4
        }
        
        response = self.client.post(
            url,
            data=json.dumps(data),
            content_type='application/json',
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        
        self.assertTrue(response_data['success'])
        
        # Check if review is updated
        self.review1.refresh_from_db()
        self.assertEqual(self.review1.content, 'Updated content')
        self.assertEqual(self.review1.rating, 4)
    
    def test_edit_review_not_owner(self):
        self.client.login(username='user2', password='pass123')
        
        url = reverse('review:review_edit', kwargs={'review_id': self.review1.id})
        data = {
            'content': 'Trying to edit',
            'rating': 1
        }
        
        response = self.client.post(
            url,
            data=json.dumps(data),
            content_type='application/json',
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        
        self.assertEqual(response.status_code, 404)
    
    def test_delete_review_owner(self):
        self.client.login(username='user1', password='pass123')
        
        url = reverse('review:delete_review', kwargs={'review_id': self.review1.id})
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        
        self.assertTrue(response_data['success'])
        self.assertEqual(Review.objects.count(), 1)
    
    def test_delete_review_not_owner(self):
        self.client.login(username='user2', password='pass123')
        
        url = reverse('review:delete_review', kwargs={'review_id': self.review1.id})
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        
        self.assertFalse(response_data['success'])
        self.assertEqual(Review.objects.count(), 2)
    
    def test_review_statistics(self):
        self.client.login(username='user1', password='pass123')
        
        url = reverse('review:review_statistics', kwargs={'field_id': self.lapangan.id})
        response = self.client.get(
            url,
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        
        self.assertIn('total_reviews', data)
        self.assertIn('rating_counts', data)
        self.assertIn('average_rating', data)
        
        self.assertEqual(data['total_reviews'], 2)
        self.assertEqual(data['average_rating'], 4.0)  # (5 + 3) / 2


class ReviewFilterTest(TestCase):
    
    def setUp(self):
        self.client = Client()
        
        # Create user
        self.user = User.objects.create_user(
            username='testuser',
            password='pass123'
        )
        self.profile = Profile.objects.create(
            user=self.user,
            role='USER'
        )
        
        self.lapangan = Lapangan.objects.create(
            nama_lapangan='Test Arena',
            jenis_olahraga='Futsal',
            lokasi='Jakarta',
            harga_per_jam=100000
        )
        
        # Create multiple reviews with different ratings
        for i in range(1, 6):
            Review.objects.create(
                user=self.profile,
                field=self.lapangan,
                rating=i,
                content=f'Review rating {i}'
            )
    
    def test_filter_by_rating(self):
        self.client.login(username='testuser', password='pass123')
        
        url = reverse('review:review_list', kwargs={'field_id': self.lapangan.id})
        response = self.client.get(
            f'{url}?filter=5',
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        
        self.assertEqual(len(data['reviews']), 1)
        self.assertEqual(data['reviews'][0]['rating'], 5)
    
    def test_filter_terbaru(self):
        self.client.login(username='testuser', password='pass123')
        
        url = reverse('review:review_list', kwargs={'field_id': self.lapangan.id})
        response = self.client.get(
            f'{url}?filter=terbaru',
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        
        self.assertEqual(len(data['reviews']), 5)


class LapanganRatingUpdateTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='pass123'
        )
        self.profile = Profile.objects.create(
            user=self.user,
            role='USER'
        )
        
        self.lapangan = Lapangan.objects.create(
            nama_lapangan='Test Arena',
            jenis_olahraga='Futsal',
            lokasi='Jakarta',
            harga_per_jam=100000,
            rating=0.00,
            jumlah_ulasan=0
        )
    
    def test_rating_update_after_add_review(self):
        Review.objects.create(
            user=self.profile,
            field=self.lapangan,
            rating=5,
            content='Great!'
        )
        
        self.lapangan.update_rating()
        self.lapangan.refresh_from_db()
        
        self.assertEqual(self.lapangan.rating, Decimal('5.00'))
        self.assertEqual(self.lapangan.jumlah_ulasan, 1)
    
    def test_rating_average_calculation(self):
        Review.objects.create(
            user=self.profile,
            field=self.lapangan,
            rating=5,
            content='Excellent'
        )
        Review.objects.create(
            user=self.profile,
            field=self.lapangan,
            rating=3,
            content='Average'
        )
        
        self.lapangan.update_rating()
        self.lapangan.refresh_from_db()
        
        self.assertEqual(self.lapangan.rating, Decimal('4.00'))
        self.assertEqual(self.lapangan.jumlah_ulasan, 2)
    
    def test_rating_after_delete_review(self):
        review1 = Review.objects.create(
            user=self.profile,
            field=self.lapangan,
            rating=5,
            content='Great'
        )
        Review.objects.create(
            user=self.profile,
            field=self.lapangan,
            rating=3,
            content='OK'
        )
        
        self.lapangan.update_rating()
        self.lapangan.refresh_from_db()
        
        review1.delete()
        
        self.lapangan.update_rating()
        self.lapangan.refresh_from_db()
        
        self.assertEqual(self.lapangan.rating, Decimal('3.00'))
        self.assertEqual(self.lapangan.jumlah_ulasan, 1)