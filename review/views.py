import json
from django.http import JsonResponse
from django.shortcuts import render
from .models import Review
from booking.models import Lapangan as Field
from authbooking.models import Profile
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Avg

def review_list(request, field_id):
    field = get_object_or_404(Field, id=field_id)
    
    filter_rating = request.GET.get('filter', 'all')
    
    reviews = Review.objects.filter(field=field)
    
    if filter_rating == 'terbaru':
        reviews = reviews.order_by('-created_at')
    elif filter_rating != 'all':
        try:
            rating_value = int(filter_rating)
            if 1 <= rating_value <= 5:
                reviews = reviews.filter(rating=rating_value).order_by('-created_at')
            else:
                reviews = reviews.order_by('-created_at')
        except ValueError:
            reviews = reviews.order_by('-created_at')
    else:
        reviews = reviews.order_by('-created_at')

    for review in reviews:
        review.is_owner = review.user.user == request.user
        review.id = review.id

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        reviews_data = [
            {
                "id": review.id,
                "user": review.user.user.username,
                "content": review.content,
                "rating": review.rating,
                "created_at": review.created_at.strftime("%d %b %Y %H:%M"),
                "is_owner": review.user.user == request.user
            }
            for review in reviews
        ]
        

        return JsonResponse({"reviews": reviews_data})

    return render(request, 'all_reviews.html', {
        'reviews': reviews,
        'field': field,
        'show_navbar': True
    })

def review_list_in_gallery(request, field_id):
    field = get_object_or_404(Field, id=field_id)
    
    filter_rating = request.GET.get('filter', 'all')
    limit = int(request.GET.get('limit', 4)) 
    
    reviews = Review.objects.filter(field=field)
    
    if filter_rating == 'terbaru':
        reviews = reviews.order_by('-created_at')
    elif filter_rating != 'all':
        try:
            rating_value = int(filter_rating)
            if 1 <= rating_value <= 5:
                reviews = reviews.filter(rating=rating_value).order_by('-created_at')
            else:
                reviews = reviews.order_by('-created_at')
        except ValueError:
            reviews = reviews.order_by('-created_at')
    else:
        reviews = reviews.order_by('-created_at')

    reviews = reviews[:limit] 

    for review in reviews:
        review.is_owner = review.user.user == request.user
        review.id = review.id

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        reviews_data = [
            {
                "id": review.id,
                "user": review.user.user.username,
                "content": review.content,
                "rating": review.rating,
                "created_at": review.created_at.strftime("%d %b %Y %H:%M"),
                "is_owner": review.user.user == request.user
            }
            for review in reviews
        ]
        
        return JsonResponse({"reviews": reviews_data})

    return render(request, 'reviews.html', {
        'reviews': reviews,
        'field': field,
        'show_navbar': False
    })

def review_statistics(request, field_id):
    field = get_object_or_404(Field, id=field_id)
    reviews = Review.objects.filter(field=field)
    
    total_reviews = reviews.count()
    rating_counts = {i: reviews.filter(rating=i).count() for i in range(1, 6)}
    average_rating = reviews.aggregate(Avg('rating'))['rating__avg'] or 0
    
    return JsonResponse({
        "total_reviews": total_reviews,
        "rating_counts": rating_counts,
        "average_rating": average_rating
    })

@csrf_exempt
def review_edit(request, review_id):
    if request.method == "POST" and request.headers.get('x-requested-with') == 'XMLHttpRequest':
        try:
            review_id = int(review_id)
        except ValueError:
            return JsonResponse({"success": False, "error": "ID tidak valid"}, status=400)

        try:
            review = Review.objects.get(id=review_id, user__user=request.user)
        except Review.DoesNotExist:
            return JsonResponse({"success": False, "error": "Review tidak ditemukan"}, status=404)

        try:
            data = json.loads(request.body)
            new_content = data.get('content', '').strip()
            new_rating = data.get('rating')
        except json.JSONDecodeError:
            return JsonResponse({"success": False, "error": "Data tidak valid"}, status=400)

        if not new_content:
            return JsonResponse({"success": False, "error": "Konten tidak boleh kosong"}, status=400)

        if new_rating is not None:
            try:
                new_rating = int(new_rating)
                if 1 <= new_rating <= 5:
                    review.rating = new_rating
                else:
                    return JsonResponse({"success": False, "error": "Rating harus 1-5"}, status=400)
            except ValueError:
                return JsonResponse({"success": False, "error": "Rating tidak valid"}, status=400)

        review.content = new_content
        review.save()

        review.field.update_rating()

        return JsonResponse({
            "success": True,
            "updated": {
                "content": review.content,
                "rating": review.rating,
                "created_at": review.created_at.strftime("%d %b %Y %H:%M"),
            }
        })

    return JsonResponse({"success": False, "error": "Metode tidak valid"}, status=400)

@csrf_exempt
def delete_review(request, review_id):
    if request.method == "POST":
        review = get_object_or_404(Review, id=review_id)
        if review.user.user == request.user:
            field = review.field
            review.delete()
            field.update_rating()
            return JsonResponse({"success": True})
        else:
            return JsonResponse({"success": False, "error": "Tidak memiliki izin."})
    return JsonResponse({"success": False, "error": "Metode tidak valid."})

def add_review(request, field_id):
    if request.method == "POST":
        data = json.loads(request.body)
        content = data.get("content")
        field = Field.objects.get(id=field_id)
        rating = data.get("rating")
        user = request.user
        profile = Profile.objects.get(user=user)
        review = Review.objects.create(
            user=profile,
            field=field,
            content=content,
            rating=rating,
        )
        field.update_rating()

        return JsonResponse({
            "success": True,
            "message": "Review berhasil ditambahkan!",
            "review":{
                "user": user.username,
                "content": review.content,
                "rating": review.rating,
                "created_at": review.created_at,
                "is_owner": True
            }
        })
    return JsonResponse({"success": False, "error": "Invalid method"}, status=405)