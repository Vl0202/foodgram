import json

from django.core.management.base import BaseCommand
from recipes.models import Ingredient


class Command(BaseCommand):
    help = 'Загрузка ингредиентов из JSON файла'

    def add_arguments(self, parser):
        parser.add_argument('filename', type=str, help='Путь к JSON файлу')

    def handle(self, *args, **options):
        filename = options['filename']
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                data = json.load(f)
                created = Ingredient.objects.bulk_create(
                    [Ingredient(**item) for item in data],
                    ignore_conflicts=True
                )
                self.stdout.write(
                    f'Успешно загружено {len(created)} ингредиентов'
                )
        except FileNotFoundError:
            self.stderr.write(f'Ошибка: Файл {filename} не найден')
        except KeyError as e:
            self.stderr.write(f'Ошибка: Отсутствует обязательное поле {e}')
        except json.JSONDecodeError:
            self.stderr.write('Ошибка: Неверный формат JSON файла')
        except Exception as e:
            self.stderr.write(f'Ошибка: {e}')
