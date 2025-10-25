document.addEventListener('DOMContentLoaded', () => {
    const toast = document.getElementById('toast-component');
    if (!toast) return;

    const icon = document.getElementById('toast-icon');
    const title = document.getElementById('toast-title');
    const message = document.getElementById('toast-message');

    // Ambil pesan Django (kalau ada)
    const djangoToast = document.querySelector('.django-toast-data');
    if (djangoToast) {
        const type = djangoToast.dataset.type;
        const text = djangoToast.dataset.message;

        // Tentukan style berdasarkan jenis pesan
        let bgColor = '';
        let iconHTML = '';
        let titleText = '';

        switch (type) {
            case 'success':
                bgColor = 'bg-green-100 text-green-800 border-l-4 border-green-500';
                iconHTML = '<i class="fa-solid fa-circle-check"></i>';
                titleText = 'Berhasil!';
                break;
            case 'error':
                bgColor = 'bg-red-100 text-red-800 border-l-4 border-red-500';
                iconHTML = '<i class="fa-solid fa-triangle-exclamation"></i>';
                titleText = 'Gagal!';
                break;
            case 'warning':
                bgColor = 'bg-yellow-100 text-yellow-800 border-l-4 border-yellow-500';
                iconHTML = '<i class="fa-solid fa-circle-exclamation"></i>';
                titleText = 'Peringatan!';
                break;
            default:
                bgColor = 'bg-blue-100 text-blue-800 border-l-4 border-blue-500';
                iconHTML = '<i class="fa-solid fa-info-circle"></i>';
                titleText = 'Info';
        }

        // Terapkan isi dan style
        toast.classList.add(...bgColor.split(' '));
        icon.innerHTML = iconHTML;
        title.textContent = titleText;
        message.textContent = text;

        // Animasi muncul
        toast.classList.remove('opacity-0', 'pointer-events-none', 'translate-y-10');
        toast.classList.add('opacity-100', 'translate-y-0');

        // Auto-hide setelah 4 detik
        setTimeout(() => {
            toast.classList.remove('opacity-100', 'translate-y-0');
            toast.classList.add('opacity-0', 'pointer-events-none', 'translate-y-10');
        }, 4000);
    }
});
