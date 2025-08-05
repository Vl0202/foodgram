import json
from django.core.management.base import BaseCommand
from recipes.models import Ingredient

class Command(BaseCommand):
    help = 'Load ingredients from JSON file'

    def handle(self, *args, **options):
        try:
            with open('data/ingredients.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
                ingredients = [
                    Ingredient(
                        name=item['name'],
                        measurement_unit=item['measurement_unit']
                    )
                    for item in data
                ]
                Ingredient.objects.bulk_create(ingredients)
                self.stdout.write(f'Successfully loaded {len(ingredients)} ingredients')
        except FileNotFoundError:
            self.stdout.write('Error: data/ingredients.json file not found')
        except KeyError as e:
            self.stdout.write(f'Error: missing required field {str(e)}')
        except Exception as e:
            self.stdout.write(f'Error: {str(e)}')