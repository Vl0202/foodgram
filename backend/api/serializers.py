import base64
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
        return Subscribe.objects.filter(
            follower=user, following=user_profile.id)\
            .exists()


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
    id = serializers.PrimaryKeyRelatedField(
        queryset=Ingredient.objects.all(),
        source='ingredient',
    )
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
        source='ingredientamount_set',
        many=True,
        read_only=True,
    )
    image = Base64ImageField()
    tags = TagSerializer(
        read_only=True,
        many=True
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
        ingredient_amounts = [
            IngredientAmount(
                recipe=recipe,
                ingredient_id=ingredient['id'],
                amount=ingredient['amount']
            )
            for ingredient in ingredients
        ]
        IngredientAmount.objects.bulk_create(ingredient_amounts)

    def validate_field(self, field, model):
        data = self.initial_data.get(field)
        if not data:
            raise serializers.ValidationError({
                field: f'Для рецепта нужен хотя бы один {field}'
            })

        ids = [item if field == 'tags' else item['id'] for item in data]
        duplicates = {id for id, count in Counter(ids).items() if count > 1}

        if duplicates:
            raise serializers.ValidationError({
                field: f'Обнаружены дубликаты: {duplicates}'
            })

    def validate(self, data):
        if self.context['request'].method == 'POST':
            raise serializers.ValidationError(
                {'image': 'У рецепта должна быть картинка'}
            )
        data['ingredients'] = self.validate_field('ingredients', Ingredient)
        data['tags'] = self.validate_field('tags', Tag)
        return data

    def create(self, validated_data):
        ingredients_data = validated_data.pop('ingredients', [])
        tags_data = validated_data.pop('tags', [])
        recipe = super().create(validated_data)
        if tags_data:
            recipe.tags.set(tags_data)
        if ingredients_data:
            self.create_ingredients(ingredients_data, recipe)
        return recipe

    def update(self, instance, validated_data):
        instance = super().update(instance, validated_data)
        if 'tags' in self.initial_data:
            tags_data = self.validate_field('tags', Tag)
            instance.tags.set(tags_data)
        if 'ingredients' in self.initial_data:
            ingredients_data = self.validate_field('ingredients', Ingredient)
            instance.recipe_amounts.all().delete()
            self.create_ingredients(ingredients_data, instance)
        return instance


class SubscribedUserSerializer(serializers.ModelSerializer):
    id = serializers.ReadOnlyField(source='following.id')
    email = serializers.ReadOnlyField(source='following.email')
    username = serializers.ReadOnlyField(source='following.username')
    first_name = serializers.ReadOnlyField(source='following.first_name')
    last_name = serializers.ReadOnlyField(source='following.last_name')
    avatar = serializers.SerializerMethodField()
    is_subscribed = serializers.SerializerMethodField()
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.IntegerField(
        source='following.recipes.count',
        read_only=True
    )

    class Meta:
        model = Subscribe
        fields = ('id', 'email', 'username', 'first_name', 'last_name',
                  'is_subscribed', 'recipes', 'recipes_count', 'avatar')
        read_only_fields = fields

    def get_is_subscribed(self, obj):
        return Subscribe.objects.filter(
            follower=obj.follower,
            following=obj.following,
        ).exists()

    def get_recipes(self, obj):
        recipes = Recipe.objects.filter(author=obj.following)
        if 'recipes_limit' in self.context.get('request').GET:
            limit = int(self.context['request'].GET['recipes_limit'])
            recipes = recipes[:limit]
        return RecipeShortSerializer(recipes, many=True).data

    def get_recipes_count(self, obj):
        return Recipe.objects.filter(author=obj.following).count()

    def get_avatar(self, obj):
        if obj.following.avatar:
            return obj.following.avatar.url
        return None


class RecipeShortSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')
        read_only_fields = fields

    def get_image(self, obj):
        if obj.image:
            return base64.b64encode(obj.image.read()).decode('utf-8')
        return None
