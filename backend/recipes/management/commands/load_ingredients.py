from recipes.models import Ingredient

from ._base_import import BaseImportCommand


class Command(BaseImportCommand):
    model = Ingredient
    fields = ['name', 'measurement_unit']
    help_text = 'Загрузка ингредиентов из JSON файла'
