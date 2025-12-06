# lapangin2/authbooking/urls.py
from . import views
from django.urls import path

app_name = 'authbooking'

urlpatterns = [
    # django
    path('register/', views.register_user, name='register'),
    path('login/', views.login_user, name='login'),
    path('logout/', views.logout_user, name='logout'),

    # flutter
    path('login-flutter/', views.login_flutter, name='login-flutter'),
    path('register-flutter/', views.register_flutter, name='register-flutter'),
    path('logout-flutter/', views.logout_flutter, name='logout-flutter'),
]