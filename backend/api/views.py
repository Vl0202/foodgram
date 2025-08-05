import base64
import os

from api.filters import RecipeFilter
from api.paginations import PageLimitPagination
from api.permissions import IsAuthorOrReadOnlyPermission
from api.serializers import (AvatarSerializer, IngredientSerializer,
                             RecipeSerializer, RecipeShortSerializer,
                             SubscribeSerializer, TagSerializer)
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django_filters.rest_framework import DjangoFilterBackend
from djoser.views import UserViewSet
from recipes.models import (Favorite, Ingredient, Recipe, ShoppingCart,
                            Subscribe, Tag)
from recipes.services import generate_shopping_list
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from urlshortner.utils import shorten_url

User = get_user_model()


class UserProfileViewSet(UserViewSet):
    pagination_class = PageLimitPagination

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
            avatar_base64 = avatar_base64.split(',')[1]
            avatar_data = base64.b64decode(avatar_base64)
            avatar_file = ContentFile(avatar_data,
                                      name=f'avatar{user.id}.png')
            user.avatar.save(f'avatar{user.id}.png', avatar_file)
            user.save()
            return Response(
                AvatarSerializer(user, context={'request': request}).data
            )
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
        following = get_object_or_404(User, id=id)

        if request.method == 'POST':
            if Subscribe.objects.filter(
                follower=request.user,
                following=following,
            ).exists():
                msg = f'Вы уже подписаны на {following.username}'
                return Response(
                    {'errors': msg}, status=status.HTTP_400_BAD_REQUEST
                )

            Subscribe.objects.create(
                follower=request.user,
                following=following,
            )
            return Response(status=status.HTTP_201_CREATED)

        elif request.method == 'GET':
            return Response(
                data={'is_subscribed': Subscribe.objects.filter(
                    follower=request.user,
                    following=following,
                ).exists()},
                status=status.HTTP_200_OK
            )

    @subscribe.mapping.delete
    def del_subscribe(self, request, id=None):
        following = get_object_or_404(User, id=id)

        if request.user == following:
            return Response(
                data={'errors': 'Нельзя отписаться от себя'},
                status=status.HTTP_400_BAD_REQUEST
            )

        Subscribe.objects.filter(
            follower=request.user,
            following=following
        ).delete()

        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False,
            permission_classes=[IsAuthenticated])
    def subscriptions(self, request):
        pages = self.paginate_queryset(request.user.followers.all())
        serializer = SubscribeSerializer(
            pages,
            many=True,
            context={'request': request}
        )
        return self.get_paginated_response(serializer.data)


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    pagination_class = None
    permission_classes = (permissions.IsAuthenticatedOrReadOnly,)


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    pagination_class = None
    permission_classes = (permissions.IsAuthenticatedOrReadOnly,)
    filter_backends = (DjangoFilterBackend,)
    filterset_fields = ('name',)


class RecipeViewSet(viewsets.ModelViewSet):
    queryset = Recipe.objects.all()
    serializer_class = RecipeSerializer
    pagination_class = PageLimitPagination
    permission_classes = (IsAuthorOrReadOnlyPermission, )
    filter_backends = (DjangoFilterBackend,)
    filterset_class = RecipeFilter

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    @action(detail=True,
            permission_classes=(permissions.IsAuthenticatedOrReadOnly, ),
            url_path='get-link')
    def get_link(self, request, pk=None):
        exists = Recipe.objects.filter(id=pk).exists()
        if not exists:
            raise Http404('Рецепт не найден')

        long_url = request.build_absolute_uri(
            reverse('recipe-detail', args=[pk])
        )
        short_url = shorten_url(long_url, is_permanent=False)
        return Response({'short-link': short_url})

    def add_to_favorite_or_shopping_cart(self, request, model, pk=None):
        user = request.user
        recipe = get_object_or_404(Recipe, id=pk)

        if model.objects.filter(recipe=recipe, user=user).exists():
            return Response(
                {'errors': 'Рецепт уже добавлен в коллекцию'},
                status=status.HTTP_400_BAD_REQUEST
            )

        obj = model.objects.create(recipe=recipe, user=user)
        serializer = RecipeShortSerializer(obj)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def remove_recipe(self, request, model, pk=None):
        user = request.user
        instance = get_object_or_404(
            model.objects.filter(recipe=pk, user=user),
            'Рецепт не был добавлен в коллекцию'
        )
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        methods=['POST'],
        detail=True,
        permission_classes=(IsAuthenticated, )
    )
    def shopping_cart(self, request, pk=None):
        return self.add_recipe(request, ShoppingCart, pk)

    @shopping_cart.mapping.delete
    def delete_shopping_cart(self, request, pk=None):
        return self.remove_recipe(request, ShoppingCart, pk)

    @action(detail=False,
            permission_classes=(IsAuthenticated, ),
            url_path='download_shopping_cart')
    def download_shopping_cart(self, request):
        response = HttpResponse(
            generate_shopping_list(request.user),
            content_type='text/plain'
        )
        response['Content-Disposition'] = (
            'attachment; filename="shopping_list.txt"'
        )
        return response

    @action(methods=['POST'], detail=True,
            permission_classes=(IsAuthenticated, ))
    def favorite(self, request, pk=None):
        return self.add_to_favorite_or_shopping_cart(request, Favorite, pk)

    @favorite.mapping.delete
    def del_favorite(self, request, pk=None):
        return self.remove_recipe(request, Favorite, pk)
