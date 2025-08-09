from datetime import date

from django.db.models import Sum
from django.template.loader import render_to_string
from recipes.models import IngredientAmount


def generate_shopping_list(user):
    ingredients = (
        IngredientAmount.objects
        .filter(recipe__shopping_cart__user=user)
        .values('ingredient__name', 'ingredient__measurement_unit')
        .annotate(total=Sum('amount'))
        .order_by('ingredient__name')
    )

    recipes = (
        user.shopping_cart.select_related('author')
        .order_by('name').distinct()
    )

    return render_to_string('shopping_list.txt', {
        'date': date.today(),
        'ingredients': [{
            'name': ingredient['ingredient__name'],
            'unit': ingredient['ingredient__measurement_unit'],
            'total': ingredient['total']
        } for ingredient in ingredients],
        'recipes': recipes
    })
