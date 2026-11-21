from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.generics import (CreateAPIView, DestroyAPIView,
                                     ListAPIView, RetrieveUpdateAPIView)
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from users.models import Payment, User

from .paginators import UserPaginator
from .permissions import IsOwnerOrReadOnly
from .serializers import (PaymentSerializer, PrivateUserSerializer,
                          PublicUserSerializer)
from .services import (create_stripe_price, create_stripe_product,
                       create_stripe_session, retrieve_stripe_session)


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
    permission_classes = [IsAuthenticated]

    filter_backends = [DjangoFilterBackend, OrderingFilter, SearchFilter]

    filterset_fields = ("course", "lesson", "payment_method")
    ordering_fields = ("date",)
    search_fields = ("payment_method", "amount", "user__email")

    def perform_create(self, serializer):
        payment = serializer.save(user=self.request.user)

        # Получаем связанный продукт (курс или урок)
        item = payment.course if payment.course else payment.lesson
        payment.amount = item.price

        # 1. Создаем продукт в Stripe
        product = create_stripe_product(name=item.name)

        # 2. Создаем цену в Stripe (в копейках)
        price = create_stripe_price(amount=item.price, product_id=product["id"])

        # 3. Создаем сессию оплаты
        session = create_stripe_session(price_id=price["id"])

        # 4. Сохраняем ID сессии, ссылку и сумму в БД
        payment.session_id = session["id"]
        payment.payment_link = session["url"]
        payment.save()

    @action(detail=False, methods=["get"], url_path=r"status/(?P<session_id>[^/.]+)")
    def check_status(self, request, session_id=None):
        """
        Эндпоинт: GET /payments/status/<session_id>/
        Получает данные о сессии из Stripe и обновляет статус в БД.
        """
        payment = get_object_or_404(Payment, session_id=session_id)
        session_data = retrieve_stripe_session(session_id)

        # Обновляем и сохраняем статус платежа в нашей системе
        payment_status = session_data.get("payment_status")  # 'paid', 'unpaid'
        payment.status = payment_status
        payment.save()

        return Response(
            {
                "payment_id": payment.id,
                "session_id": session_id,
                "session_status": session_data.get(
                    "status"
                ),  # 'open', 'complete', 'expired'
                "payment_status": payment_status,
            },
            status=status.HTTP_200_OK,
        )
