from django.contrib.auth import get_user_model
from djoser.serializers import UserSerializer
from drf_extra_fields.fields import Base64ImageField
from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator

from ..recipes.models import (
    Favorite,
    Ingredient,
    IngredientAmount,
    Subscribe,
    Recipe,
    ShoppingCart,
    Tag
)

User = get_user_model()


class UserProfileSerializer(UserSerializer):
    is_subscribed = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = UserSerializer.Meta.fields + (
            'is_subscribed',
            'avatar',
        )

    def get_is_subscribed(self, user_profile):
        request = self.context.get('request')
        return bool(request and request.user and not request.user.is_anonymous
                    and Subscribe.objects.filter(
                        follower=request.user,
                        following=user_profile
                    ).exists())


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
        error_messages={
            'Продукт с таким id не существует.',
        }
    )
    name = serializers.ReadOnlyField(source='ingredient.name')
    measurement_unit = serializers.ReadOnlyField(
        source='ingredient.measurement_unit'
    )
    amount = serializers.IntegerField(
        min_value=1,
        max_value=10000,
        error_messages={
            'min_value': 'Количество не может быть меньше 1',
            'max_value': 'Количество не может превышать 10000',
            'invalid': 'Введите целое число'
        }
    )

    class Meta:
        model = IngredientAmount
        fields = ('id', 'name', 'measurement_unit', 'amount')
        validators = [
            UniqueTogetherValidator(
                queryset=IngredientAmount.objects.all(),
                fields=['ingredient', 'recipe']
            )
        ]


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
            'ingredients',
            'tags',
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
                f'{field}': f'Для рецепта нужен хотя бы один {field}'
            })

        item_set = set()
        duplicates = set()

        for field_item in data:
            id = field_item if field == 'tags' else field_item['id']

            if id in item_set:
                duplicates.add(str(id))
            item_set.add(id)

        if duplicates:
            raise serializers.ValidationError({
                field: f'Обнаружены дубликаты: {", ".join(duplicates)}'
            })

        return data

    def validate(self, data):
        image = self.initial_data.get('image')
        if not image:
            raise serializers.ValidationError(
                {'image': 'У рецепта должна быть картинка'}
            )
        data['ingredients'] = self.validate_field('ingredients', Ingredient)
        data['tags'] = self.validate_field('tags', Tag)
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
        instance = super().update(instance, validated_data)
        if tags_data is not None:
            instance.tags.set(tags_data)
        if ingredients_data is not None:
            instance.ingredient_amounts.all().delete()
            self.create_ingredients(ingredients_data, instance)

        return instance


class SubscribeSerializer(serializers.ModelSerializer):
    email = serializers.CharField(source='following.email', read_only=True)
    username = serializers.CharField(
        source='following.username', read_only=True)
    first_name = serializers.CharField(
        source='following.first_name', read_only=True)
    last_name = serializers.CharField(
        source='following.last_name', read_only=True)
    avatar = serializers.SerializerMethodField()
    is_subscribed = serializers.BooleanField(
        read_only=True, default=True)
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.IntegerField(
        source='following.recipes.count',
        read_only=True
    )

    class Meta:
        model = Subscribe
        fields = ('id', 'email', 'username', 'first_name', 'last_name',
                  'is_subscribed', 'recipes', 'recipes_count', 'avatar')

    def get_recipes(self, obj):
        queryset = obj.following.recipes.all()
        if 'recipes_limit' in self.context.get('request').GET:
            limit = int(self.context['request'].GET['recipes_limit'])
            queryset = queryset[:limit]
        return CropRecipeSerializer(queryset, many=True).data

    def get_avatar(self, obj):
        if obj.following.avatar:
            return obj.following.avatar.url
        return None


class RecipeShortSerializer(serializers.ModelSerializer):
    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')
        read_only_fields = fields

    image = serializers.ImageField(read_only=True, use_url=True)


class CropRecipeSerializer(serializers.ModelSerializer):

    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')
        read_only_fields = fields
