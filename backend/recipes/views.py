from django.http import Http404
from django.shortcuts import redirect
from django.views import View

from .models import Recipe


class RecipeShortLinkRedirectView(View):
    def get(self, request, recipe_id):
        if not Recipe.objects.filter(id=recipe_id).exists():
            raise Http404("Рецепт не существует")
        return redirect(f'/recipes/{recipe_id}/', permanent=False)
