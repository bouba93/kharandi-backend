from rest_framework import serializers
from .models import User, Profile, PointTransaction


class ProfileSerializer(serializers.ModelSerializer):
    points_in_gnf = serializers.ReadOnlyField()

    class Meta:
        model  = Profile
        fields = [
            "first_name", "last_name", "avatar", "school_level",
            "birth_date", "city", "bio", "onboarding_completed",
            "niveau", "serie", "display_name", "tutor_status",
            "tutor_subjects", "tutor_levels", "tutor_zone",
            "shop_name", "shop_description", "delivery_zone", "shop_status",
            "points", "points_in_gnf",
        ]


class UserSerializer(serializers.ModelSerializer):
    profile = ProfileSerializer(read_only=True)

    class Meta:
        model        = User
        fields       = ["id", "phone", "role", "date_joined", "profile"]
        read_only_fields = ["id", "phone", "date_joined"]


class ProfileUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Profile
        fields = [
            "first_name", "last_name", "avatar", "school_level",
            "birth_date", "city", "bio", "onboarding_completed",
        ]


class OTPSendSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=20)

    def validate_phone(self, value):
        clean = value.replace(" ", "").replace("-", "")
        if not clean.startswith("+"):
            clean = "+224" + clean.lstrip("0")
        return clean


class OTPVerifySerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=20)
    code  = serializers.CharField(max_length=10, required=False, allow_blank=True)
    role  = serializers.ChoiceField(
        choices=["STUDENT", "TUTOR", "PARENT", "VENDOR"],
        default="STUDENT", required=False
    )

    def validate_phone(self, value):
        clean = value.replace(" ", "").replace("-", "")
        if not clean.startswith("+"):
            clean = "+224" + clean.lstrip("0")
        return clean


class PointTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model  = PointTransaction
        fields = [
            "id", "type", "source", "points",
            "balance_after", "description", "reference", "created_at",
        ]
