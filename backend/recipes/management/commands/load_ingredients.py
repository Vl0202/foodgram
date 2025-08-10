from recipes.models import Ingredient

from ._base_import import BaseImportCommand


class Command(BaseImportCommand):
    model = Ingredient
    help_text = 'Загрузка ингредиентов из JSON файла'
