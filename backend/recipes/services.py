from datetime import date

from django.db.models import Sum
from django.template.loader import render_to_string
from recipes.models import IngredientAmount


def generate_shopping_list(user):
    recipes_in_cart = user.shopping_carts.values_list(
        'recipe', flat=True)
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
        user.shoppingcarts.select_related('recipe').distinct())

    content = render_to_string('shopping_list.txt', {
        'ingredients': ingredients,
        'recipes': recipes,
        'date': date.today()
    })
    return content
