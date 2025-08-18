from datetime import date
from django.db.models import Sum
from django.template.loader import render_to_string
from django.utils.dateformat import format
from recipes.models import IngredientAmount, ShoppingCart


def generate_shopping_list(user):
    recipes_in_cart = user.shopping_carts.all().values_list('recipe', flat=True)
    
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

    # Форматируем дату по-русски
    months = {
        1: 'января', 2: 'февраля', 3: 'марта', 4: 'апреля',
        5: 'мая', 6: 'июня', 7: 'июля', 8: 'августа',
        9: 'сентября', 10: 'октября', 11: 'ноября', 12: 'декабря'
    }
    today = date.today()
    formatted_date = f"{today.day} {months[today.month]} {today.year} года"

    content = render_to_string('shopping_list.txt', {
        'ingredients': ingredients_for_template,
        'recipes': list(recipes),
        'date': formatted_date
    })
    return content