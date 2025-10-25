from django.urls import path
from . import views

app_name = 'gallery'

urlpatterns = [
    path('<int:lap_id>/', views.show_gallery, name='show_gallery'),
]
