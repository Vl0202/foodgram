from django.urls import path

from .views import RecipeShortLinkRedirectView

app_name = 'recipes'
urlpatterns = [
    path('s/', RecipeShortLinkRedirectView.as_view()),
]
