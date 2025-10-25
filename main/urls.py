from django.urls import path
from . import views

app_name = 'main' 

urlpatterns = [
    # Path kosong: Ini akan menjadi homepage /
    path('', views.show_landing_page, name='home'),
]