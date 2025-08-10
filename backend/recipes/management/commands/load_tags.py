from recipes.models import Tag

from ._base_import import BaseImportCommand


class Command(BaseImportCommand):
    model = Tag
    help_text = 'Загрузка тегов из JSON файла'
