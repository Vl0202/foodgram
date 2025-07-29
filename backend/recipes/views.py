import base64
import csv
from collections import defaultdict

from django.db.models import Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from urlshortner.utils import shorten_url

from .filters import RecipeFilter
from .mixins import ListRetrieveModelMixin
from .models import (Favorite, Ingredient, IngredientAmount, Recipe,
                     ShoppingCart, Tag)
from .paginations import PageLimitPagination
from .permissions import IsAuthorOrReadOnlyPermission
from .serializers import (IngredientSerializer, RecipeSerializer,
                          ShoppingCartSerializer, TagSerializer)


class TagViewSet(ListRetrieveModelMixin):

    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    pagination_class = None
    permission_classes = (permissions.IsAuthenticatedOrReadOnly, )


class IngredientViewSet(ListRetrieveModelMixin):

    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    pagination_class = None
    permission_classes = (permissions.IsAuthenticatedOrReadOnly, )

    def get_queryset(self):
        queryset = Ingredient.objects.all()
        name = self.request.query_params.get('name')
        if name:
            queryset = queryset.filter(name__startswith=name)
        return queryset


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

    def add_recipe(self, request, model, pk=None):
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
            return Response(ShoppingCartSerializer(obj).data,
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
        return self.add_recipe(request, ShoppingCart, pk)

    @shopping_cart.mapping.delete
    def delete_shopping_cart(self, request, pk=None):
        return self.remove_recipe(request, ShoppingCart, pk)

    @action(detail=False,
            permission_classes=(IsAuthenticated, ),
            url_path='download_shopping_cart')
    def download_shoopping_cart(self, request):
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
        return self.add_recipe(request, Favorite, pk)

    @favorite.mapping.delete
    def del_favorite(self, request, pk=None):
        return self.remove_recipe(request, Favorite, pk)
