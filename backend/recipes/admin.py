from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.db import models
from django.utils.html import mark_safe

from .models import (Favorite, Ingredient, IngredientAmount, Recipe,
                     ShoppingCart, Subscribe, Tag, UserProfile)


class CountRecipesMixin:
    list_display = ('recipe_count',)

    @admin.display(
        description='Рецепты',
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
            )
        }),
    )
    list_display = (
        'username',
        'email',
        'get_full_name',
        'avatar_tag',
        'get_subscriptions_count',
        'get_subscribers_count',
        *CountRecipesMixin.list_display
    )

    @admin.display(description='Полное имя')
    def get_full_name(self, user):
        return f"{user.first_name} {user.last_name}".strip()

    @admin.display(description='Аватар')
    def avatar_tag(self, user):
        if user.avatar:
            return mark_safe(
                f'<img src="{user.avatar.url}" width="50" height="50">')
        return "Нет аватара"
    avatar_tag.short_description = 'Аватар'

    @admin.display(description='Подписки')
    def get_subscriptions_count(self, obj):
        return obj.authors.count()

    @admin.display(description='Подписчики')
    def get_subscribers_count(self, obj):
        return obj.followers.count()

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related(
            'authors', 'followers'
        )


class IngredientAdmin(CountRecipesMixin, admin.ModelAdmin):
    list_display = (
        'id', 'name', 'measurement_unit', *CountRecipesMixin.list_display
    )
    search_fields = ('name__icontains', 'measurement_unit')
    list_filter = ('measurement_unit',)


class IngredientAmountInline(admin.TabularInline):
    model = IngredientAmount
    extra = 1
    fields = ('ingredient', 'amount', 'get_measurement_unit')
    readonly_fields = ('get_measurement_unit',)
    autocomplete_fields = ['ingredient']

    @admin.display(description='Единица измерения')
    def get_measurement_unit(self, obj):
        if obj.id:
            return obj.ingredient.measurement_unit
        ingredient_id = self.form.initial.get('ingredient')
        if ingredient_id:
            ingredient = Ingredient.objects.filter(id=ingredient_id).first()
            return ingredient.measurement_unit if ingredient else ''
        return ''


class RecipeAdmin(admin.ModelAdmin):
    inlines = [IngredientAmountInline]
    list_display = (
        'id', 'name', 'get_author_username',
        'cooking_time', 'get_ingredients',
        'get_tags', 'image_tag', 'count_favorites'
    )
    list_filter = ('tags', 'author__username',)
    search_fields = ('name__icontains', 'author__username__icontains')
    formfield_overrides = {
        models.ImageField: {
            'widget': forms.FileInput(attrs={'accept': 'image/*'})}
    }

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if obj and obj.image:
            form.base_fields['image'].help_text = mark_safe(
                f'<img src="{obj.image.url}" width="200" height="200" />')
        return form

    @admin.display(description='Изображение')
    def image_tag(self, recipe):
        if recipe.image:
            return mark_safe(
                f'<img src="{recipe.image.url}" width="50" height="50" />')
        return "Нет изображения"

    @admin.display(
        description='логин')
    def get_author_username(self, obj):
        return obj.author.username

    @admin.display(
        description='Ингредиенты',
        ordering='ingredients__name'
    )
    def get_ingredients(self, recipe):
        ingredients_list = [
            f'- {ing.ingredient.name} '
            f'({ing.amount} {ing.ingredient.measurement_unit})'
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
