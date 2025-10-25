# pbp-kelompok-d06/lapangin/lapangin-feat-admin-dashboard/community/tests.py

from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from community.models import Community, CommunityMember
from authbooking.models import Profile


class CommunityTests(TestCase):

    def setUp(self):
        """
        Menyiapkan data awal untuk setiap tes.
        - Membuat 1 user PEMILIK
        - Membuat 1 user PENYEWA
        - Membuat 1 Komunitas oleh PEMILIK
        """

        # 1. Membuat user PEMILIK
        self.pemilik_user = User.objects.create_user(
            username='pemilik_tes',
            password='password123'
        )

        # Buat atau ambil Profile terkait user ini
        self.pemilik_profile, _ = Profile.objects.get_or_create(
            user=self.pemilik_user,
            defaults={'role': 'PEMILIK'}
        )
        # Jika sudah ada, pastikan role-nya benar
        self.pemilik_profile.role = 'PEMILIK'
        self.pemilik_profile.save()

        # 2. Membuat user PENYEWA
        self.penyewa_user = User.objects.create_user(
            username='penyewa_tes',
            password='password123'
        )

        self.penyewa_profile, _ = Profile.objects.get_or_create(
            user=self.penyewa_user,
            defaults={'role': 'PENYEWA'}
        )
        self.penyewa_profile.role = 'PENYEWA'
        self.penyewa_profile.save()

        # 3. Membuat Komunitas
        self.community = Community.objects.create(
            community_name="Klub Futsal PBP",
            description="Tes deskripsi komunitas",
            location="Depok",
            sports_type="futsal",
            max_member=50,
            created_by=self.pemilik_user
        )

        # 4. Client untuk simulasi browser
        self.client = Client()

    def test_community_model_creation(self):
        """Tes apakah model Community berhasil dibuat di setUp."""
        komunitas = Community.objects.get(id=self.community.id)
        self.assertEqual(komunitas.community_name, "Klub Futsal PBP")
        self.assertEqual(komunitas.created_by, self.pemilik_user)
        self.assertEqual(Community.objects.count(), 1)

    def test_show_community_page_public_access(self):
        """Tes apakah halaman daftar komunitas (public) bisa diakses."""
        response = self.client.get(reverse('community:show_community_page'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Klub Futsal PBP")

    def test_community_detail_page_public_access(self):
        """Tes apakah halaman detail komunitas (public) bisa diakses."""
        response = self.client.get(reverse('community:show_detail_community', args=[self.community.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Tentang Komunitas")
        self.assertContains(response, "Tes deskripsi komunitas")

    def test_admin_community_list_access_as_pemilik(self):
        """Tes apakah user PEMILIK bisa mengakses halaman admin komunitas."""
        self.client.login(username='pemilik_tes', password='password123')
        response = self.client.get(reverse('community:admin_community_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Klub Futsal PBP")

    def test_admin_community_list_permission_denied_for_penyewa(self):
        """Tes apakah user PENYEWA ditolak saat mengakses halaman admin komunitas."""
        self.client.login(username='penyewa_tes', password='password123')
        response = self.client.get(reverse('community:admin_community_list'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)

    def test_admin_community_list_permission_denied_for_guest(self):
        """Tes apakah user yang belum login (Guest) ditolak saat mengakses halaman admin."""
        response = self.client.get(reverse('community:admin_community_list'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)

    def test_join_community_as_penyewa(self):
        """Tes apakah user PENYEWA bisa bergabung ke komunitas."""
        self.client.login(username='penyewa_tes', password='password123')
        self.assertFalse(
            CommunityMember.objects.filter(community=self.community, user=self.penyewa_user).exists()
        )
        response = self.client.post(reverse('community:join_community', args=[self.community.pk]), follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            CommunityMember.objects.filter(community=self.community, user=self.penyewa_user).exists()
        )
