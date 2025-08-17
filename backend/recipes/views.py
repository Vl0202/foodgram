from django.http import HttpResponseRedirect
from django.views import View


class RecipeShortLinkRedirectView(View):
    def get(self, request, recipe_id):
        return HttpResponseRedirect(f'/recipes/{recipe_id}/')
