from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail

from materials.models import Course, Subscription


@shared_task
def send_course_update_email(course_id):
    """Отправляет уведомление об обновлении всем подписанным на курс пользователям."""
    try:
        course = Course.objects.get(pk=course_id)
    except Course.DoesNotExist:
        return

    # Получаем всех активных подписчиков курса
    subscriptions = Subscription.objects.filter(course=course).select_related("user")
    recipient_list = [sub.user.email for sub in subscriptions if sub.user.email]

    if recipient_list:
        send_mail(
            subject=f"Обновление курса «{course.name}»",
            message=f"Материалы курса «{course.name}» были обновлены. Зайдите на платформу, чтобы ознакомиться!",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=recipient_list,
            fail_silently=False,
        )
