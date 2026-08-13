from urllib.parse import urlparse

from rest_framework import serializers


class HistoryMessageSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=["user", "assistant"])
    content = serializers.CharField(max_length=4000, trim_whitespace=True)


class AIAskSerializer(serializers.Serializer):
    message = serializers.CharField(max_length=4000, trim_whitespace=True)
    history = HistoryMessageSerializer(many=True, required=False, default=list)

    def validate_history(self, value):
        if len(value) > 10:
            raise serializers.ValidationError("L'historique est limité à 10 messages.")
        return value


class AIImageAskSerializer(serializers.Serializer):
    question = serializers.CharField(
        max_length=2000,
        required=False,
        default="Explique et corrige ce document scolaire.",
        trim_whitespace=True,
    )
    image_url = serializers.CharField(
        max_length=2048,
        required=False,
        allow_blank=True,
        default="",
        trim_whitespace=True,
    )

    def validate_image_url(self, value):
        if not value:
            return value
        parsed = urlparse(value)
        if parsed.scheme != "https" or not parsed.netloc:
            raise serializers.ValidationError("L'URL de l'image doit être une URL HTTPS valide.")
        return value


class GenerateQCMSerializer(serializers.Serializer):
    subject = serializers.CharField(max_length=100, trim_whitespace=True)
    level = serializers.CharField(max_length=10, trim_whitespace=True)
    topic = serializers.CharField(max_length=200, trim_whitespace=True)
    difficulty = serializers.CharField(
        max_length=10,
        required=False,
        default="MOYEN",
    )

    def validate_difficulty(self, value):
        value = value.upper()
        if value not in {"FACILE", "MOYEN", "DIFFICILE"}:
            raise serializers.ValidationError("Difficulté invalide.")
        return value


class SubmitQCMSerializer(serializers.Serializer):
    answers = serializers.DictField(
        child=serializers.IntegerField(min_value=0, max_value=3),
        allow_empty=False,
    )
