from django.db import models
from django.contrib.auth.models import User

class Community(models.Model):
    CATEGORY_CHOICES = [
        ('futsal', 'Futsal'),
        ('bulutangkis', 'Bulutangkis'),
        ('basket', 'Basket'),
    ]

    # Fields original dari teman Anda
    community_name = models.CharField(max_length=255)
    description = models.TextField()
    location = models.CharField(max_length=255)
    member_count = models.IntegerField(default=0)
    max_member = models.IntegerField()
    contact_person_name = models.CharField(max_length=30)
    sports_type = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='futsal')
    contact_phone = models.CharField(max_length=20)
    community_image = models.ImageField(upload_to='community_images/', null=True, blank=True)
    date_added = models.DateField(auto_now_add=True)
    
    # Fields TAMBAHAN untuk integrasi admin dashboard & forum
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='communities_created')

    def __str__(self):
        return self.community_name
    
    class Meta:
        verbose_name_plural = 'Communities'


class CommunityMember(models.Model):
    """Model untuk tracking member komunitas"""
    community = models.ForeignKey(Community, on_delete=models.CASCADE, related_name='members')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    joined_date = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ('community', 'user')
        verbose_name_plural = 'Community Members'

    def __str__(self):
        return f"{self.user.username} - {self.community.community_name}"


class CommunityPost(models.Model):
    """Model untuk forum post di komunitas"""
    community = models.ForeignKey(Community, on_delete=models.CASCADE, related_name='posts')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()
    image = models.ImageField(upload_to='community_posts/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Community Posts'

    def __str__(self):
        return f"Post by {self.user.username} in {self.community.community_name}"


class PostComment(models.Model):
    """Model untuk komentar pada post"""
    post = models.ForeignKey(CommunityPost, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']
        verbose_name_plural = 'Post Comments'

    def __str__(self):
        return f"Comment by {self.user.username}"


class CommunityRequest(models.Model):
    """Model untuk request komunitas baru dari member"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    
    requester = models.ForeignKey(User, on_delete=models.CASCADE)
    community_name = models.CharField(max_length=200)
    description = models.TextField()
    sports_type = models.CharField(max_length=50)
    location_preference = models.CharField(max_length=200)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    request_date = models.DateTimeField(auto_now_add=True)
    admin_notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-request_date']
        verbose_name_plural = 'Community Requests'

    def __str__(self):
        return f"{self.community_name} - {self.requester.username}"