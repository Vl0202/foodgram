import base64
import csv
import os
from collections import defaultdict

from api.filters import RecipeFilter
from api.paginations import PageLimitPagination
from api.permissions import IsAuthorOrReadOnlyPermission
from api.serializers import (AvatarSerializer, IngredientSerializer,
                             RecipeSerializer, RecipeShortSerializer,
                             SubscribedUserSerializer, TagSerializer)
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.db.models import Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from djoser.views import UserViewSet
from recipes.models import (Favorite, Ingredient, IngredientAmount, Recipe,
                            ShoppingCart, Subscribe, Tag)
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from urlshortner.utils import shorten_url

User = get_user_model()


class UserProfileViewSet(UserViewSet):
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
        serializer = SubscribedUserSerializer(
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
        serializer = SubscribedUserSerializer(
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
        get_object_or_404(Recipe, id=pk)
        long_url = request.build_absolute_uri(f'/api/recipes/{pk}/')
        short_url = shorten_url(long_url, is_permanent=False)
        return Response({'short-link': short_url})

    def add_to_favorite_or_shopping_cart(self, request, model, pk=None):
        user = request.user
        try:
            recipe = Recipe.objects.get(
                id=pk
            )
        except Recipe.DoesNotExist:
            error_status = status.HTTP_404_NOT_FOUND if model == ShoppingCart\
                else status.HTTP_400_BAD_REQUEST
            return Response(
                status=error_status,
                data={'errors': 'Указанного рецепта не существует'}
            )
        if model.objects.filter(
            recipe=recipe,
            user=user
        ).exists():
            model_name = 'список покупок' if model == ShoppingCart\
                else 'избранное'
            return Response({'errors': f'Рецепт уже добавлен в {model_name}'},
                            status=status.HTTP_400_BAD_REQUEST)
        obj = model.objects.create(
            recipe=recipe,
            user=user,
        )
        if model == ShoppingCart:
            return Response(RecipeShortSerializer(obj).data,
                            status=status.HTTP_201_CREATED)

        return Response(
            data={
                'id': recipe.id,
                'name': recipe.name,
                'cooking_time': recipe.cooking_time,
                'image': base64.b64encode(recipe.image.read()).decode('utf-8')
            },
            status=status.HTTP_201_CREATED
        )

    def remove_recipe(self, request, model, pk=None):
        user = request.user
        recipe = get_object_or_404(Recipe, id=pk)
        instance = model.objects.filter(
            recipe=recipe,
            user=user
        )
        if instance.exists():
            instance.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        model_name = 'список покупок' if model == ShoppingCart\
            else 'избранное'
        return Response(
            status=status.HTTP_400_BAD_REQUEST,
            data={f'errors: Рецепт не был добавлен в {model_name}'}
        )

    @action(
        methods=['POST'],
        detail=True,
        permission_classes=(IsAuthenticated, )
    )
    def shopping_cart(self, request, pk=None):
        return self.add_to_favorite_or_shopping_cart(request, ShoppingCart, pk)

    @shopping_cart.mapping.delete
    def delete_shopping_cart(self, request, pk=None):
        return self.remove_recipe(request, ShoppingCart, pk)

    @action(detail=False,
            permission_classes=(IsAuthenticated, ),
            url_path='download_shopping_cart')
    def download_shopping_cart(self, request):
        ingredients = IngredientAmount.objects.filter(
            recipe__shopping_cart__user=request.user
        ).values(
            'ingredient__name',
            'ingredient__measurement_unit'
        ).annotate(total_amount=Sum('amount'))

        total_ingredients = defaultdict(int)
        for ingredient in ingredients:
            name = ingredient['ingredient__name']
            unit = ingredient['ingredient__measurement_unit']
            total_ingredients[f'{name} ({unit})'] += ingredient['total_amount']

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; \
            filename="shopping_cart.csv"'

        writer = csv.writer(response)
        writer.writerow(['Ингредиент', 'Количество'])

        for item in total_ingredients:
            writer.writerow([item, total_ingredients[item]])
        return response

    @action(methods=['POST'], detail=True,
            permission_classes=(IsAuthenticated, ))
    def favorite(self, request, pk=None):
        return self.add_to_favorite_or_shopping_cart(request, Favorite, pk)

    @favorite.mapping.delete
    def del_favorite(self, request, pk=None):
        return self.remove_recipe(request, Favorite, pk)
