from django.urls import path

from .views import RecipeShortLinkRedirectView

app_name = 'recipes'
urlpatterns = [
    path(
        's/<int:recipe_id>/',
        RecipeShortLinkRedirectView.as_view(),
        name='recipe-short-link'),
]
