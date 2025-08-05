from django.shortcuts import get_object_or_404, redirect
from django.views import View
from django.http import Http404
from django.urls import reverse
from .models import Recipe

class RecipeShortLinkRedirectView(View):
    
    def get(self, request, short_code):
        try:
            recipe = get_object_or_404(Recipe, id=short_code)
            return redirect(
                reverse('recipe-detail', kwargs={'pk': recipe.id}),
                permanent=False
            )
        except (ValueError, Http404):
            raise Http404("Рецепт не существует")