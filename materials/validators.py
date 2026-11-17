import re
from rest_framework import serializers


class YouTubeOnlyValidator:
    """Проверяет, что в тексте или поле ссылки нет URL на сторонние ресурсы, кроме youtube.com."""

    def __init__(self, field):
        self.field = field

    def __call__(self, attrs):
        # Получаем значение поля из словаря переданных данных
        value = attrs.get(self.field)
        if not value:
            return

        # Регулярное выражение для поиска любых ссылок (http, https, www)
        url_pattern = r'(https?://[^\s]+|www\.[^\s]+)'
        found_urls = re.findall(url_pattern, str(value), flags=re.IGNORECASE)

        for url in found_urls:
            # Проверяем, содержит ли найденная ссылка домен youtube.com или youtu.be
            if not re.search(r'(youtube\.com|youtu\.be)', url, flags=re.IGNORECASE):
                raise serializers.ValidationError(
                    {self.field: f"Запрещено добавлять ссылки на сторонние ресурсы ({url}). Разрешен только youtube.com."}
                )
