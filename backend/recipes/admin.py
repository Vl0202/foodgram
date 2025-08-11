from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import mark_safe

from .models import (Favorite, Ingredient, Recipe, ShoppingCart, Subscribe,
                     Tag, UserProfile)


class CountRecipesMixin:
    list_display = ('recipe_count',)

    @admin.display(
        description='Количество рецептов',
        ordering='recipes__count'
    )
    def recipe_count(self, obj):
        return obj.recipes.count()


class SubscribeAdmin(admin.ModelAdmin):
    list_display = ('id', 'follower', 'following')
    list_filter = ('following', 'follower')
    search_fields = (
        'follower__username',
        'following__username'
    )


class UserProfileAdmin(CountRecipesMixin, UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ('Дополнительно', {
            'fields': (
                'avatar',
                'recipe_count',
                'subscription_count',
                'follower_count'
            )
        }),
    )
    list_display = (
        'username',
        'email',
        'get_full_name',
        'avatar_tag',
        'subscription_count',
        'follower_count',
        *CountRecipesMixin.list_display
    )

    @admin.display(
        description='Полное имя',
        ordering='first_name'
    )
    def get_full_name(self, user):
        return f"{user.first_name} {user.last_name}".strip() or user.username

    @admin.display(
        description='Аватар',
        ordering='avatar'
    )
    @mark_safe
    def avatar_tag(self, user):
        if user.avatar:
            return f'<img src="{user.avatar.url}" width="50" height="50">'

    @admin.display(
        description='Количество подписок',
        ordering='subscriptions__count'
    )
    def subscription_count(self, obj):
        return obj.authors.count()

    @admin.display(
        description='Количество подписчиков',
        ordering='followers__count'
    )
    def follower_count(self, obj):
        return obj.followers.count()


class IngredientAdmin(CountRecipesMixin, admin.ModelAdmin):
    list_display = (
        'id', 'name', 'measurement_unit', *CountRecipesMixin.list_display
    )
    search_fields = ('name__icontains', 'measurement_unit')


class RecipeAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'name', 'author',
        'cooking_time', 'get_ingredients',
        'get_tags', 'image', 'count_favorites'
    )
    list_filter = ('tags', 'author')
    search_fields = ('name__icontains', 'author__username__icontains')

    @admin.display(
        description='Ингредиенты',
        ordering='ingredients__name'
    )
    def get_ingredients(self, recipe):
        ingredients_list = [
            f"- {ing.ingredient.name} "
            f"({ing.amount} {ing.ingredient.measurement_unit})"
            for ing in recipe.recipe_amounts.select_related('ingredient').all()
        ]
        return mark_safe('<br>'.join(ingredients_list))

    @admin.display(
        description='Теги',
        ordering='tags__name'
    )
    def get_tags(self, obj):
        return ', '.join(tag.name for tag in obj.tags.all())

    @admin.display(
        description='Лайки',
        ordering='favorites__count'
    )
    def count_favorites(self, recipe):
        return recipe.favorites.count()


class TagAdmin(CountRecipesMixin, admin.ModelAdmin):
    list_display = ('id', 'name', 'slug', *CountRecipesMixin.list_display)
    list_filter = ('name', 'slug')


class ShoppingCartAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'recipe')
    search_fields = ('user__username', 'recipe__name')
    list_filter = ('user', 'recipe')


class FavoriteAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'recipe')
    search_fields = ('user__username', 'recipe__name')
    list_filter = ('user', 'recipe')


admin.site.register(UserProfile, UserProfileAdmin)
admin.site.register(Subscribe, SubscribeAdmin)
admin.site.register(Tag, TagAdmin)
admin.site.register(Ingredient, IngredientAdmin)
admin.site.register(Recipe, RecipeAdmin)
admin.site.register(ShoppingCart, ShoppingCartAdmin)
admin.site.register(Favorite, FavoriteAdmin)
