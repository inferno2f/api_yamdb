import uuid

from django.contrib.auth.models import AbstractUser
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from .validators import year_validator


ADMIN = 'admin'
MODERATOR = 'moderator'
USER = 'user'

ROLES = (
    (MODERATOR, 'moderator'),
    (USER, 'user'),
    (ADMIN, 'admin'),
)


class User(AbstractUser):
    bio = models.TextField('О пользователе', blank=True, null=True)
    role = models.CharField(
        'Права доступа', choices=ROLES, default=USER, max_length=10)
    confirmation_code = models.CharField(
        'Код подтверждения', max_length=36, default=uuid.uuid4)

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'
        ordering = ('id',)

    @property
    def is_admin(self):
        return self.role == 'admin' or self.is_superuser

    @property
    def is_moderator(self):
        return self.role == 'moderator' or self.is_superuser or self.is_admin

    def __str__(self) -> str:
        return self.username


class Genre(models.Model):
    name = models.CharField('Жанр', max_length=150, unique=True)
    slug = models.SlugField('Слаг', unique=True)

    class Meta:
        verbose_name = 'Жанр'
        verbose_name_plural = 'Жанры'
        ordering = ('id',)

    def __str__(self) -> str:
        return self.name


class Title(models.Model):
    name = models.CharField('Название', max_length=150)
    year = models.PositiveIntegerField(
        'Год выхода', validators=[year_validator])
    description = models.TextField('Описание', blank=True)
    genre = models.ManyToManyField(Genre, 'Жанр')
    category = models.ForeignKey(
        'Category', verbose_name='Категория', null=True,
        on_delete=models.SET_NULL)

    class Meta:
        verbose_name = 'Произведение'
        verbose_name_plural = 'Произведения'
        ordering = ('id',)

    def __str__(self) -> str:
        return self.name


class Review(models.Model):
    author = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='reviews',
        verbose_name='Автор')
    title = models.ForeignKey(
        'Title', on_delete=models.CASCADE, related_name='reviews',
        verbose_name='Произведение')
    text = models.TextField('Комментарий')
    score = models.PositiveIntegerField(
        'Оценка',
        validators=[
            MinValueValidator(
                1, 'You can rate a title on a scale from 1 to 10'),
            MaxValueValidator(
                10, 'You can rate a title on a scale from 1 to 10')])
    pub_date = models.DateTimeField('Дата публикации', auto_now_add=True)

    class Meta:
        verbose_name = 'Отзыв'
        verbose_name_plural = 'Отзывы'
        constraints = [
            models.UniqueConstraint(
                fields=('title', 'author'),
                name='unique_review'
            ),
        ]
        ordering = ('-pub_date',)


class Comment(models.Model):
    review = models.ForeignKey(
        Review, on_delete=models.CASCADE, related_name='comments',
        verbose_name='Отзыв')
    author = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='comments',
        verbose_name='Автор')
    text = models.TextField('Комментарий к отзыву')
    pub_date = models.DateTimeField('Дата публикации', auto_now_add=True)

    class Meta:
        verbose_name = 'Комментарий'
        verbose_name_plural = 'Комментарии'
        ordering = ('-pub_date',)

    def __str__(self) -> str:
        return self.text[:30]


class Category(models.Model):
    name = models.CharField('Категория', max_length=256, unique=True)
    slug = models.SlugField('Слаг', unique=True, max_length=50)

    class Meta:
        verbose_name = 'Категория'
        verbose_name_plural = 'Категории'
        ordering = ('id',)

    def __str__(self) -> str:
        return self.name
