import json

from django.core.management.base import BaseCommand


class BaseImportCommand(BaseCommand):
    model = None
    fields = []
    help_text = ''

    def add_arguments(self, parser):
        parser.add_argument('json_file', type=str, help=self.help_text)

    def handle(self, *args, **options):
        filename = options['json_file']
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                data = json.load(f)
                created = self.model.objects.bulk_create(
                    self.model(**item)
                    for item in data
                )
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Успешно загружено {len(created)} '
                        f'записей из {filename}')
                )
        except Exception as e:
            self.stderr.write(f'Ошибка при обработке файла {filename}: {e}')
