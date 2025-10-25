"""
URL configuration for lapangin project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.urls import path
from . import views

app_name = 'community'  # Pastikan konsisten

urlpatterns = [
    # Public views
    path('', views.show_community_page, name='show_community_page'),
    path('<int:pk>/', views.community_detail, name='show_detail_community'),  
    path('<int:pk>/join/', views.join_community, name='join_community'),
    path('<int:pk>/leave/', views.leave_community, name='leave_community'),
    
    # Forum features
    path('<int:pk>/post/create/', views.post_create, name='post_create'),
    path('post/<int:pk>/delete/', views.post_delete, name='post_delete'),
    path('post/<int:pk>/comment/', views.comment_create, name='comment_create'),
    
    # Request komunitas (member)
    path('request/', views.request_community_create, name='request_community_create'),
    path('request/my/', views.my_community_requests, name='my_community_requests'),
    
    # Admin views
    path('admin/list/', views.admin_community_list, name='admin_community_list'),
    path('admin/create/', views.admin_community_create, name='admin_community_create'),
    path('admin/<int:pk>/edit/', views.admin_community_edit, name='admin_community_edit'),
    path('admin/<int:pk>/delete/', views.admin_community_delete, name='admin_community_delete'),
    path('admin/requests/', views.admin_request_list, name='admin_request_list'),
    path('admin/requests/<int:pk>/approve/', views.admin_request_approve, name='admin_request_approve'),
    path('admin/requests/<int:pk>/reject/', views.admin_request_reject, name='admin_request_reject'),
    
    # API endpoints
    path('xml/', views.show_xml, name='show_xml'),
    path('json/', views.show_json, name='show_json'),
    path('xml/<int:id>/', views.show_xml_by_id, name='show_xml_by_id'),
    path('json/<int:id>/', views.show_json_by_id, name='show_json_by_id'),
]