from django.db.models.signals import post_save
from django.dispatch import receiver
from datetime import date, time, timedelta
from .models import Lapangan, SlotTersedia


@receiver(post_save, sender=Lapangan)
def create_booking_slots(sender, instance, created, **kwargs):
    """
    Signal untuk otomatis membuat booking sessions (slots) 
    ketika lapangan baru dibuat
    """
    if created:  # Hanya jalankan saat lapangan BARU dibuat, bukan di-update
        
        # Definisikan 14 slot waktu per jam dari 08:00 sampai 22:00
        time_slots = []
        for hour in range(8, 22): 
            start_time = time(hour, 0)
            end_time = time(hour + 1, 0)
            time_slots.append((start_time, end_time))
        
        start_date = date.today()
        DAYS_TO_CREATE = 80  # Buat slot untuk 80 hari ke depan
        
        slot_count = 0
        for day_offset in range(DAYS_TO_CREATE):
            tgl = start_date + timedelta(days=day_offset)
            
            for start_time, end_time in time_slots:
                SlotTersedia.objects.get_or_create(
                    lapangan=instance,
                    tanggal=tgl,
                    jam_mulai=start_time,
                    defaults={
                        'jam_akhir': end_time,
                        'is_available': True,
                    }
                )
                slot_count += 1
        
        print(f"✅ Auto-generated {slot_count} booking slots for {instance.nama_lapangan}")