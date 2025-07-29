from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import CustomUser, Subscribe

admin.site.register(Subscribe)


UserAdmin.fieldsets += (
    ('Extra Fields', {'fields': ('avatar',)}),
)
admin.site.register(CustomUser, UserAdmin)
