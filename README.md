# Tugas Kelompok Tahap 1
---

## i. Nama Anggota Kelompok 
- Kenzie Nibras Tradezqi (2406414776)
- Saikhah Ummu Anja Amalia (2406436045)
- Syifa Anabella (2406417922)
- Zibeon Jonriano Wisnumoerti (2406355634)
- Faishal Khoiriansyah Wicaksono (2406436335)

## ii. Deskripsi Aplikasi 
Lapangin, website ini hadir dari frustasi nyata kami sebagai mahasiswa yang aktif dalam melakukan olahraga khususnya olahraga futsal, basket, dan badminton. Kami tahu betul bagaimana sulitnya menyeimbangkan antara jadwal kuliah yang padat dan kebutuhan untuk berolahraga.

**Masalah yang Kami Hadapi dan Ingin Kami Atasi:**
1. Hambatan Jadwal yang Padat
    Sebagai mahasiswa, waktu kami sangat berharga. Kami sering kesulitan menemukan waktu untuk datang langsung ke lokasi lapangan hanya untuk mengecek ketersediaan atau melakukan booking. Waktu yang seharusnya bisa dipakai untuk berolahraga atau belajar jadi terbuang di jalan.

2. Respons Admin yang Lambat
    Ketika mencoba booking melalui kontak telepon atau chat, kami sering dihadapkan pada admin yang tidak fast respon, terutama saat peak hour. Ketidakpastian ini membuat rencana olahraga tim menjadi kacau.

3. Proses Manual yang Tidak Efisien
    Proses booking dan konfirmasi yang masih mengandalkan transfer bank atau pembayaran tunai rentan terhadap kesalahan, seperti double booking, yang sangat merugikan kami sebagai penyewa.

Kami menciptakan aplikasi ini untuk menjadi jembatan digital yang cepat, pasti, dan transparan bagi para pecinta olahraga. Ini adalah solusi anti-ribet yang mengatasi semua isu di atas:

1. Booking Cepat, Anti-Buang Waktu: Dengan aplikasi kami, Anda bisa melihat ketersediaan real-time untuk lapangan futsal, basket, dan badminton tanpa harus menelepon atau datang langsung. Hanya perlu beberapa detik untuk booking di sela-sela jam kuliah Anda.

2. Konfirmasi Instan: Tidak perlu menunggu balasan admin yang lama. Setelah pembayaran digital berhasil, slot lapangan langsung menjadi milik Anda dengan konfirmasi instan di dalam aplikasi.

3. Transparansi Penuh: Pengguna dapat membandingkan harga, fasilitas, dan ulasan dari semua lapangan di satu tempat, memastikan Anda mendapatkan lapangan terbaik tanpa ada hidden cost atau kejutan.

Tujuan utama kami yaitu mengubah pengalaman booking lapangan yang dulunya penuh ketidakpastian menjadi semudah memesan makanan online. Aplikasi ini adalah komitmen kami untuk memastikan bahwa semangat berolahraga Anda tidak lagi terhambat oleh proses booking yang merepotkan.

## iii. Daftar modul yang akan diimplementasikan
1. Modul Autentikasi & Role User
Deskripsi:
    Mengatur login, logout, register, serta role pengguna (Guest, Member, Admin).
Guest = pengunjung tanpa login,
Member = pengguna terdaftar, 
Admin = pemilik lapangan.
Implementasi:
Model: extend User Django (misalnya Profile dengan field role).
Views: login/logout, register.
Templating: form register & login dengan Tailwind.


2. Modul Booking Lapangan
Deskripsi:
    Fitur utama untuk reservasi lapangan olahraga (futsal, basket, badminton). Member bisa booking, admin mengelola jadwal.
Implementasi:
Model: Lapangan, Booking (ForeignKey ke Member & Lapangan ).
Views: tampilkan jadwal, form booking, validasi bentrok jadwal.
Template: kalender/tabel jadwal booking, portal kontak pembayaran.

3. Modul Ulasan & Rating
Deskripsi:
    Member yang sudah booking bisa memberi ulasan & rating lapangan. Guest & Member bisa membaca ulasan.
Implementasi:
Model: Review (isi teks + rating bintang + relasi ke booking).
Views: form tambah ulasan, tampilkan ulasan per lapangan.
Template: card review dengan star rating.
Filter: hanya Member yang sudah booking bisa memberi ulasan.

4. Modul Galeri Lapangan
Deskripsi:
    Admin bisa upload foto-foto lapangan (interior, fasilitas), yang bisa dilihat oleh Guest & Member.
Implementasi:
Model: Galeri (gambar + relasi ke Lapangan).
Views: upload foto (Admin), tampilkan galeri (semua user).
Template: grid galeri responsive dengan Tailwind.
Fitur tambahan: lazy load atau AJAX untuk load foto tanpa reload halaman penuh.

5. Modul Komunitas
Deskripsi:
    Admin bisa membuat komunitas berdasarkan request Member (misalnya Komunitas Futsal Malam Jumat), lalu menambahkan link grup eksternal (WA/Telegram/Discord). Website menampilkan daftar komunitas dalam bentuk card/page.
Implementasi:
Model: Komunitas (nama, deskripsi, lapangan, link grup, dibuat_oleh).
Views: request komunitas (Member), buat komunitas (Admin).
Template: card/page komunitas dengan tombol “Join Group” (direct ke link eksternal).
Filter: Guest hanya bisa melihat daftar komunitas, join hanya setelah login.


6. Modul User Admin and Role Management 
Deskripsi:
    Halaman khusus Admin untuk mengelola booking, ulasan, galeri, dan komunitas.
Implementasi:
Model: memanfaatkan existing models (Booking, Review, Galeri, Komunitas).
Views: dashboard ringkasan (jumlah booking, rating rata-rata, komunitas aktif).
Template: Admin dashboard, card/page komunitas, card/page lapangan, create_community, create_field.
Filter : hanya role Admin yang dapat mengakses page ini

## iv. Sumber initial dataset kategori utama produk
https://drive.google.com/file/d/1eK_QtY82Bna3GwvQcrdlPG-tcmi6Ijmy/view?usp=drive_link


## v. Role atau peran pengguna beserta deskripsinya (karena bisa saja lebih dari satu jenis pengguna yang mengakses aplikasi)
**1. Guest**
Seorang Guest adalah pengguna yang mengunjungi platform tanpa melakukan login. Peran ini didesain untuk menarik minat pengunjung agar mendaftar dengan memberikan gambaran umum tentang apa yang ditawarkan oleh platform.

Akses Fitur & Modul:
- Bisa mengakses halaman Login dan Register untuk membuat akun baru.
- Bisa melihat jadwal ketersediaan lapangan (misalnya, dalam bentuk kalender atau tabel).
- Bisa membaca semua ulasan dan melihat rating yang diberikan oleh member lain untuk setiap lapangan.
- Bisa melihat seluruh galeri foto yang diunggah oleh Admin untuk setiap lapangan.
- Bisa melihat daftar komunitas yang sudah dibuat oleh Admin.

**2. Member**
- Seorang Member adalah pengguna yang telah mendaftar dan login ke dalam platform. Mereka adalah pengguna utama yang akan berinteraksi dengan fitur-fitur inti seperti booking dan ulasan.

Akses Fitur & Modul:
- Bisa melakukan Login dan Logout.
- Bisa mengelola informasi profil dasarnya (misalnya, ganti password).
- Bisa melakukan reservasi atau booking lapangan sesuai jadwal yang tersedia.
- Bisa melihat riwayat booking yang pernah dilakukannya.
- Bisa mengakses portal pembayaran untuk menyelesaikan booking.
- Bisa memberikan ulasan dan rating (dalam bentuk bintang) untuk lapangan yang sudah selesai dibooking.
- Bisa membaca semua ulasan dari member lain.
- Bisa melihat seluruh galeri foto lapangan.
- Bisa melihat daftar komunitas yang ada.
- Bisa bergabung dengan komunitas melalui link eksternal yang disediakan (WA/Telegram/Discord).
- Bisa mengajukan permintaan (request) kepada Admin untuk membuat komunitas baru.

**3. Admin**
Seorang Admin adalah pemilik atau pengelola lapangan yang memiliki kontrol penuh atas konten dan operasional yang terkait dengan lapangannya. Peran ini berfokus pada manajemen dan administrasi.

Akses Fitur & Modul:
- Bisa melakukan Login dan Logout ke akun adminnya.
- Bisa mengelola semua jadwal booking, termasuk melihat, mengonfirmasi, atau membatalkan reservasi dari Member.
- Bisa memblokir jadwal tertentu secara manual jika diperlukan.
- Bisa melihat semua ulasan yang masuk untuk lapangannya.
- Bisa memoderasi ulasan (misalnya, menyembunyikan atau menghapus ulasan yang tidak pantas).
- Bisa mengunggah (upload) foto-foto baru ke galeri lapangannya.
- Bisa menghapus foto dari galeri.
- Bisa menerima dan meninjau permintaan pembuatan komunitas dari para Member.
- Bisa membuat komunitas baru, termasuk menambahkan nama, deskripsi, dan link grup eksternal.
- Bisa mengelola (edit/hapus) komunitas yang sudah ada.

## vi. Tautan deployment PWS dan link design
- Link Deployment PWS : https://zibeon-jonriano-lapangin.pbp.cs.ui.ac.id/
- Link Design Figma : https://www.figma.com/design/tns2TMUBqT8nJTY6pSLh3S/Lapangin?node-id=0-1&t=2XItc6nUPHshY1KH-1
