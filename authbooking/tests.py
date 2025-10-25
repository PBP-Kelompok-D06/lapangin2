from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User

class AuthBookingTests(TestCase):
    def test_register_page_loads(self):
        response = self.client.get(reverse('authbooking:register'))
        self.assertEqual(response.status_code, 200)

    def test_login_page_loads(self):
        response = self.client.get(reverse('authbooking:login'))
        self.assertEqual(response.status_code, 200)

    def test_register_post_creates_user(self):
        response = self.client.post(
            reverse('authbooking:register'),
            {
                'username': 'testuser',
                'password1': 'StrongPassword!123', #buat password yang kuat biar berhasil register oleh django
                'password2': 'StrongPassword!123',
                'role': 'PEMILIK',
                'nomor_rekening': '1234567890', 
                'nomor_whatsapp': '08123456789',
            },
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
    
        self.assertTrue(User.objects.filter(username='testuser').exists())


    def test_login_post_redirects(self):
        User.objects.create_user(username='testuser', password='abc123456')
        data = {
            'username': 'testuser',
            'password': 'abc123456'
        }
        response = self.client.post(
            reverse('authbooking:login'),
            data,
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn('application/json', response['Content-Type'])

    def test_logout_redirects(self):
        User.objects.create_user(username='testuser', password='abc123456')
        self.client.login(username='testuser', password='abc123456')
        response = self.client.get(reverse('authbooking:logout'))
        # Logout kemungkinan redirect ke login
        self.assertEqual(response.status_code, 302)