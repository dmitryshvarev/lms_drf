from rest_framework import serializers

from users.models import Payment, User


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = "__all__"
        read_only_fields = ["date"]  # auto_now_add поле нельзя менять вручную

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Сумма оплаты должна быть больше нуля.")
        return value

    def validate(self, data):
        course = data.get("course")
        lesson = data.get("lesson")

        if course and lesson:
            raise serializers.ValidationError(
                "Нельзя указать одновременно и курс, и урок. Выберите что-то одно."
            )
        if not course and not lesson:
            raise serializers.ValidationError(
                "Необходимо указать либо курс, либо урок для оплаты."
            )

        return data


class UserSerializer(serializers.ModelSerializer):
    payments = PaymentSerializer(many=True, read_only=True)

    class Meta:
        model = User
        fields = "__all__"
