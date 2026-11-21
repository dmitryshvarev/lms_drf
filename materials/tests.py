from django.contrib.auth.models import Group
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from materials.models import Course, Lesson, Subscription
from users.models import User


class BaseAPITestCase(APITestCase):
    """Базовый класс с фикстурами пользователей, ролей и тестовых объектов."""

    def setUp(self):
        # Группа модераторов
        self.moder_group, _ = Group.objects.get_or_create(name="moders")

        # Пользователи: владелец, модератор и обычный пользователь
        self.owner = User.objects.create(email="owner@test.com")
        self.moder = User.objects.create(email="moder@test.com")
        self.moder.groups.add(self.moder_group)
        self.other_user = User.objects.create(email="other@test.com")

        # Базовый курс и урок владельца
        self.course = Course.objects.create(
            name="Базовый курс",
            description="Описание с разрешенной ссылкой https://youtube.com",
            owner=self.owner,
        )
        self.lesson = Lesson.objects.create(
            name="Базовый урок",
            description="Описание базового урока",
            course=self.course,
            owner=self.owner,
            video_url="https://youtube.com",
        )

        # Аутентификация владельца по умолчанию
        self.client.force_authenticate(user=self.owner)


class CourseTestCase(BaseAPITestCase):
    """Тесты для CourseViewSet (CRUD, права доступа, валидация и вычисляемые поля)."""

    def setUp(self):
        super().setUp()
        self.list_url = reverse("materials:courses-list")
        self.detail_url = reverse("materials:courses-detail", args=[self.course.pk])

    def test_course_create_by_user(self):
        """Обычный авторизованный пользователь может создать курс и становится его owner."""
        self.client.force_authenticate(user=self.other_user)
        data = {
            "name": "Новый курс",
            "description": "Полезные материалы: https://youtu.be",
        }
        response = self.client.post(self.list_url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Course.objects.count(), 2)
        created_course = Course.objects.get(pk=response.data["id"])
        self.assertEqual(created_course.owner, self.other_user)

    def test_course_create_invalid_description_link(self):
        """YouTubeOnlyValidator отклоняет сторонние ссылки в описании курса."""
        self.client.force_authenticate(user=self.other_user)
        data = {
            "name": "Курс со сторонней ссылкой",
            "description": "Смотрите видео на https://rutube.ru",
        }
        response = self.client.post(self.list_url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Course.objects.count(), 1)

    def test_course_create_by_moder_forbidden(self):
        """Модератор не может создавать курсы (~IsModer)."""
        self.client.force_authenticate(user=self.moder)
        data = {"name": "Курс модератора", "description": "Описание"}
        response = self.client.post(self.list_url, data)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_course_list_and_custom_fields(self):
        """Проверка списка курсов, пагинации и полей lessons_count / is_subscribed."""
        self.client.force_authenticate(user=self.other_user)
        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get("results", response.data)
        self.assertEqual(len(results), 1)

        course_data = results[0]
        self.assertEqual(course_data["name"], self.course.name)
        self.assertEqual(course_data["lessons_count"], 1)
        self.assertFalse(course_data["is_subscribed"])

        # Оформляем подписку и проверяем изменение is_subscribed
        Subscription.objects.create(user=self.other_user, course=self.course)
        response_subscribed = self.client.get(self.list_url)
        results_subscribed = response_subscribed.data.get(
            "results", response_subscribed.data
        )
        self.assertTrue(results_subscribed[0]["is_subscribed"])

    def test_course_retrieve_permissions(self):
        """Детальный просмотр курса доступен владельцу и модератору, закрыт чужим."""
        self.client.force_authenticate(user=self.owner)
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["lessons_count"], 1)
        self.assertEqual(len(response.data["lessons"]), 1)

        self.client.force_authenticate(user=self.moder)
        self.assertEqual(
            self.client.get(self.detail_url).status_code, status.HTTP_200_OK
        )

        self.client.force_authenticate(user=self.other_user)
        self.assertEqual(
            self.client.get(self.detail_url).status_code, status.HTTP_403_FORBIDDEN
        )

    def test_course_update_permissions(self):
        """Обновление курса доступно владельцу и модератору, запрещено чужим."""
        self.client.force_authenticate(user=self.owner)
        response = self.client.patch(self.detail_url, {"name": "Обновлено владельцем"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.client.force_authenticate(user=self.moder)
        response = self.client.patch(self.detail_url, {"name": "Обновлено модератором"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.client.force_authenticate(user=self.other_user)
        response = self.client.patch(self.detail_url, {"name": "Чужая правка"})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_course_delete_permissions(self):
        """Удаление курса доступно только владельцу (~IsModer & IsOwner)."""
        self.client.force_authenticate(user=self.moder)
        self.assertEqual(
            self.client.delete(self.detail_url).status_code, status.HTTP_403_FORBIDDEN
        )

        self.client.force_authenticate(user=self.other_user)
        self.assertEqual(
            self.client.delete(self.detail_url).status_code, status.HTTP_403_FORBIDDEN
        )

        self.client.force_authenticate(user=self.owner)
        self.assertEqual(
            self.client.delete(self.detail_url).status_code, status.HTTP_204_NO_CONTENT
        )
        self.assertEqual(Course.objects.count(), 0)


class LessonTestCase(BaseAPITestCase):
    """Тесты для эндпоинтов уроков (Lesson*APIView) и валидатора YouTubeOnlyValidator."""

    def setUp(self):
        super().setUp()
        self.create_url = reverse("materials:lesson_create")
        self.list_url = reverse("materials:lessons_list")
        self.retrieve_url = reverse("materials:lesson_detail", args=[self.lesson.pk])
        self.update_url = reverse("materials:lesson_edit", args=[self.lesson.pk])
        self.delete_url = reverse("materials:lesson_delete", args=[self.lesson.pk])

    def test_lesson_create(self):
        """Создание урока пользователем и запрет для модератора."""
        data = {
            "name": "Новый урок",
            "description": "Описание нового урока",
            "course": self.course.pk,
            "video_url": "https://youtube.com",
        }

        # Модератор получает 403
        self.client.force_authenticate(user=self.moder)
        self.assertEqual(
            self.client.post(self.create_url, data).status_code,
            status.HTTP_403_FORBIDDEN,
        )

        # Обычный пользователь создает урок
        self.client.force_authenticate(user=self.owner)
        response = self.client.post(self.create_url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Lesson.objects.count(), 2)
        self.assertEqual(Lesson.objects.get(pk=response.data["id"]).owner, self.owner)

    def test_lesson_create_invalid_links(self):
        """Проверка YouTubeOnlyValidator для video_url и description."""
        self.client.force_authenticate(user=self.owner)

        # Невалидный video_url
        bad_video_data = {
            "name": "Урок со сторонним видео",
            "description": "Обычное описание",
            "course": self.course.pk,
            "video_url": "https://vimeo.com",
        }
        response_video = self.client.post(self.create_url, bad_video_data)
        self.assertEqual(response_video.status_code, status.HTTP_400_BAD_REQUEST)

        # Невалидная ссылка в description
        bad_desc_data = {
            "name": "Урок со сторонней ссылкой в описании",
            "description": "Доп. материалы на https://example.com",
            "course": self.course.pk,
            "video_url": "https://youtube.com",
        }
        response_desc = self.client.post(self.create_url, bad_desc_data)
        self.assertEqual(response_desc.status_code, status.HTTP_400_BAD_REQUEST)

    def test_lesson_list(self):
        """Получение списка уроков с пагинацией."""
        self.client.force_authenticate(user=self.other_user)
        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get("results", response.data)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["name"], self.lesson.name)

    def test_lesson_retrieve_permissions(self):
        """Просмотр урока доступен владельцу и модератору."""
        self.client.force_authenticate(user=self.other_user)
        self.assertEqual(
            self.client.get(self.retrieve_url).status_code, status.HTTP_403_FORBIDDEN
        )

        self.client.force_authenticate(user=self.moder)
        self.assertEqual(
            self.client.get(self.retrieve_url).status_code, status.HTTP_200_OK
        )

        self.client.force_authenticate(user=self.owner)
