# pbp-kelompok-d06/lapangin/lapangin-feat-admin-dashboard/community/tests.py

from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from community.models import Community, CommunityMember, CommunityRequest, CommunityPost
from authbooking.models import Profile

class CommunityTests(TestCase):

    def setUp(self):
        """
        Menyiapkan data awal untuk setiap tes.
        - Membuat 1 user PEMILIK
        - Membuat 1 user PENYEWA
        - Membuat 1 Komunitas oleh PEMILIK
        """
        
        # 1. Membuat user PEMILIK (admin)
        self.pemilik_user = User.objects.create_user(
            username='pemilik_tes', 
            password='password123'
        )
        # Refresh user object from DB to load related profile created by signal
        self.pemilik_user.refresh_from_db() # <-- TAMBAHKAN BARIS INI
        # Mengatur role-nya via Profile
        self.pemilik_user.profile.role = 'PEMILIK'
        self.pemilik_user.profile.save()

        # 2. Membuat user PENYEWA (member)
        self.penyewa_user = User.objects.create_user(
            username='penyewa_tes', 
            password='password123'
        )
        # Refresh user object from DB to load related profile created by signal
        self.penyewa_user.refresh_from_db() # <-- TAMBAHKAN BARIS INI
        # Role default-nya sudah 'PENYEWA', tapi kita pastikan
        self.penyewa_user.profile.role = 'PENYEWA'
        self.penyewa_user.profile.save()

        # 3. Membuat Komunitas
        self.community = Community.objects.create(
            community_name="Klub Futsal PBP",
            description="Tes deskripsi komunitas",
            location="Depok",
            sports_type="futsal",
            max_member=50,
            created_by=self.pemilik_user
        )
        
        # 4. Menyiapkan client (browser virtual)
        self.client = Client()

    def test_community_model_creation(self):
        """Tes apakah model Community berhasil dibuat di setUp."""
        komunitas = Community.objects.get(id=self.community.id)
        self.assertEqual(komunitas.community_name, "Klub Futsal PBP")
        self.assertEqual(komunitas.created_by, self.pemilik_user)
        self.assertEqual(Community.objects.count(), 1)

    def test_show_community_page_public_access(self):
        """Tes apakah halaman daftar komunitas (public) bisa diakses."""
        # 'community:show_community_page' didapat dari community/urls.py
        response = self.client.get(reverse('community:show_community_page'))
        
        # Cek status 200 (OK)
        self.assertEqual(response.status_code, 200)
        # Cek apakah nama komunitas tes kita muncul di halaman
        self.assertContains(response, "Klub Futsal PBP")

    def test_community_detail_page_public_access(self):
        """Tes apakah halaman detail komunitas (public) bisa diakses."""
        response = self.client.get(reverse('community:show_detail_community', args=[self.community.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Tentang Komunitas")
        self.assertContains(response, "Tes deskripsi komunitas")

    def test_admin_community_list_access_as_pemilik(self):
        """Tes apakah user PEMILIK bisa mengakses halaman admin komunitas."""
        # Login sebagai pemilik
        self.client.login(username='pemilik_tes', password='password123')
        
        response = self.client.get(reverse('community:admin_community_list'))
        
        # Cek status 200 (OK)
        self.assertEqual(response.status_code, 200)
        # Cek apakah nama komunitasnya ada di dashboard-nya
        self.assertContains(response, "Klub Futsal PBP")

    def test_admin_community_list_permission_denied_for_penyewa(self):
        """Tes apakah user PENYEWA ditolak saat mengakses halaman admin komunitas."""
        # Login sebagai penyewa
        self.client.login(username='penyewa_tes', password='password123')
        
        response = self.client.get(reverse('community:admin_community_list'))
        
        # Harusnya di-redirect (status 302) ke halaman login
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)

    def test_admin_community_list_permission_denied_for_guest(self):
        """Tes apakah user yang belum login (Guest) ditolak saat mengakses halaman admin."""
        # Tidak login
        response = self.client.get(reverse('community:admin_community_list'))
        
        # Harusnya di-redirect (status 302) ke halaman login
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)

    def test_join_community_as_penyewa(self):
        """Tes apakah user PENYEWA bisa bergabung ke komunitas."""
        # Login sebagai penyewa
        self.client.login(username='penyewa_tes', password='password123')
        
        # Pastikan user belum join
        self.assertFalse(
            CommunityMember.objects.filter(community=self.community, user=self.penyewa_user).exists()
        )
        
        # Jalankan view 'join_community'. 
        # follow=True berarti client akan mengikuti redirect setelah join
        response = self.client.post(reverse('community:join_community', args=[self.community.pk]), follow=True)
        
        # Cek apakah view-nya berhasil dan kembali ke halaman detail
        self.assertEqual(response.status_code, 200)
        
        # Cek apakah data CommunityMember sudah dibuat di database
        self.assertTrue(
            CommunityMember.objects.filter(community=self.community, user=self.penyewa_user).exists()
        )