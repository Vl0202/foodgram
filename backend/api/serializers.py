from collections import Counter

from django.contrib.auth import get_user_model
from djoser.serializers import UserSerializer
from drf_extra_fields.fields import Base64ImageField
from recipes.constants import MIN_AMOUNT
from recipes.models import (Favorite, Ingredient, IngredientAmount, Recipe,
                            ShoppingCart, Subscribe, Tag, UserProfile)
from rest_framework import serializers

User = get_user_model()


class UserProfileSerializer(UserSerializer):
    is_subscribed = serializers.SerializerMethodField()

    class Meta:
        model = UserProfile
        fields = UserSerializer.Meta.fields + (
            'is_subscribed',
            'avatar',
        )

    def get_is_subscribed(self, user_profile):
        user = self.context.get('request').user
        if not user or user.is_anonymous:
            return False
        Subscribe.objects.filter(
            follower=user,
            following=user_profile.id
        ).exists()


class AvatarSerializer(UserProfileSerializer):
    class Meta:
        model = User
        fields = ('avatar', )


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        fields = ('id', 'name', 'slug')
        model = Tag


class IngredientSerializer(serializers.ModelSerializer):
    class Meta:
        fields = ('id', 'name', 'measurement_unit')
        model = Ingredient


class IngredientAmountSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source='ingredient.id')
    name = serializers.ReadOnlyField(source='ingredient.name')
    measurement_unit = serializers.ReadOnlyField(
        source='ingredient.measurement_unit'
    )
    amount = serializers.IntegerField(
        min_value=MIN_AMOUNT
    )

    class Meta:
        model = IngredientAmount
        fields = ('id', 'name', 'measurement_unit', 'amount')


class RecipeSerializer(serializers.ModelSerializer):
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()
    author = UserProfileSerializer(read_only=True)
    ingredients = IngredientAmountSerializer(
        source='recipe_amounts',
        many=True,
        read_only=True,
    )
    image = Base64ImageField()
    tags = TagSerializer(
        read_only=True,
        many=True,
    )

    class Meta:
        fields = (
            'id',
            'ingredients',
            'tags',
            'image',
            'text',
            'cooking_time',
            'author',
            'name',
            'is_favorited',
            'is_in_shopping_cart',
        )

        read_only_fields = (
            'author',
            'is_favorited',
            'is_in_shopping_cart'
        )
        model = Recipe

    def get_is_favorited(self, obj):
        request = self.context.get('request')
        return Favorite.objects.filter(
            user=request.user.id,
            recipe=obj,
        ).exists()

    def get_is_in_shopping_cart(self, obj):
        request = self.context.get('request')
        return ShoppingCart.objects.filter(
            user=request.user.id,
            recipe=obj,
        ).exists()

    def create_ingredients(self, ingredients, recipe):
        IngredientAmount.objects.bulk_create(
            IngredientAmount(
                recipe=recipe,
                ingredient_id=ingredient['id'],
                amount=ingredient['amount']
            )
            for ingredient in ingredients
        )

    def validate_field(self, field, model):
        data = self.initial_data.get(field)
        if not data:
            raise serializers.ValidationError({
                field: f'Для рецепта нужен хотя бы один {field}'
            })
        ids = [item if field == 'tags' else item.get('id') for item in data]
        duplicates = {id for id, count in Counter(ids).items() if count > 1}
        if duplicates:
            raise serializers.ValidationError({
                field: f'Обнаружены дубликаты: {duplicates}'
            })
        return data

    def validate(self, data):
        request = self.context.get('request')
        if request.method == 'POST' and not data.get('image'):
            raise serializers.ValidationError({
                'image': 'У рецепта должна быть картинка'
            })
        tags_data = self.validate_field('tags', Tag)
        data['tags'] = tags_data
        ingredients_data = self.validate_field('ingredients', Ingredient)
        data['ingredients'] = [
            {'id': item['id'], 'amount': item['amount']}
            for item in ingredients_data
        ]
        return data

    def create(self, validated_data):
        ingredients_data = validated_data.pop('ingredients')
        tags_data = validated_data.pop('tags')
        recipe = super().create(validated_data)
        recipe.tags.set(tags_data)
        self.create_ingredients(ingredients_data, recipe)
        return recipe

    def update(self, instance, validated_data):
        ingredients_data = validated_data.pop('ingredients', None)
        tags_data = validated_data.pop('tags', None)
        instance.tags.set(tags_data)
        instance.recipe_amounts.all().delete()
        self.create_ingredients(ingredients_data, instance)

        return super().update(instance, validated_data)


class SubscribedUserSerializer(UserProfileSerializer):
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.IntegerField(
        source='following.recipes.count',
        read_only=True
    )

    class Meta:
        model = UserProfile
        fields = UserProfileSerializer.Meta.fields + (
            'recipes', 'recipes_count')
        read_only_fields = fields

    def get_recipes(self, obj):
        recipes = Recipe.objects.filter(author=obj)
        if 'recipes_limit' in self.context.get('request').GET:
            limit = int(self.context['request'].GET['recipes_limit'])
            recipes = recipes[:limit]
        return RecipeShortSerializer(recipes, many=True).data


class RecipeShortSerializer(serializers.ModelSerializer):

    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')
        read_only_fields = fields
