from django.conf import settings
from django.db import models


class Course(models.Model):
    name = models.CharField(
        max_length=200, verbose_name="Название", help_text="Укажите название курса"
    )
    image = models.ImageField(
        upload_to="materials/images",
        verbose_name="Превью (изображение)",
        null=True,
        blank=True,
    )
    description = models.TextField(
        verbose_name="Описание курса", help_text="Опишите курс", blank=True, null=True
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="Владелец",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )

    class Meta:
        verbose_name = "Курс"
        verbose_name_plural = "Курсы"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Lesson(models.Model):
    name = models.CharField(
        max_length=200, verbose_name="Название", help_text="Укажите название урока"
    )
    description = models.TextField(
        verbose_name="Описание урока", help_text="Опишите урок", blank=True, null=True
    )
    image = models.ImageField(
        upload_to="materials/images",
        verbose_name="Превью (изображение)",
        blank=True,
        null=True,
    )
    course = models.ForeignKey(
        Course,
        verbose_name="Курс",
        help_text="Введите название курса",
        on_delete=models.SET_NULL,
        related_name="lessons",
        blank=True,
        null=True,
    )
    video_url = models.URLField(
        verbose_name="Ссылка на видео",
        help_text="Введите ссылку на видео",
        blank=True,
        null=True,
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="Владелец урока",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )

    class Meta:
        verbose_name = "Урок"
        verbose_name_plural = "Уроки"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Subscription(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="subscriptions",
        verbose_name="Пользователь",
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="subscriptions",
        verbose_name="Курс",
    )

    class Meta:
        verbose_name = "Подписка"
        verbose_name_plural = "Подписки"
        unique_together = ("user", "course")

    def __str__(self):
        return f"{self.user} - {self.course}"
