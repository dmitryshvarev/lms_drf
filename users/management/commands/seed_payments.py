from django.core.management.base import BaseCommand

from materials.models import Course, Lesson
from users.models import Payment, User


class Command(BaseCommand):
    help = "Заполняет таблицу Payment тестовыми данными"

    def handle(self, *args, **options):
        # Удаляем старые записи
        Payment.objects.all().delete()

        # Получаем или выбираем тестовые объекты для связей
        user = User.objects.first()
        course = Course.objects.first()
        lesson = Lesson.objects.first()

        if not user:
            self.stdout.write(
                self.style.ERROR("В базе нет ни одного пользователя! Создайте юзера.")
            )
            return

        # Создаем записи
        payments_data = [
            {
                "user": user,
                "course": course,
                "lesson": None,
                "amount": 2500.00,
                "payment_method": Payment.TRANSFER,
            },
            {
                "user": user,
                "course": None,
                "lesson": lesson,
                "amount": 500.00,
                "payment_method": Payment.CASH,
            },
        ]

        created_count = 0
        for item in payments_data:
            Payment.objects.create(**item)
            created_count += 1

        self.stdout.write(
            self.style.SUCCESS(f"Успешно добавлено платежей: {created_count}")
        )
