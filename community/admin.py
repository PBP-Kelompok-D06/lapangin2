from django.contrib import admin
from .models import Community, CommunityMember, CommunityPost, PostComment, CommunityRequest

@admin.register(Community)
class CommunityAdmin(admin.ModelAdmin):
    list_display = ('community_name', 'sports_type', 'location', 'member_count', 'max_member', 'is_active', 'created_by', 'date_added')
    list_filter = ('sports_type', 'is_active', 'date_added')
    search_fields = ('community_name', 'location', 'contact_person_name', 'contact_phone', 'created_by__username')
    readonly_fields = ('date_added', 'member_count')

@admin.register(CommunityMember)
class CommunityMemberAdmin(admin.ModelAdmin):
    list_display = ('user', 'community', 'joined_date', 'is_active')
    list_filter = ('is_active', 'joined_date', 'community')
    search_fields = ('user__username', 'community__community_name')
    raw_id_fields = ('user', 'community')
    date_hierarchy = 'joined_date'

@admin.register(CommunityPost)
class CommunityPostAdmin(admin.ModelAdmin):
    list_display = ('id', 'community', 'user', 'created_at', 'updated_at')
    list_filter = ('community', 'created_at')
    search_fields = ('content', 'user__username', 'community__community_name')
    raw_id_fields = ('user', 'community')
    date_hierarchy = 'created_at'

@admin.register(PostComment)
class PostCommentAdmin(admin.ModelAdmin):
    list_display = ('id', 'post', 'user', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('content', 'user__username', 'post__community__community_name')
    raw_id_fields = ('post', 'user')
    date_hierarchy = 'created_at'

@admin.register(CommunityRequest)
class CommunityRequestAdmin(admin.ModelAdmin):
    list_display = ('community_name', 'requester', 'sports_type', 'status', 'request_date')
    list_filter = ('status', 'sports_type', 'request_date')
    search_fields = ('community_name', 'requester__username', 'location_preference')
    date_hierarchy = 'request_date'
