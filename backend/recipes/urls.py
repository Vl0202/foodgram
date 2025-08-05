from django.urls import path

from .views import RecipeShortLinkRedirectView

urlpatterns = [
    path('s/', RecipeShortLinkRedirectView.as_view()),
]
