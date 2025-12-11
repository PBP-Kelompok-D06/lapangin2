from django.urls import path
from . import views

app_name = 'gallery'

urlpatterns = [
    path('<int:lap_id>/', views.show_gallery, name='show_gallery'),
    path('api/lapangan/', views.get_lapangan_list, name='api_lapangan_list'),
    path('api/lapangan/<int:lap_id>/', views.get_lapangan_detail, name='api_lapangan_detail'),
    path('proxy-image/', views.proxy_image, name='proxy_image'),

]
