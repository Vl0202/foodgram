from datetime import date

from django.db.models import Sum
from django.template.loader import render_to_string
from recipes.models import IngredientAmount, ShoppingCart


def generate_shopping_list(user):
    recipes_in_cart = (
        ShoppingCart.objects
        .filter(user=user)
        .values_list('recipe', flat=True)
    )
    ingredients = (
        IngredientAmount.objects
        .filter(recipe__in=recipes_in_cart)
        .values(
            'ingredient__name',
            'ingredient__measurement_unit'
        )
        .annotate(total=Sum('amount'))
        .order_by('ingredient__name')
    )

    recipes = (
        ShoppingCart.objects
        .filter(user=user)
        .select_related('recipe__author')
        .values('recipe__name', 'recipe__author__username')
        .distinct()
    )

    ingredients_for_template = [
        {
            'name': item['ingredient__name'],
            'unit': item['ingredient__measurement_unit'],
            'total': item['total']
        }
        for item in ingredients
    ]

    content = render_to_string('shopping_list.txt', {
        'ingredients': ingredients_for_template,
        'recipes': list(recipes),
        'date': date.today()
    })
    return content
