from django.test import TestCase, Client
from django.contrib.auth.models import User
from booking.models import Booking, Lapangan, SlotTersedia
from authbooking.models import Profile
from datetime import date, time, timedelta
from django.urls import reverse
from django.utils import timezone
import json
from django.db.models.signals import post_save
from booking.signals import create_booking_slots
from unittest.mock import patch
import os


class BookingTestSetup(TestCase):
    """Base setup untuk semua booking tests"""
    
    def setUp(self):
        self.client = Client()
        
        # Matikan signal biar gak auto-create 1120 slot tiap test
        post_save.disconnect(create_booking_slots, sender=Lapangan)
        
        # Buat user dan profile
        self.user = User.objects.create_user(
            username='user1', 
            password='password123',
            email='user1@test.com'
        )
        self.user_profile = Profile.objects.create(
            user=self.user,
            role='PENYEWA'
        )
        
        # Buat owner user dan profile
        self.owner = User.objects.create_user(
            username='owner',
            password='password123',
            email='owner@test.com'
        )
        self.owner_profile = Profile.objects.create(
            user=self.owner,
            role='PEMILIK',
            nomor_whatsapp='081234567890',
            nomor_rekening='1234567890'
        )
        
        # Buat lapangan manual
        self.lapangan = Lapangan.objects.create(
            nama_lapangan='Lapangan Futsal A',
            jenis_olahraga='Futsal',
            lokasi='Jakarta',
            harga_per_jam=100000,
            fasilitas='Toilet, Kantin',
            rating=4.5,
            jumlah_ulasan=10,
            pengelola=self.owner_profile
        )
        
        # Buat slot manual untuk hari ini
        self.slot_today = SlotTersedia.objects.create(
            lapangan=self.lapangan,
            tanggal=date.today(),
            jam_mulai=time(9, 0),
            jam_akhir=time(10, 0),
            is_available=True
        )
        
        # Buat slot untuk besok
        self.slot_tomorrow = SlotTersedia.objects.create(
            lapangan=self.lapangan,
            tanggal=date.today() + timedelta(days=1),
            jam_mulai=time(10, 0),
            jam_akhir=time(11, 0),
            is_available=True
        )


class ShowBookingPageTests(BookingTestSetup):
    """Test untuk show_booking_page view"""
    
    def test_booking_page_renders_successfully(self):
        """Test halaman booking dapat diakses"""
        url = reverse('booking:show_booking_page')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'booking.html')
    
    def test_booking_page_shows_lapangan(self):
        """Test halaman menampilkan lapangan"""
        url = reverse('booking:show_booking_page')
        response = self.client.get(url)
        
        self.assertIn('lapangan_terpilih', response.context)
        self.assertIn('all_lapangan', response.context)
        self.assertEqual(
            response.context['lapangan_terpilih'].pk, 
            self.lapangan.pk
        )
    
    def test_booking_page_filter_by_lapangan(self):
        """Test filter by lapangan_id"""
        url = reverse('booking:show_booking_page')
        response = self.client.get(url, {'lapangan_id': self.lapangan.pk})
        
        self.assertEqual(
            response.context['lapangan_terpilih'].pk,
            self.lapangan.pk
        )
    
    def test_booking_page_filter_by_date(self):
        """Test filter by date"""
        test_date = date.today() + timedelta(days=2)
        url = reverse('booking:show_booking_page')
        response = self.client.get(url, {
            'date': test_date.strftime('%Y-%m-%d')
        })
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('filter_date_str', response.context)
    
    def test_booking_page_invalid_date_fallback(self):
        """Test invalid date falls back to today"""
        url = reverse('booking:show_booking_page')
        response = self.client.get(url, {'date': 'invalid-date'})
        
        self.assertEqual(response.status_code, 200)
        # Should fallback to today
        filter_date = date.fromisoformat(response.context['filter_date_str'])
        self.assertEqual(filter_date, date.today())
    
    def test_booking_page_shows_slots_by_date(self):
        """Test slots organized by date"""
        url = reverse('booking:show_booking_page')
        response = self.client.get(url)
        
        self.assertIn('slots_by_date', response.context)
        slots_by_date = response.context['slots_by_date']
        
        # Should have 7 days
        self.assertEqual(len(slots_by_date), 7)
    
    def test_booking_page_slot_status_available(self):
        """Test slot status AVAILABLE"""
        url = reverse('booking:show_booking_page')
        response = self.client.get(url)
        
        slots_by_date = response.context['slots_by_date']
        today_slots = slots_by_date.get(date.today(), [])
        
        if today_slots:
            slot = today_slots[0]
            self.assertEqual(slot.display_status, 'AVAILABLE')
    
    def test_booking_page_slot_status_booked(self):
        """Test slot status BOOKED"""
        # Mark slot as not available
        self.slot_today.is_available = False
        self.slot_today.save()
        
        url = reverse('booking:show_booking_page')
        response = self.client.get(url)
        
        slots_by_date = response.context['slots_by_date']
        today_slots = slots_by_date.get(date.today(), [])
        
        if today_slots:
            booked_slot = [s for s in today_slots if s.pk == self.slot_today.pk][0]
            self.assertEqual(booked_slot.display_status, 'BOOKED')
    
    def test_booking_page_slot_status_pending(self):
        """Test slot status PENDING"""
        # Create pending booking
        booking = Booking.objects.create(
            user=self.user,
            slot=self.slot_today,
            tanggal_booking=timezone.now(),
            total_bayar=100000,
            status_pembayaran='PENDING'
        )
        self.slot_today.pending_booking = booking
        self.slot_today.save()
        
        url = reverse('booking:show_booking_page')
        response = self.client.get(url)
        
        slots_by_date = response.context['slots_by_date']
        today_slots = slots_by_date.get(date.today(), [])
        
        if today_slots:
            pending_slot = [s for s in today_slots if s.pk == self.slot_today.pk][0]
            self.assertEqual(pending_slot.display_status, 'PENDING')
    
    @patch('os.path.exists')
    def test_booking_page_hero_image_exists(self, mock_exists):
        """Test hero image when file exists"""
        mock_exists.return_value = True
        
        url = reverse('booking:show_booking_page')
        response = self.client.get(url)
        
        expected_image = f'images/lapangan{self.lapangan.id}.png'
        self.assertEqual(response.context['hero_image_url'], expected_image)
    
    @patch('os.path.exists')
    def test_booking_page_hero_image_default(self, mock_exists):
        """Test default hero image when file not exists"""
        mock_exists.return_value = False
        
        url = reverse('booking:show_booking_page')
        response = self.client.get(url)
        
        self.assertEqual(
            response.context['hero_image_url'], 
            'images/lapangan_default.jpg'
        )
    
    def test_booking_page_no_lapangan_shows_error(self):
        """Test error when no lapangan in database"""
        # Delete all lapangan
        Lapangan.objects.all().delete()
        
        url = reverse('booking:show_booking_page')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'login.html')


class CreateBookingTests(BookingTestSetup):
    """Test untuk create_booking view"""
    
    def test_create_booking_requires_login(self):
        """Test create booking requires authentication"""
        self.client.logout()
        
        url = reverse('booking:create_booking')
        response = self.client.post(
            url,
            data=json.dumps({'slot_id': self.slot_today.pk}),
            content_type='application/json'
        )
        
        # Should redirect to login
        self.assertEqual(response.status_code, 302)
    
    def test_create_booking_success(self):
        """Test successful booking creation"""
        self.client.force_login(self.user)
        
        url = reverse('booking:create_booking')
        response = self.client.post(
            url,
            data=json.dumps({'slot_id': self.slot_today.pk}),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertIn('booking_id', data)
        
        # Verify booking created
        booking = Booking.objects.get(pk=data['booking_id'])
        self.assertEqual(booking.user, self.user)
        self.assertEqual(booking.slot, self.slot_today)
        self.assertEqual(booking.status_pembayaran, 'PENDING')
    
    def test_create_booking_updates_slot_pending(self):
        """Test slot updated with pending_booking"""
        self.client.force_login(self.user)
        
        url = reverse('booking:create_booking')
        response = self.client.post(
            url,
            data=json.dumps({'slot_id': self.slot_today.pk}),
            content_type='application/json'
        )
        
        data = response.json()
        booking_id = data['booking_id']
        
        # Verify slot updated
        self.slot_today.refresh_from_db()
        self.assertIsNotNone(self.slot_today.pending_booking)
        self.assertEqual(self.slot_today.pending_booking.pk, booking_id)
    
    def test_create_booking_invalid_slot(self):
        """Test booking with invalid slot_id"""
        self.client.force_login(self.user)
        
        url = reverse('booking:create_booking')
        response = self.client.post(
            url,
            data=json.dumps({'slot_id': 99999}),
            content_type='application/json'
        )
        
        # View catches exception and returns 500 with error message
        self.assertEqual(response.status_code, 500)
        data = response.json()
        self.assertIn('message', data)
        self.assertIn('Error', data['message'])
    
    def test_create_booking_calculates_total(self):
        """Test total_bayar calculated correctly"""
        self.client.force_login(self.user)
        
        url = reverse('booking:create_booking')
        response = self.client.post(
            url,
            data=json.dumps({'slot_id': self.slot_today.pk}),
            content_type='application/json'
        )
        
        data = response.json()
        booking = Booking.objects.get(pk=data['booking_id'])
        
        self.assertEqual(booking.total_bayar, self.lapangan.harga_per_jam)
    
    def test_create_booking_method_not_allowed(self):
        """Test GET method not allowed"""
        self.client.force_login(self.user)
        
        url = reverse('booking:create_booking')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 405)
        data = response.json()
        self.assertIn('tidak diizinkan', data['message'].lower())
    
    def test_create_booking_handles_exception(self):
        """Test error handling"""
        self.client.force_login(self.user)
        
        url = reverse('booking:create_booking')
        # Send invalid JSON
        response = self.client.post(
            url,
            data='invalid json',
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 500)


class CheckSlotStatusTests(BookingTestSetup):
    """Test untuk check_slot_status AJAX view"""
    
    def test_check_slot_status_requires_lapangan_id(self):
        """Test requires lapangan_id parameter"""
        url = reverse('booking:check_slot_status')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn('error', data)
    
    def test_check_slot_status_invalid_lapangan(self):
        """Test with invalid lapangan_id"""
        url = reverse('booking:check_slot_status')
        response = self.client.get(url, {'lapangan_id': 99999})
        
        self.assertEqual(response.status_code, 404)
    
    def test_check_slot_status_returns_slot_data(self):
        """Test returns correct slot status data"""
        url = reverse('booking:check_slot_status')
        response = self.client.get(url, {'lapangan_id': self.lapangan.pk})
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertIsInstance(data, list)
        self.assertTrue(len(data) > 0)
        
        # Check data structure
        slot_data = data[0]
        self.assertIn('id', slot_data)
        self.assertIn('status', slot_data)
    
    def test_check_slot_status_available(self):
        """Test AVAILABLE status"""
        url = reverse('booking:check_slot_status')
        response = self.client.get(url, {'lapangan_id': self.lapangan.pk})
        
        data = response.json()
        available_slot = [s for s in data if s['id'] == self.slot_today.pk][0]
        
        self.assertEqual(available_slot['status'], 'AVAILABLE')
    
    def test_check_slot_status_booked(self):
        """Test BOOKED status"""
        self.slot_today.is_available = False
        self.slot_today.save()
        
        url = reverse('booking:check_slot_status')
        response = self.client.get(url, {'lapangan_id': self.lapangan.pk})
        
        data = response.json()
        booked_slot = [s for s in data if s['id'] == self.slot_today.pk][0]
        
        self.assertEqual(booked_slot['status'], 'BOOKED')
    
    def test_check_slot_status_pending(self):
        """Test PENDING status"""
        booking = Booking.objects.create(
            user=self.user,
            slot=self.slot_today,
            tanggal_booking=timezone.now(),
            total_bayar=100000,
            status_pembayaran='PENDING'
        )
        self.slot_today.pending_booking = booking
        self.slot_today.save()
        
        url = reverse('booking:check_slot_status')
        response = self.client.get(url, {'lapangan_id': self.lapangan.pk})
        
        data = response.json()
        pending_slot = [s for s in data if s['id'] == self.slot_today.pk][0]
        
        self.assertEqual(pending_slot['status'], 'PENDING')


class ShowPaymentPageTests(BookingTestSetup):
    """Test untuk show_payment_page view"""
    
    def setUp(self):
        super().setUp()
        # Create booking for payment tests
        self.booking = Booking.objects.create(
            user=self.user,
            slot=self.slot_today,
            tanggal_booking=timezone.now(),
            total_bayar=100000,
            status_pembayaran='PENDING'
        )
    
    def test_payment_page_requires_login(self):
        """Test payment page requires authentication"""
        self.client.logout()
        
        url = reverse('booking:show_payment_page', kwargs={
            'booking_id': self.booking.pk
        })
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 302)
    
    def test_payment_page_renders_successfully(self):
        """Test payment page renders"""
        self.client.force_login(self.user)
        
        url = reverse('booking:show_payment_page', kwargs={
            'booking_id': self.booking.pk
        })
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'payment_detail.html')
    
    def test_payment_page_shows_booking_info(self):
        """Test payment page shows booking info"""
        self.client.force_login(self.user)
        
        url = reverse('booking:show_payment_page', kwargs={
            'booking_id': self.booking.pk
        })
        response = self.client.get(url)
        
        self.assertEqual(response.context['booking'].pk, self.booking.pk)
        self.assertIn('no_rekening', response.context)
        self.assertIn('contact_whatsapp', response.context)
    
    def test_payment_page_other_user_forbidden(self):
        """Test other user cannot access payment page"""
        other_user = User.objects.create_user(
            username='other',
            password='pass'
        )
        self.client.force_login(other_user)
        
        url = reverse('booking:show_payment_page', kwargs={
            'booking_id': self.booking.pk
        })
        response = self.client.get(url, follow=True)
        
        # Should redirect with error message
        messages = list(response.context['messages'])
        self.assertTrue(
            any('tidak memiliki akses' in str(m).lower() for m in messages)
        )
    
    def test_payment_page_timeout_countdown(self):
        """Test timeout countdown for PENDING booking"""
        self.client.force_login(self.user)
        
        url = reverse('booking:show_payment_page', kwargs={
            'booking_id': self.booking.pk
        })
        response = self.client.get(url)
        
        self.assertIsNotNone(response.context['time_to_expire_ms'])
    
    def test_payment_page_timeout_expired(self):
        """Test booking cancelled after timeout"""
        # Set booking time to past (more than 5 minutes ago)
        self.booking.tanggal_booking = timezone.now() - timedelta(minutes=10)
        self.booking.save()
        
        self.slot_today.pending_booking = self.booking
        self.slot_today.save()
        
        self.client.force_login(self.user)
        
        url = reverse('booking:show_payment_page', kwargs={
            'booking_id': self.booking.pk
        })
        response = self.client.get(url, follow=True)
        
        # Should redirect to booking page
        self.assertRedirects(
            response, 
            reverse('booking:show_booking_page')
        )
        
        # Booking should be cancelled
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status_pembayaran, 'CANCELLED')
        
        # Slot should be cleared
        self.slot_today.refresh_from_db()
        self.assertIsNone(self.slot_today.pending_booking)
    
    def test_payment_page_paid_no_countdown(self):
        """Test no countdown for PAID booking"""
        self.booking.status_pembayaran = 'PAID'
        self.booking.save()
        
        self.client.force_login(self.user)
        
        url = reverse('booking:show_payment_page', kwargs={
            'booking_id': self.booking.pk
        })
        response = self.client.get(url)
        
        self.assertIsNone(response.context['time_to_expire_ms'])
    
    def test_payment_page_404_invalid_booking(self):
        """Test 404 for invalid booking_id"""
        self.client.force_login(self.user)
        
        url = reverse('booking:show_payment_page', kwargs={
            'booking_id': 99999
        })
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 404)


class MyBookingsTests(BookingTestSetup):
    """Test untuk my_bookings view"""
    
    def test_my_bookings_requires_login(self):
        """Test my bookings requires authentication"""
        self.client.logout()
        
        url = reverse('booking:my_bookings')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 302)
    
    def test_my_bookings_renders_successfully(self):
        """Test my bookings page renders"""
        self.client.force_login(self.user)
        
        url = reverse('booking:my_bookings')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'my_bookings.html')
    
    def test_my_bookings_shows_paid_bookings(self):
        """Test shows PAID bookings"""
        # Create PAID booking
        Booking.objects.create(
            user=self.user,
            slot=self.slot_today,
            tanggal_booking=timezone.now(),
            total_bayar=100000,
            status_pembayaran='PAID'
        )
        
        self.client.force_login(self.user)
        
        url = reverse('booking:my_bookings')
        response = self.client.get(url)
        
        self.assertEqual(len(response.context['bookings']), 1)
    
    def test_my_bookings_shows_locked_slots(self):
        """Test shows bookings with locked slots"""
        # Mark slot as not available
        self.slot_today.is_available = False
        self.slot_today.save()
        
        # Create booking
        Booking.objects.create(
            user=self.user,
            slot=self.slot_today,
            tanggal_booking=timezone.now(),
            total_bayar=100000,
            status_pembayaran='PENDING'
        )
        
        self.client.force_login(self.user)
        
        url = reverse('booking:my_bookings')
        response = self.client.get(url)
        
        self.assertTrue(len(response.context['bookings']) > 0)
    
    def test_my_bookings_excludes_pending_available(self):
        """Test excludes PENDING bookings with available slots"""
        # Create PENDING booking with available slot
        Booking.objects.create(
            user=self.user,
            slot=self.slot_tomorrow,
            tanggal_booking=timezone.now(),
            total_bayar=100000,
            status_pembayaran='PENDING'
        )
        
        self.client.force_login(self.user)
        
        url = reverse('booking:my_bookings')
        response = self.client.get(url)
        
        # Should be empty or not include the pending booking
        pending_bookings = [
            b for b in response.context['bookings'] 
            if b.status_pembayaran == 'PENDING' and b.slot.is_available
        ]
        self.assertEqual(len(pending_bookings), 0)
    
    def test_my_bookings_empty_for_new_user(self):
        """Test empty bookings for new user"""
        new_user = User.objects.create_user(
            username='newuser',
            password='pass'
        )
        self.client.force_login(new_user)
        
        url = reverse('booking:my_bookings')
        response = self.client.get(url)
        
        self.assertEqual(len(response.context['bookings']), 0)
    
    def test_my_bookings_ordered_by_date(self):
        """Test bookings ordered by tanggal_booking descending"""
        # Create multiple bookings
        booking1 = Booking.objects.create(
            user=self.user,
            slot=self.slot_today,
            tanggal_booking=timezone.now() - timedelta(days=2),
            total_bayar=100000,
            status_pembayaran='PAID'
        )
        
        booking2 = Booking.objects.create(
            user=self.user,
            slot=self.slot_tomorrow,
            tanggal_booking=timezone.now() - timedelta(days=1),
            total_bayar=100000,
            status_pembayaran='PAID'
        )
        
        self.client.force_login(self.user)
        
        url = reverse('booking:my_bookings')
        response = self.client.get(url)
        
        bookings = response.context['bookings']
        # Most recent first
        self.assertEqual(bookings[0].pk, booking2.pk)
        self.assertEqual(bookings[1].pk, booking1.pk)