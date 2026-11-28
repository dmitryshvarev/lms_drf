from datetime import timedelta

from celery import shared_task
from django.utils import timezone

from users.models import User


@shared_task
def deactivate_inactive_users():
    """Блокирует пользователей, которые не заходили в систему более 30 дней."""
    one_month_ago = timezone.now() - timedelta(days=30)

    # Находим активных пользователей, чей last_login старше 30 дней (и не пустой)
    inactive_users = User.objects.filter(is_active=True, last_login__lt=one_month_ago)

    # Массово обновляем статус
    count = inactive_users.update(is_active=False)
    return f"Заблокировано пользователей: {count}"
