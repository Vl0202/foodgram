from django.urls import include, path
from rest_framework import routers

from .views import CustomUserViewSet

app_name = 'users'

router = routers.DefaultRouter()
router.register(r'users', CustomUserViewSet)

urlpatterns = [
    path('api/', include(router.urls)),
    path('api/auth/', include('djoser.urls.authtoken')),
    path('api/', include('djoser.urls')),
]
