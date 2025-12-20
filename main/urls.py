# lapangin2/main/urls.py
from django.urls import path
from . import views

app_name = 'main' 

urlpatterns = [
    # Path kosong: Ini akan menjadi homepage /
    path('', views.show_landing_page, name='home'),
    path('proxy-image/', views.proxy_image, name='proxy_image'),
    path('api/booking/', views.get_lapangan_list, name='get_booking_list'),
]