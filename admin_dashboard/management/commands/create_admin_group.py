from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType

class Command(BaseCommand):
    help = 'Create Admin group with appropriate permissions'

    def handle(self, *args, **options):
        # Create Admin group
        admin_group, created = Group.objects.get_or_create(name='Admin')
        
        if created:
            self.stdout.write(self.style.SUCCESS('Admin group created successfully!'))
        else:
            self.stdout.write(self.style.WARNING('Admin group already exists'))
        
        # Add all permissions to Admin group
        permissions = Permission.objects.all()
        admin_group.permissions.set(permissions)
        
        self.stdout.write(self.style.SUCCESS(f'Added {permissions.count()} permissions to Admin group'))