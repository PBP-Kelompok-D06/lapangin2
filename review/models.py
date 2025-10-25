from django.db import models
from authbooking.models import Profile
from booking.models import Lapangan

class Review (models.Model):
    user = models.ForeignKey(Profile, on_delete=models.CASCADE)
    field = models.ForeignKey(Lapangan, on_delete=models.CASCADE)
    rating = models.IntegerField()
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Review by {self.user.user.username} for {self.field.nama_lapangan} - Rating: {self.rating}"

# Create your models here.
