from django.urls import include, path
from rest_framework import routers

from .views import (IngredientViewSet, RecipeViewSet, TagViewSet,
                    UserProfileViewSet)

router = routers.DefaultRouter()
router.register(r'users', UserProfileViewSet)
router.register(r'tags', TagViewSet)
router.register(r'ingredients', IngredientViewSet)
router.register(r'recipes', RecipeViewSet)
app_name = 'api'


urlpatterns = [
    path('api/', include(router.urls)),
    path('api/auth/', include('djoser.urls.authtoken')),
]
