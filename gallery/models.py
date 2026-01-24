from django.db import models
from django.core.exceptions import ValidationError
import uuid
from django.contrib import admin
from django.utils.html import format_html


class Album(models.Model):
    title = models.CharField(max_length=200, verbose_name="Название")
    description = models.TextField(blank=True, verbose_name="Описание")
    access_token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    expires_at = models.DateTimeField(blank=True, null=True, verbose_name="Дата и время окончания доступа")
    
    full_set_price = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        verbose_name="Цена за весь комплект",
        default=2500.00,
        editable=False
    )

    cover_image = models.ImageField(upload_to='album_covers/', blank=True, null=True, verbose_name="Обложка (необязательно)")
    
    # Поле родителя. limit_choices_to={'is_grouping': True} гарантирует,
    # что родителем может быть ТОЛЬКО папка, а не фото-альбом.
    parent = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sub_albums',
        verbose_name="Родительская папка",
        limit_choices_to={'is_grouping': True}
    )
    
    is_grouping = models.BooleanField(
        default=False,
        verbose_name="Это папка?",
        help_text="Если галочка стоит — это Папка (содержит другие альбомы). Если нет — это Альбом с фото."
    )

    class Meta:
        verbose_name = "Объект галереи"
        verbose_name_plural = "Все объекты"
        ordering = ['title']

    def __str__(self):
        return self.title

    def clean(self):
        # === ИЗМЕНЕНИЕ: УБРАЛ ЗАПРЕТ НА ВЛОЖЕННОСТЬ ===
        # Раньше здесь был код, запрещающий папке иметь родителя.
        # Теперь мы разрешаем папкам быть внутри папок.
        
        # Единственная проверка: нельзя стать родителем самому себе
        if self.parent == self:
             raise ValidationError('Объект не может быть родителем самому себе.')
             
        super().clean()

    @admin.display(description='Обложка')
    def cover_thumbnail(self):
        if self.cover_image:
            return format_html(f'<img src="{self.cover_image.url}" width="100">')
        return "Нет обложки"


# --- ПРОКСИ-МОДЕЛИ ---

class GroupingAlbum(Album):
    class Meta:
        proxy = True
        verbose_name = "Папка"
        verbose_name_plural = "Папки"


class PhotoAlbum(Album):
    class Meta:
        proxy = True
        verbose_name = "Альбом"
        verbose_name_plural = "Альбомы"


# --- МОДЕЛЬ ФОТО (без изменений) ---

class Photo(models.Model):
    album = models.ForeignKey(
        PhotoAlbum,
        related_name='photos',
        on_delete=models.CASCADE,
        verbose_name="Альбом",
        limit_choices_to={'is_grouping': False}
    )
    image = models.ImageField(upload_to='photos/originals/', verbose_name="Оригинальное фото")
    processed_image = models.ImageField(
        upload_to='photos/processed/',
        verbose_name="Обработанное фото (для показа)",
        blank=True,
        null=True,
        editable=False
    )
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата загрузки")

    class Meta:
        verbose_name = "Фотография"
        verbose_name_plural = "Фотографии"
        ordering = ['uploaded_at']

    def __str__(self):
        return f"Фото #{self.id} в альбоме '{self.album.title}'"



