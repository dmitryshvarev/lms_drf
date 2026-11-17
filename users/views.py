from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.generics import (CreateAPIView, DestroyAPIView,
                                     ListAPIView, RetrieveUpdateAPIView)
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.viewsets import ModelViewSet

from users.models import Payment, User

from .paginators import UserPaginator
from .permissions import IsOwnerOrReadOnly
from .serializers import (PaymentSerializer, PrivateUserSerializer,
                          PublicUserSerializer)


class UserRetrieveUpdateAPIView(RetrieveUpdateAPIView):
    """
    Представление для просмотра любого профиля (GET)
    и редактирования только своего (PUT, PATCH).
    """

    queryset = User.objects.all()
    permission_classes = [IsAuthenticated, IsOwnerOrReadOnly]

    def get_serializer_class(self):
        if getattr(self, "swagger_fake_view", False):
            return PrivateUserSerializer

        user_id = self.kwargs.get("pk")
        if str(self.request.user.id) == str(user_id):
            return PrivateUserSerializer

        return PublicUserSerializer


class UserListAPIView(ListAPIView):
    """Список всех пользователей только с публичной информацией."""

    queryset = User.objects.all()
    permission_classes = [IsAuthenticated]
    serializer_class = PublicUserSerializer
    pagination_class = UserPaginator


class UserCreateAPIView(CreateAPIView):
    queryset = User.objects.all()
    serializer_class = PrivateUserSerializer
    permission_classes = (AllowAny,)


class UserDestroyAPIView(DestroyAPIView):
    """Удаление профиля. Доступно только владельцу аккаунта."""

    queryset = User.objects.all()
    permission_classes = [IsAuthenticated, IsOwnerOrReadOnly]


class PaymentViewSet(ModelViewSet):
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer

    filter_backends = [DjangoFilterBackend, OrderingFilter, SearchFilter]

    filterset_fields = ("course", "lesson", "payment_method")
    ordering_fields = ("date",)
    search_fields = ("payment_method", "amount", "user__email")
