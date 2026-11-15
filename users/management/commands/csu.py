import os

from django.core.management.base import BaseCommand

from users.models import User


class Command(BaseCommand):
    help = "Создает суперпользователя"

    def handle(self, *args, **options):
        user = User.objects.create_superuser(email=os.getenv("ADMIN_EMAIL"))
        user.set_password(os.getenv("ADMIN_PASSWORD"))
        user.save()
