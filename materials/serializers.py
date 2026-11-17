from rest_framework import serializers

from materials.models import Course, Lesson
from materials.validators import YouTubeOnlyValidator


class LessonSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lesson
        fields = "__all__"
        validators = [
            YouTubeOnlyValidator(field="video_url"),
            YouTubeOnlyValidator(field="description"),
        ]


class CourseSerializer(serializers.ModelSerializer):
    lessons = LessonSerializer(many=True, read_only=True)

    lessons_count = serializers.SerializerMethodField()

    def get_lessons_count(self, obj):
        return obj.lessons.count()

    class Meta:
        model = Course
        fields = "__all__"
        validators = [
            YouTubeOnlyValidator(field="description"),
        ]
