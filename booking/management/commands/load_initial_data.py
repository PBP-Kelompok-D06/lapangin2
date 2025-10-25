'''
File ini digunakan untuk load initial dataset yang 100 data lapangan,
kode ini akan berinteraksi dengan booking/models.py yaitu model Lapangan,
1. Pastiin kalian pull branch feat/booking, kalo kalian bisa buka kode ini di vscode kalian harusnya kalian udh ngelakuin pull dari branch feat/booking
2. load data set dengan jalanin perintah ini di cmd : python manage.py load_initial_data
'''

import csv
import os
import io
from datetime import date, time, timedelta
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from booking.models import Lapangan, SlotTersedia

class Command(BaseCommand):
    help = 'Memuat data Lapangan dan SlotTersedia awal dari CSV.'

    def handle(self, *args, **options):
        # Path ke lapangin/data/data_lapangan.csv
        csv_file_path = os.path.join(settings.BASE_DIR, 'data', 'data_lapangan.csv')

        if not os.path.exists(csv_file_path):
            raise CommandError(f'File CSV tidak ditemukan di: {csv_file_path}')

        self.stdout.write(self.style.NOTICE('Memulai pembuatan data lapangan...'))

        try:
            with open(csv_file_path, 'r', encoding='utf-8') as file:
                content = file.read()
                
                # Pembersihan karakter bermasalah di beberapa baris CSV (TIDAK MENGHAPUS SPASI & KOMA DI TENGAH)
                content = content.replace('”', '"') 
                content = content.replace(',"', ',"')
                
                # Kita TIDAK menggunakan content.replace(', ', ',') agar nama lapangan tetap utuh!
                
                # Menggunakan csv.reader default untuk memastikan parsing yang benar
                # Quoting=csv.QUOTE_MINIMAL membantu menjaga string berquote
                csv_reader = csv.DictReader(io.StringIO(content))
                
                lapangan_count = 0
                slot_count = 0
                
                # Definisikan 14 slot waktu per jam dari 08:00 sampai 22:00
                time_slots = []
                for hour in range(8, 22): 
                    start_time = time(hour, 0)
                    end_time = time(hour + 1, 0)
                    time_slots.append((start_time, end_time))
                    
                start_date = date.today()

                # Tentukan rentang 80 hari untuk diisi data (perkiraan waktu terlama untuk akses web ini)
                DAYS_TO_CREATE = 80

                # Mendefinisikan fungsi safe_int dan safe_float di luar loop (Best Practice)
                def safe_int(val):
                    try:
                        return int(val.strip())
                    except ValueError:
                        return 0

                def safe_float(val):
                    try:
                        return float(val.strip())
                    except ValueError:
                        return 0.0

                for row in csv_reader:
                    
                    try:
                        # 1. Membersihkan dan Mengambil Nilai DENGAN .strip()
                        original_nama = row['nama_lapangan'].strip() 
                        nama_lapangan_val = original_nama # Nama awal untuk get_or_create
                        jenis_olahraga_val = row['jenis_olahraga'].strip()
                        lokasi_val = row['lokasi'].strip()
                        fasilitas_val = row['fasilitas'].strip().strip('"') 
                        
                        # Konversi Numerik (Memanggil fungsi safe_float/int)
                        harga_per_jam_num = safe_int(row['harga_per_jam'])
                        rating_num = safe_float(row['rating'])
                        jumlah_ulasan_num = safe_int(row['jumlah_ulasan'])

                    except KeyError as e:
                         raise CommandError(f'Kolom {e} hilang di CSV. Pastikan header CSV benar.')
                    except Exception as e:
                         # Tangani error konversi dengan pesan yang lebih informatif
                         raise CommandError(f"Gagal memproses baris untuk lapangan '{row.get('nama_lapangan', 'N/A')}'. Error: {e}")

                    
                    # --- FIX UNTUK MEMAKSA 100 LAPANGAN UNIK DENGAN MENGGUNAKAN ID CSV ---
                    # Kita menggunakan ID dari CSV untuk memastikan Lapangan dibuat unik 
                    # Jika nama Lapangan sudah terpakai
                    
                    # Coba cari Lapangan berdasarkan nama awal
                    lapangan, created = Lapangan.objects.get_or_create(
                        nama_lapangan=nama_lapangan_val, 
                        defaults={
                            'jenis_olahraga': jenis_olahraga_val,
                            'harga_per_jam': harga_per_jam_num, 
                            'lokasi': lokasi_val,
                            'fasilitas': fasilitas_val,
                            'rating': rating_num,
                            'jumlah_ulasan': jumlah_ulasan_num,
                        }
                    )
                    
                    if not created:
                        # Jika Lapangan tidak dibuat (yaitu, ditemukan yang sudah ada/duplikat),
                        # Kita coba ubah namanya dengan menambahkan ID unik dari CSV (asumsi kolom 'id' ada)
                        try:
                            csv_id = row['id'].strip()
                            new_unique_name = f"{original_nama} (ID {csv_id})"
                            
                            lapangan, created = Lapangan.objects.get_or_create(
                                nama_lapangan=new_unique_name, 
                                defaults={
                                    'jenis_olahraga': jenis_olahraga_val,
                                    'harga_per_jam': harga_per_jam_num, 
                                    'lokasi': lokasi_val,
                                    'fasilitas': fasilitas_val,
                                    'rating': rating_num,
                                    'jumlah_ulasan': jumlah_ulasan_num,
                                }
                            )
                            if created:
                                # Jika Lapangan berhasil dibuat dengan nama baru, kita hitung sebagai Lapangan baru
                                lapangan_count += 1
                                self.stdout.write(self.style.WARNING(f"Nama '{original_nama}' diubah menjadi '{new_unique_name}' untuk menghindari duplikasi."))
                            
                        except KeyError:
                            self.stdout.write(self.style.ERROR(f"Duplikasi Lapangan ditemukan ('{original_nama}'), tetapi kolom 'id' CSV tidak ditemukan untuk membuat nama unik."))
                    else:
                        lapangan_count += 1
                    
                    # 3. Buat Slot Tersedia (14 slot X 7 hari)
                        for day_offset in range(DAYS_TO_CREATE): # <-- LOOP BARU: Mengulang untuk setiap hari
                            tgl = start_date + timedelta(days=day_offset) # <-- MENGHITUNG TANGGAL MASA DEPAN
                            
                            for start_time, end_time in time_slots: # <-- Mengulang 14 slot per hari
                                
                                SlotTersedia.objects.get_or_create(
                                    lapangan=lapangan,
                                    tanggal=tgl,
                                    jam_mulai=start_time,
                                    defaults={
                                        'jam_akhir': end_time,
                                        'is_available': True,
                                    }
                                )
                                slot_count += 1

                self.stdout.write(self.style.SUCCESS(
                    f'Berhasil membuat {lapangan_count} Lapangan unik.'
                ))
                self.stdout.write(self.style.SUCCESS(
                    f'Berhasil membuat total {slot_count} SlotTersedia (Initial Dataset > 100)!'
                ))

        except Exception as e:
            # Catch all exception untuk error yang tidak terduga
            raise CommandError(f'Gagal memproses data secara keseluruhan. Error: {e}')
