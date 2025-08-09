from django.contrib.auth import get_user_model
from django.contrib.auth.models import AbstractUser
from django.core import validators
from django.core.validators import RegexValidator
from django.db import models

from .constants import MIN_AMOUNT, MIN_TIME


class UserProfile(AbstractUser):
    first_name = models.CharField('Имя', max_length=150, blank=True)
    last_name = models.CharField('Фамилия', max_length=150, blank=True)
    email = models.EmailField('Электронная почта', unique=True, max_length=254)
    username = models.CharField(
        'Логин',
        max_length=150,
        unique=True,
        validators=[RegexValidator(
            regex=r'^[\w.@+-]+$',
            message=(
                'Введите корректный никнейм. '
                'Это значение может содержать только '
                'буквы, цифры и символы @/./+/-/_'
            )
        )]
    )
    avatar = models.ImageField(
        upload_to='users/images/',
        default=None,
        verbose_name='Аватар',
    )

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name', 'username']

    class Meta:
        ordering = ['last_name', 'first_name']
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'


User = get_user_model()


class Subscribe(models.Model):
    follower = models.ForeignKey(
        User,
        verbose_name='Подписчик',
        related_name='followers',
        on_delete=models.CASCADE
    )

    following = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='autors',
        verbose_name='Автор',
    )

    class Meta:
        ordering = ['-following__id']
        verbose_name = 'Подписка'
        verbose_name_plural = 'Подписки'
        constraints = [
            models.UniqueConstraint(
                fields=['following', 'follower'],
                name='unique follow',
            ),
            models.CheckConstraint(
                check=~models.Q(following=models.F('follower')),
                name='no_self_subscription'
            )
        ]


class Tag(models.Model):
    name = models.CharField(max_length=32,
                            unique=True,
                            verbose_name="Название")
    slug = models.SlugField(unique=True,
                            max_length=32,
                            verbose_name="Слаг")

    class Meta:
        verbose_name = "Тег"
        verbose_name_plural = "Теги"
        ordering = ['name']

    def __str__(self):
        return self.name


class Ingredient(models.Model):
    name = models.CharField(max_length=128,
                            verbose_name="Название")
    measurement_unit = models.CharField(max_length=64,
                                        verbose_name="Единица измерения")

    class Meta:
        verbose_name = "Продукт"
        verbose_name_plural = "Продукты"
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(
                fields=['name', 'measurement_unit'],
                name='unique_ingredient_with_measurement'
            )
        ]

    def __str__(self):
        return self.name


class Recipe(models.Model):
    name = models.CharField(
        max_length=256,
        verbose_name="Название",
    )
    text = models.TextField(verbose_name="Описание")

    image = models.ImageField(
        upload_to='recipes/images/',
        verbose_name='Картинка',
    )
    author = models.ForeignKey(
        User,
        related_name='recipes',
        on_delete=models.CASCADE,
        verbose_name="Автор",
    )
    ingredients = models.ManyToManyField(
        Ingredient,
        related_name='recipes',
        through='IngredientAmount',
        verbose_name="Продукты",
    )
    cooking_time = models.PositiveIntegerField(
        verbose_name='Время приготовления',
        validators=[
            validators.MinValueValidator(
                MIN_TIME,
                message='Время приготовления не может '
                f'быть меньше {MIN_TIME} минуты'
            )
        ]
    )
    tags = models.ManyToManyField(
        Tag,
        related_name='recipes',
        verbose_name='Теги',
    )

    class Meta:
        ordering = ['name']
        verbose_name = "Рецепт"
        verbose_name_plural = "Рецепты"

    def __str__(self):
        return self.name


class IngredientAmount(models.Model):
    ingredient = models.ForeignKey(
        Ingredient,
        on_delete=models.CASCADE,
        related_name='recipe_amounts',
        verbose_name='Продукт',
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name='recipe_amounts',
        verbose_name='Рецепт',
    )
    amount = models.PositiveSmallIntegerField(
        validators=(
            validators.MinValueValidator(
                MIN_AMOUNT,
                message=f'Минимальное количество продуктов {MIN_AMOUNT}'),
        ),
        verbose_name='Количество',
    )

    class Meta:
        ordering = ['-id']
        verbose_name = 'Количество продукта'
        verbose_name_plural = 'Количество продуктов'
        constraints = [
            models.UniqueConstraint(fields=['ingredient', 'recipe'],
                                    name='unique ingredients recipe',)
        ]


class RecipeUserRelation(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name='Пользователь',
        related_name='%(class)s_set',
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        rrelated_name='%(class)s_set',
        verbose_name='Рецепт',
    )

    class Meta:
        abstract = True
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'recipe'],
                name='unique_user_%(class)s_recipe'
            )
        ]

    def __str__(self):
        return f'{self.user} → {self.recipe} ({self._meta.verbose_name})'


class Favorite(RecipeUserRelation):
    class Meta (RecipeUserRelation.Meta):
        verbose_name = 'Избранное'
        verbose_name_plural = 'Избранные'


class ShoppingCart(RecipeUserRelation):
    class Meta (RecipeUserRelation.Meta):
        verbose_name = 'Список покупок'
        verbose_name_plural = 'Списки покупок'
