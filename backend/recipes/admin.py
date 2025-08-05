from django.contrib import admin
from django.utils.html import mark_safe
from django.contrib.auth.admin import UserAdmin

from .models import UserProfile, Subscribe
from .models import Favorite, Ingredient, Recipe, ShoppingCart, Tag


class SubscribeAdmin(admin.ModelAdmin):
    list_display = ('id', 'follower', 'following')
    list_filter = ('following', 'follower')
    search_fields = (
        'follower__username',
        'following__username'
    )
    
    class Meta:
        verbose_name = 'Подписка'
        verbose_name_plural = 'Подписки'

class UserProfileAdmin(UserAdmin):
    
    fieldsets = UserAdmin.fieldsets + (
        ('Дополнительно', {
            'fields': (
                'avatar',
                'full_name',
                'recipe_count',
                'subscription_count',
                'follower_count',
            )
        }),
    )
    list_display = (
        'username',
        'email',
        'full_name',
        'recipe_count',
        'subscription_count',
        'follower_count',
        'avatar_tag'
    )
    list_filter = UserAdmin.list_filter + ('recipe_count',)
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()
    
    @mark_safe
    def avatar_tag(self):
        if self.avatar:
            return f'<img src="{self.avatar.url}" width="50" height="50">'
        return 'Нет аватара'
    avatar_tag.short_description = 'Аватар'
    
    @property
    def recipe_count(self):
        return self.recipes.count()
    
    @property
    def subscription_count(self):
        return self.subscriptions.count()
    
    @property
    def follower_count(self):
        return self.followers.count()


class IngredientAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'measurement_unit')
    search_fields = ('name__icontains', 'measurement_unit')
    list_filter = ('measurement_unit',)


class RecipeAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'author', 'cooking_time', 'ingredients', 'tags', 'image', 'count_favorites')
    list_filter = ('tags', 'author' )
    search_fields = ('name__icontains', 'author__username__icontains')

    def count_favorites(self, recipe):
        return recipe.favorites.count()


class TagAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'slug', 'recipes_count')

    def recipes_count(self, tag):
        return tag.recipes.count()


class ShoppingCartAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'recipe')
    search_fields = ('user__username', 'recipe__name')


class FavoriteAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'recipe') 
    search_fields = ('user__username', 'recipe__name')

admin.site.register(UserProfile, UserProfileAdmin)
admin.site.register(Subscribe,SubscribeAdmin)
admin.site.register(Tag, TagAdmin)
admin.site.register(Ingredient, IngredientAdmin)
admin.site.register(Recipe, RecipeAdmin)
admin.site.register(ShoppingCart, ShoppingCartAdmin)
admin.site.register(Favorite, FavoriteAdmin)
