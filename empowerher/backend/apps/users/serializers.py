from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from .models import EntrepreneurProfile


class EntrepreneurProfileSerializer(serializers.ModelSerializer):

    class Meta:
        model = EntrepreneurProfile

        fields = [
            "phone_number",
            "city",
            "state",
            "business_stage",
            "preferred_language",
        ]
        # The model stores ciphertext, so the plain-text limits live here.
        extra_kwargs = {
            "phone_number": {"max_length": 15, "allow_blank": True},
            "city": {"max_length": 100, "allow_blank": True},
        }


class UserSerializer(serializers.ModelSerializer):

    profile = EntrepreneurProfileSerializer(
        source="entrepreneur_profile",
        read_only=True,
    )

    class Meta:
        model = User

        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "profile",
        ]


class RegisterSerializer(serializers.ModelSerializer):

    password = serializers.CharField(
        write_only=True,
        validators=[validate_password]
    )

    password_confirm = serializers.CharField(
        write_only=True
    )

    phone_number = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=15,
    )

    city = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=100,
    )

    state = serializers.CharField(
        required=False,
        allow_blank=True
    )

    business_stage = serializers.ChoiceField(
        choices=EntrepreneurProfile.BUSINESS_STAGE_CHOICES,
        required=False,
        default="idea"
    )

    preferred_language = serializers.ChoiceField(
        choices=EntrepreneurProfile.LANGUAGE_CHOICES,
        required=False,
        default="en"
    )

    class Meta:
        model = User

        fields = [
            "username",
            "email",
            "password",
            "password_confirm",
            "first_name",
            "last_name",
            "phone_number",
            "city",
            "state",
            "business_stage",
            "preferred_language",
        ]

    def validate(self, data):

        if data["password"] != data["password_confirm"]:
            raise serializers.ValidationError({
                "password": "Passwords do not match."
            })

        return data

    def create(self, validated_data):

        phone_number = validated_data.pop(
            "phone_number",
            ""
        )

        city = validated_data.pop(
            "city",
            ""
        )

        state = validated_data.pop(
            "state",
            ""
        )

        business_stage = validated_data.pop(
            "business_stage",
            "idea"
        )

        preferred_language = validated_data.pop(
            "preferred_language",
            "en"
        )

        validated_data.pop(
            "password_confirm"
        )

        password = validated_data.pop(
            "password"
        )

        user = User.objects.create_user(
            password=password,
            **validated_data
        )

        EntrepreneurProfile.objects.create(
            user=user,
            phone_number=phone_number,
            city=city,
            state=state,
            business_stage=business_stage,
            preferred_language=preferred_language,
        )

        return user
