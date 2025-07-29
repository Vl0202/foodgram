from django.contrib.auth import get_user_model
from djoser.serializers import UserSerializer
from drf_extra_fields.fields import Base64ImageField
from rest_framework import serializers

from .models import Subscribe

User = get_user_model()


class CustomUserSerializer(UserSerializer):
    is_subscribed = serializers.SerializerMethodField()
    avatar = Base64ImageField()

    class Meta:
        model = User
        fields = (
            'email', 'id', 'username', 'first_name', 'last_name',
            'is_subscribed', 'avatar',
        )

    def get_is_subscribed(self, obj):
        user = self.context.get('request').user
        if not user or user.is_anonymous:
            return False
        return Subscribe.objects.filter(follower=user, following=obj.id)\
            .exists()


class AvatarSerializer(CustomUserSerializer):
    class Meta:
        model = User
        fields = ('avatar', )
