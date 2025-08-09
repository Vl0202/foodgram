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
        methods=['POST', 'GET', 'DELETE'],
        detail=True,
    )
    def subscribe(self, request, id=None):
        if request.method == 'DELETE':
            deleted_count = Subscribe.objects.filter(
                follower=request.user,
                following_id=id
            ).delete()
            return Response(
                status=(
                    status.HTTP_204_NO_CONTENT
                    if deleted_count
                    else status.HTTP_404_NOT_FOUND
                )
            )

        if request.method == 'GET':
            return Response({
                'is_subscribed': Subscribe.objects.filter(
                    follower=request.user,
                    following_id=id
                ).exists()
            }, status=status.HTTP_200_OK)

        if request.user.id == id:
            return Response(
                {'errors': 'Нельзя подписаться на себя'},
                status=status.HTTP_400_BAD_REQUEST
            )

        created = Subscribe.objects.get_or_create(
            follower=request.user,
            following_id=id,
            defaults={'follower': request.user, 'following_id': id}
        )

        if not created:
            return Response(
                {'errors': f'Вы уже подписаны на пользователя с id={id}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        return Response(status=status.HTTP_201_CREATED)

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
            raise Http404(f'Рецепт с id={pk} не найден')

        long_url = request.build_absolute_uri(
            reverse('api:recipes-detail', args=[pk])
        )
        return Response({'short-link': long_url})

    def add_to_favorite_or_shopping_cart(self, request, model, pk=None):
        collection_name = (
            'избранное'
            if model == Favorite
            else 'корзину покупок'
        )
        obj, created = model.objects.get_or_create(
            recipe_id=pk,
            user=request.user,
            defaults={'recipe_id': pk, 'user': request.user}
        )

        if not created:
            return Response(
                {'errors': f'Рецепт {pk} уже добавлен в {collection_name}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        return Response(
            RecipeShortSerializer(obj).data,
            status=status.HTTP_201_CREATED
        )

    def remove_recipe(self, request, model, pk=None):
        user = request.user
        instance = get_object_or_404(
            model.objects.filter(recipe=pk, user=user),
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
