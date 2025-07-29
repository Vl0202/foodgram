import base64
import os

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from djoser.views import UserViewSet
from rest_framework import permissions, status
from rest_framework.decorators import action
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from recipes.paginations import PageLimitPagination
from recipes.serializers import FavoriteSerializer
from .models import Subscribe
from .serializers import AvatarSerializer

User = get_user_model()


class CustomUserViewSet(UserViewSet):
    pagination_class = PageLimitPagination

    def get_permissions(self):
        if self.action in ['retrieve', 'list']:
            return (permissions.IsAuthenticatedOrReadOnly(), )
        return super().get_permissions()

    @action(
        methods=['PUT', 'PATCH'],
        detail=False,
        permission_classes=[IsAuthenticated],
        url_path='me/avatar'
    )
    def avatar(self, request):
        user = request.user
        avatar_base64 = request.data.get('avatar')
        if avatar_base64:
            avatar_base64 = avatar_base64.split(",")[1]
            avatar_data = base64.b64decode(avatar_base64)
            avatar_file = ContentFile(avatar_data,
                                      name=f'avatar{user.id}.png')
            user.avatar.save(f'avatar{user.id}.png', avatar_file)
            user.save()
            return Response(
                AvatarSerializer(user, context={'request': request}).data
            )
        else:
            return Response({"errors": "Аватар не предоставлен"},
                            status=400)

    @avatar.mapping.delete
    def del_avatar(self, request):
        user = request.user
        if user.avatar:
            os.remove(user.avatar.path)
            user.avatar = None
            user.save()
            return Response(status=204)
        else:
            return Response({"errors": "У вас нет аватара"}, status=400)

    @action(
        methods=['POST', 'GET'],
        detail=True,
    )
    def subscribe(self, request, id=None):
        follower = request.user
        following = get_object_or_404(User, id=id)

        if follower == following:
            return Response(
                data={'errors': 'Вы не можете подписываться на самого себя'},
                status=status.HTTP_400_BAD_REQUEST
            )
        if Subscribe.objects.filter(
            follower=follower, following=following,
        ).exists():
            return Response(
                data={'errors': 'Вы уже подписаны на этого пользователя'},
                status=status.HTTP_400_BAD_REQUEST
            )

        subscribe = Subscribe.objects.create(
            follower=follower,
            following=following,
        )
        serializer = FavoriteSerializer(
            subscribe,
            context={'request': request},
        )
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @subscribe.mapping.delete
    def del_subscribe(self, request, id=None):
        follower = request.user
        following = get_object_or_404(User, id=id)

        subscribe = Subscribe.objects.filter(
            follower=follower,
            following=following,
        )
        if subscribe.exists:
            subscribe.delete()
            return Response(
                status=status.HTTP_204_NO_CONTENT,
            )
        error_code = 'Нельзя подписаться на себя' if follower == following \
            else 'Вы не подписаны на пользователя'
        return Response(
            data={'errors': error_code},
            status=status.HTTP_400_BAD_REQUEST,
        )

    @action(detail=False,
            permission_classes=[IsAuthenticated])
    def subscriptions(self, request):
        follower = request.user
        queryset = Subscribe.objects.filter(follower=follower)
        pages = self.paginate_queryset(queryset)
        serializer = FavoriteSerializer(
            pages,
            many=True,
            context={'request': request}
        )
        return self.get_paginated_response(serializer.data)
