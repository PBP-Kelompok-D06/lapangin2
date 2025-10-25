from django.urls import path
from .views import review_list, add_review, delete_review, review_edit, review_statistics,review_list_in_gallery
app_name = 'review'

urlpatterns = [
    path('<int:field_id>/', review_list, name='review_list'),
    path('<int:field_id>/add/', add_review, name='add_review'),
    path('delete/<int:review_id>/', delete_review, name='delete_review'),
    path('edit/<int:review_id>/', review_edit, name='review_edit'),
    path('<int:field_id>/statistics/', review_statistics, name='review_statistics'),
    path('gallery/<int:field_id>/', review_list_in_gallery, name='review_list_in_gallery'),

]