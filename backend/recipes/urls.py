from django.urls import include, path
from rest_framework import routers

from .views import IngredientViewSet, RecipeViewSet, TagViewSet

router = routers.DefaultRouter()
router.register(r'tags', TagViewSet)
router.register(r'ingredients', IngredientViewSet)
router.register(r'recipes', RecipeViewSet)
app_name = 'recipes'

urlpatterns = [
    path('api/', include(router.urls)),
    path('r/', include('urlshortner.urls')),
]
