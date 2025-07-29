from drf_extra_fields.fields import Base64ImageField
from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator
from users.models import Subscribe
from users.serializers import CustomUserSerializer

from .models import (Favorite, Ingredient, IngredientAmount, Recipe,
                     ShoppingCart, Tag)


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        fields = ('id', 'name', 'slug')
        model = Tag


class IngredientSerializer(serializers.ModelSerializer):
    class Meta:
        fields = ('id', 'name', 'measurement_unit')
        model = Ingredient


class IngredientAmountSerializer(serializers.ModelSerializer):
    id = serializers.ReadOnlyField(source='ingredient.id')
    name = serializers.ReadOnlyField(source='ingredient.name')
    measurement_unit = serializers.ReadOnlyField(
        source='ingredient.measurement_unit'
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
    author = CustomUserSerializer(read_only=True)
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
    id = serializers.SerializerMethodField()

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

    def get_id(self, obj):
        return f'{obj.id}'

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
        for ingredient in ingredients:
            IngredientAmount.objects.create(
                recipe=recipe,
                ingredient_id=ingredient.get('id'),
                amount=ingredient.get('amount'),
            )

    def validate_field(self, field, model):
        data = self.initial_data.get(field)
        if not data:
            raise serializers.ValidationError({
                f'{field}': f'Для рецепта нужен хотя бы один {field}'})

        item_set = set()
        for field_item in data:
            id = field_item if field == 'tags' else field_item.get('id')
            try:
                item = model.objects.get(id=id)
            except model.DoesNotExist:
                raise serializers.ValidationError({
                    f'{field}': f'Несуществующий {field} с ID {id}'
                })

            if item in item_set:
                raise serializers.ValidationError(f'{field} должны '
                                                  'быть уникальными')
            item_set.add(item)

            if field == 'ingredients' and int(field_item['amount']) <= 0:
                raise serializers.ValidationError({
                    'ingredients': ('Убедитесь, что значение количества '
                                    'ингредиента больше 0')
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
        recipe = Recipe.objects.create(**validated_data)
        recipe.tags.set(tags_data)
        self.create_ingredients(ingredients_data, recipe)
        return recipe

    def update(self, instance, validated_data):
        instance.name = validated_data.get('name', instance.name)
        instance.text = validated_data.get('text', instance.text)
        instance.cooking_time = validated_data.get(
            'cooking_time',
            instance.cooking_time
        )
        instance.image = validated_data.get('image', instance.image) or ""
        tags_data = self.validated_data.get('tags')
        instance.tags.set(tags_data)
        IngredientAmount.objects.filter(recipe=instance).all().delete()
        self.create_ingredients(validated_data.get('ingredients'), instance)
        instance.save()
        return instance


class FavoriteSerializer(serializers.ModelSerializer):
    id = serializers.ReadOnlyField(source='following.id')
    email = serializers.ReadOnlyField(source='following.email')
    username = serializers.ReadOnlyField(source='following.username')
    first_name = serializers.ReadOnlyField(source='following.first_name')
    last_name = serializers.ReadOnlyField(source='following.last_name')
    avatar = serializers.SerializerMethodField()
    is_subscribed = serializers.SerializerMethodField()
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.SerializerMethodField()

    class Meta:
        model = Subscribe
        fields = ('id', 'email', 'username', 'first_name', 'last_name',
                  'is_subscribed', 'recipes', 'recipes_count', 'avatar')

    def get_is_subscribed(self, obj):
        return Subscribe.objects.filter(
            follower=obj.follower,
            following=obj.following,
        ).exists()

    def get_recipes(self, obj):
        request = self.context.get('request')
        limit = request.GET.get('recipes_limit')
        queryset = Recipe.objects.filter(author=obj.following)
        if limit:
            queryset = queryset[:int(limit)]
        return CropRecipeSerializer(queryset, many=True).data

    def get_recipes_count(self, obj):
        return Recipe.objects.filter(author=obj.following).count()

    def get_avatar(self, obj):
        if obj.following.avatar:
            return obj.following.avatar.url
        return None


class ShoppingCartSerializer(serializers.ModelSerializer):
    id = serializers.ReadOnlyField(source='recipe.id')
    name = serializers.ReadOnlyField(source='recipe.name')
    image = serializers.SerializerMethodField()
    cooking_time = serializers.ReadOnlyField(source='recipe.cooking_time')

    class Meta:
        model = ShoppingCart
        fields = ('id', 'name', 'image', 'cooking_time')

    def get_image(self, obj):
        image = obj.recipe.image
        if image:
            return image.url
        return None


class CropRecipeSerializer(serializers.ModelSerializer):
    image = Base64ImageField()

    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')
        read_only_fields = ('id', 'name', 'image', 'cooking_time')
