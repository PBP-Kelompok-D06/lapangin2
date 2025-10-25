from django.test import TestCase
from django.urls import reverse

class MainTests(TestCase):
    def test_homepage_loads(self):
        response = self.client.get(reverse('main:home'))  # ganti sesuai nama url di main/urls.py
        self.assertEqual(response.status_code, 200)

