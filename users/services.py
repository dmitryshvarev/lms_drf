import stripe
from django.conf import settings

stripe.api_key = settings.STRIPE_API_KEY


def create_stripe_product(name: str) -> stripe.Product:
    """Создает продукт в Stripe (POST /v1/products)."""
    product = stripe.Product.create(name=name)
    return product


def create_stripe_price(
    amount: int, product_id: str, currency: str = "rub"
) -> stripe.Price:
    """Создает цену для продукта в Stripe (POST /v1/prices)."""
    price = stripe.Price.create(
        currency=currency,
        unit_amount=int(amount * 100),
        product=product_id,
    )
    return price


def create_stripe_session(
    price_id: str, success_url: str = "http://127.0.0.1:8000/"
) -> stripe.checkout.Session:
    """Создает сессию оплаты и возвращает объект со ссылкой url (POST /v1/checkout/sessions)."""
    session = stripe.checkout.Session.create(
        success_url=success_url,
        line_items=[{"price": price_id, "quantity": 1}],
        mode="payment",
    )
    return session


def retrieve_stripe_session(session_id: str):
    """Получает данные о сессии по её ID (GET /v1/checkout/sessions/:id)."""
    return stripe.checkout.Session.retrieve(session_id)
