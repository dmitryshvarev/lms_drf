from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser
from django.db import models

from materials.models import Course, Lesson


class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email обязателен")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    username = None

    email = models.EmailField(
        max_length=150, unique=True, verbose_name="Email", help_text="Укажите почту"
    )
    phone = models.CharField(
        max_length=35,
        verbose_name="Телефон",
        help_text="Укажите телефон",
        blank=True,
        null=True,
    )
    city = models.CharField(
        max_length=50,
        verbose_name="Город",
        help_text="Укажите город",
        blank=True,
        null=True,
    )
    avatar = models.ImageField(
        upload_to="users/avatars",
        verbose_name="Аватар",
        help_text="Загрузите аватар",
        blank=True,
        null=True,
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    class Meta:
        verbose_name = "Пользователь"
        verbose_name_plural = "Пользователи"

    def __str__(self):
        return f"{self.email}"

    objects = CustomUserManager()


class Payment(models.Model):
    CASH = "cash"
    TRANSFER = "transfer"

    PAYMENT_METHOD_CHOICES = [
        (CASH, "Наличные"),
        (TRANSFER, "Перевод на счет"),
    ]

    user = models.ForeignKey(
        User,
        verbose_name="Пользователь",
        on_delete=models.SET_NULL,
        related_name="payments",
        blank=True,
        null=True,
    )
    date = models.DateTimeField(
        verbose_name="Дата оплаты",
        auto_now_add=True,
    )
    course = models.ForeignKey(
        Course,
        verbose_name="Курс",
        help_text="Введите название курса",
        on_delete=models.SET_NULL,
        related_name="course_payments",
        blank=True,
        null=True,
    )
    lesson = models.ForeignKey(
        Lesson,
        verbose_name="Урок",
        help_text="Введите название урока",
        on_delete=models.SET_NULL,
        related_name="lesson_payments",
        blank=True,
        null=True,
    )
    amount = models.PositiveIntegerField(
        verbose_name="Сумма оплаты",
        blank=True,
        null=True,
    )
    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES,
        default=TRANSFER,
        verbose_name="Способ оплаты",
    )
    session_id = models.CharField(
        max_length=255,
        verbose_name="ID сессии Stripe",
        blank=True,
        null=True,
    )
    payment_link = models.URLField(
        max_length=1000,
        verbose_name="Ссылка на оплату",
        blank=True,
        null=True,
    )
    status = models.CharField(
        max_length=50, default="unpaid", verbose_name="Статус платежа"
    )

    def __str__(self):
        item = self.course if self.course else self.lesson
        return f"{self.user} — {item} ({self.amount})"

    class Meta:
        verbose_name = "Платеж"
        verbose_name_plural = "Платежи"
        ordering = ["-date"]
