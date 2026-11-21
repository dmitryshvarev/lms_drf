from decimal import Decimal

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from materials.models import Course, Lesson
from users.models import Payment, User


class BaseUsersAPITestCase(APITestCase):
    """Базовый класс с фикстурами пользователей и платежей."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="user@test.com",
            password="testpass123",
            phone="+79991112233",
            city="Москва",
        )
        self.other_user = User.objects.create_user(
            email="other@test.com",
            password="testpass123",
            phone="+79994445566",
            city="Санкт-Петербург",
        )

        self.course = Course.objects.create(name="Курс Python", owner=self.user)
        self.lesson = Lesson.objects.create(
            name="Урок 1", course=self.course, owner=self.user
        )

        self.payment_cash = Payment.objects.create(
            user=self.user,
            course=self.course,
            amount=Decimal("15000.00"),
            payment_method=Payment.CASH,
        )
        self.payment_transfer = Payment.objects.create(
            user=self.other_user,
            lesson=self.lesson,
            amount=Decimal("3000.00"),
            payment_method=Payment.TRANSFER,
        )

        # Аутентификация основного пользователя по умолчанию
        self.client.force_authenticate(user=self.user)


class UserEndpointsTestCase(BaseUsersAPITestCase):
    """Тесты для регистрации, JWT-авторизации, просмотра, обновления и удаления пользователей."""

    def setUp(self):
        super().setUp()
        self.login_url = reverse("users:login")
        self.refresh_url = reverse("users:token_refresh")
        self.register_url = reverse("users:register")
        self.list_url = reverse("users:users_list")
        self.own_detail_url = reverse("users:user_detail", args=[self.user.pk])
        self.other_detail_url = reverse("users:user_detail", args=[self.other_user.pk])
        self.own_edit_url = reverse("users:user_edit", args=[self.user.pk])
        self.other_edit_url = reverse("users:user_edit", args=[self.other_user.pk])
        self.own_delete_url = reverse("users:user_delete", args=[self.user.pk])
        self.other_delete_url = reverse("users:user_delete", args=[self.other_user.pk])

    def test_jwt_login_and_refresh(self):
        """Проверка получения и обновления JWT-токенов."""
        self.client.force_authenticate(user=None)
        login_response = self.client.post(
            self.login_url,
            {"email": "user@test.com", "password": "testpass123"},
        )
        self.assertEqual(login_response.status_code, status.HTTP_200_OK)
        self.assertIn("access", login_response.data)
        self.assertIn("refresh", login_response.data)

        refresh_response = self.client.post(
            self.refresh_url,
            {"refresh": login_response.data["refresh"]},
        )
        self.assertEqual(refresh_response.status_code, status.HTTP_200_OK)
        self.assertIn("access", refresh_response.data)

    def test_user_create_allow_any(self):
        """Регистрация нового пользователя доступна без авторизации (AllowAny)."""
        self.client.force_authenticate(user=None)
        data = {
            "email": "newuser@test.com",
            "password": "StrongPassword123!",
            "phone": "+79990001122",
            "city": "Екатеринбург",
        }
        response = self.client.post(self.register_url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(User.objects.count(), 3)

    def test_user_list_authenticated(self):
        """Авторизованный пользователь получает список пользователей с пагинацией."""
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        results = response.data.get("results", response.data)
        self.assertEqual(len(results), 2)
        self.assertNotIn("password", results[0])

    def test_user_list_unauthenticated_forbidden(self):
        """Неавторизованный пользователь не может просматривать список."""
        self.client.force_authenticate(user=None)
        response = self.client.get(self.list_url)
        self.assertIn(
            response.status_code,
            [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN],
        )

    def test_user_retrieve_private_vs_public_serializer(self):
        """Свой профиль возвращается через PrivateUserSerializer, чужой — через PublicUserSerializer."""
        own_response = self.client.get(self.own_detail_url)
        self.assertEqual(own_response.status_code, status.HTTP_200_OK)
        self.assertEqual(own_response.data["email"], self.user.email)

        other_response = self.client.get(self.other_detail_url)
        self.assertEqual(other_response.status_code, status.HTTP_200_OK)
        self.assertEqual(other_response.data["email"], self.other_user.email)
        self.assertNotIn("password", other_response.data)

    def test_user_update_permissions(self):
        """Редактирование доступно только владельцу аккаунта (через user_detail и user_edit)."""
        response_own = self.client.patch(self.own_edit_url, {"city": "Казань"})
        self.assertEqual(response_own.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.city, "Казань")

        response_other = self.client.patch(self.other_edit_url, {"city": "Сочи"})
        self.assertEqual(response_other.status_code, status.HTTP_403_FORBIDDEN)

    def test_user_delete_permissions(self):
        """Удаление профиля доступно только его владельцу."""
        response_other = self.client.delete(self.other_delete_url)
        self.assertEqual(response_other.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(User.objects.count(), 2)

        response_own = self.client.delete(self.own_delete_url)
        self.assertEqual(response_own.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(User.objects.count(), 1)


class PaymentViewSetTestCase(BaseUsersAPITestCase):
    """Тесты для PaymentViewSet (CRUD, фильтрация, поиск и сортировка)."""

    def setUp(self):
        super().setUp()
        self.list_url = reverse("users:payments-list")
        self.detail_url = reverse("users:payments-detail", args=[self.payment_cash.pk])

    @staticmethod
    def _get_results(data):
        """Универсальное извлечение списка элементов (с пагинацией или без)."""
        return data.get("results", data) if isinstance(data, dict) else data

    def test_payment_list(self):
        """Получение списка всех платежей."""
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = self._get_results(response.data)
        self.assertEqual(len(results), 2)

    def test_payment_filter_by_method_and_course(self):
        """Проверка DjangoFilterBackend по полям payment_method, course и lesson."""
        response_method = self.client.get(
            self.list_url, {"payment_method": Payment.CASH}
        )
        self.assertEqual(response_method.status_code, status.HTTP_200_OK)
        results_method = self._get_results(response_method.data)
        self.assertEqual(len(results_method), 1)
        self.assertEqual(results_method[0]["id"], self.payment_cash.pk)

        response_course = self.client.get(self.list_url, {"course": self.course.pk})
        results_course = self._get_results(response_course.data)
        self.assertEqual(len(results_course), 1)
        self.assertEqual(results_course[0]["id"], self.payment_cash.pk)

        response_lesson = self.client.get(self.list_url, {"lesson": self.lesson.pk})
        results_lesson = self._get_results(response_lesson.data)
        self.assertEqual(len(results_lesson), 1)
        self.assertEqual(results_lesson[0]["id"], self.payment_transfer.pk)

    def test_payment_search(self):
        """Проверка SearchFilter по user__email и payment_method."""
        response = self.client.get(self.list_url, {"search": "other@test.com"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = self._get_results(response.data)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["id"], self.payment_transfer.pk)

    def test_payment_ordering(self):
        """Проверка OrderingFilter по дате платежа (-date и date)."""
        response_desc = self.client.get(self.list_url, {"ordering": "-date"})
        self.assertEqual(response_desc.status_code, status.HTTP_200_OK)
        results_desc = self._get_results(response_desc.data)
        self.assertEqual(results_desc[0]["id"], self.payment_transfer.pk)

        response_asc = self.client.get(self.list_url, {"ordering": "date"})
        self.assertEqual(response_asc.status_code, status.HTTP_200_OK)
        results_asc = self._get_results(response_asc.data)
        self.assertEqual(results_asc[0]["id"], self.payment_cash.pk)

    def test_payment_create_and_retrieve(self):
        """Создание и детальный просмотр платежа."""
        data = {
            "user": self.user.pk,
            "course": self.course.pk,
            "amount": "5000.00",
            "payment_method": Payment.TRANSFER,
        }
        create_response = self.client.post(self.list_url, data)
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Payment.objects.count(), 3)

        retrieve_response = self.client.get(self.detail_url)
        self.assertEqual(retrieve_response.status_code, status.HTTP_200_OK)
