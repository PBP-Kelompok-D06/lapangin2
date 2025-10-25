'''
File ini digunakan untuk nge-assign pemilik lapangan yang ada di dataset csv (data_lapangan.csv)
Langkah-langkah sebelum menjalankan command ini:
1. Pastikan sudah melakukan load dataset lapangan (sesuai instruksi modul kalian).
2. Pastikan sudah membuat akun PEMILIK dengan username 'juragan01' dan password 'juragan123'.
3. (Opsional tapi disarankan) Assign nomor rekening dan nomor WhatsApp untuk user 'juragan01' lewat Django shell:

   Jalankan di terminal:
   >>> python manage.py shell

   Lalu di shell Python:
   >>> from django.contrib.auth.models import User
   >>> user = User.objects.get(username='juragan01')
   >>> profile = user.profile
   >>> profile.nomor_rekening = "1234567890 - a.n Juragan Lapangin"
   >>> profile.nomor_whatsapp = "081234567890"
   >>> profile.save()
   >>> print(profile.nomor_rekening, profile.nomor_whatsapp)

   (Kalau sudah tampil dengan benar, berarti berhasil disimpan.)

4. Jalankan command ini di terminal:
   python manage.py assign_single_owner 
'''


from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from booking.models import Lapangan
from authbooking.models import Profile 
from django.db import transaction

class Command(BaseCommand):
    help = 'Mengassign SEMUA Lapangan yang belum terassign ke satu akun PEMILIK: pemilik01.'

    def handle(self, *args, **options):
        TARGET_USERNAME = 'juragan01' # <-- ini username dari akun yang udah dibuat sebelumnya dengan role PEMILIK
        
        # 1. Ambil Akun User dan Profile Target
        try:
            user_owner = User.objects.get(username=TARGET_USERNAME)
            profile_owner = user_owner.profile
        except User.DoesNotExist:
            raise CommandError(f"Akun '{TARGET_USERNAME}' tidak ditemukan. Mohon buat akun tersebut terlebih dahulu (Role PEMILIK).")
        except Profile.DoesNotExist:
             raise CommandError(f"Profile tidak ditemukan untuk user '{TARGET_USERNAME}'. Pastikan akun dibuat melalui Register yang benar.")

        # 2. Ambil Semua Lapangan yang Belum Memiliki Pemilik
        all_lapangan = Lapangan.objects.filter(pengelola__isnull=True).order_by('pk')
        count_to_assign = all_lapangan.count()

        if count_to_assign == 0:
             self.stdout.write(self.style.SUCCESS("Semua Lapangan sudah memiliki pemilik. Command selesai."))
             return

        self.stdout.write(self.style.NOTICE(
            f"Memproses {count_to_assign} Lapangan unassigned ke '{TARGET_USERNAME}'..."
        ))

        # 3. Melakukan Assignment Massal (Bulk Update)
        
        # Iterasi dan set field pengelola untuk setiap objek
        for lapangan in all_lapangan:
            lapangan.pengelola = profile_owner
        
        # Simpan semua perubahan Lapangan ke database dalam satu operasi cepat
        # (Menggunakan 'pengelola' karena itu nama field Foreign Key)
        Lapangan.objects.bulk_update(all_lapangan, ['pengelola'])


        self.stdout.write(self.style.SUCCESS(
            f"✅ Berhasil mengassign {count_to_assign} Lapangan ke {TARGET_USERNAME} (PEMILIK)."
        ))