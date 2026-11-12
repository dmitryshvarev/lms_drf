from django.urls import path
from rest_framework.routers import DefaultRouter

from users.apps import UsersConfig
from users.views import (PaymentViewSet, UserCreateAPIView, UserDestroyAPIView,
                         UserListAPIView, UserRetrieveAPIView,
                         UserUpdateAPIView)

app_name = UsersConfig.name

router = DefaultRouter()
router.register(r"payments", PaymentViewSet, basename="payments")

urlpatterns = [
    path("users/", UserListAPIView.as_view(), name="users_list"),
    path("users/<int:pk>/", UserRetrieveAPIView.as_view(), name="user_detail"),
    path("users/create/", UserCreateAPIView.as_view(), name="user_create"),
    path("users/<int:pk>/delete/", UserDestroyAPIView.as_view(), name="user_delete"),
    path("users/<int:pk>/update/", UserUpdateAPIView.as_view(), name="user_edit"),
]

urlpatterns += router.urls
