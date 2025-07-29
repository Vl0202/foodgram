import django_filters
from django_filters import rest_framework as filters

from .models import Recipe


class RecipeFilter(django_filters.FilterSet):
    is_favorited = django_filters.NumberFilter(method='filter_is_favorited')
    is_in_shopping_cart = django_filters.NumberFilter(
        method='filter_is_in_shopping_cart',
    )
    tags = filters.AllValuesMultipleFilter(field_name='tags__slug')

    class Meta:
        model = Recipe
        fields = ('is_favorited', 'is_in_shopping_cart', 'author', 'tags')

    def filter_is_favorited(self, queryset, name, value):
        if self.request.user.is_anonymous:
            return queryset
        if value == 0:
            return queryset.exclude(favorites__user=self.request.user)
        return queryset.filter(favorites__user=self.request.user)

    def filter_is_in_shopping_cart(self, queryset, name, value):
        if self.request.user.is_anonymous:
            return queryset
        if value == 0:
            return queryset.exclude(shopping_cart__user=self.request.user)
        return queryset.filter(shopping_cart__user=self.request.user)
