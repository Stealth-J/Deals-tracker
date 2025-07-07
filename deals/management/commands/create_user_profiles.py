from django.core.management.base import BaseCommand
from deals.models import Profile, User

class Command(BaseCommand):
    help = "Creating corresponding profiles for already existing users"

    def handle(self, *args, **options):
        for user in User.objects.all():
            Profile.objects.create(user = user)