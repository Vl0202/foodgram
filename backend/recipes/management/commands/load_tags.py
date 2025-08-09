from recipes.models import Tag

from ._base_import import BaseImportCommand


class Command(BaseImportCommand):
    model = Tag
    fields = ['name', 'color', 'slug']
    help_text = 'Загрузка тегов из JSON файла'
