from django.db import models
import uuid
from django.core.files.base import ContentFile
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont, ImageOps
import os

# === 1. БАЗОВАЯ МОДЕЛЬ (ОБЩАЯ ДЛЯ ВСЕХ ПАПОК) ===
class GroupingAlbum(models.Model):
    title = models.CharField(max_length=200, verbose_name="Название")
    
    # Родительская папка
    parent = models.ForeignKey(
        'self', 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True, 
        related_name='sub_albums', 
        verbose_name="Родительская папка",
        limit_choices_to={'is_grouping': True} 
    )
    cover_image = models.ImageField(upload_to='album_covers/', blank=True, null=True, verbose_name="Обложка")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    
    access_token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, verbose_name="Access Token")
    
    # True = Это папка (Садик или Группа), False = Это конечный альбом (Ребенок)
    is_grouping = models.BooleanField(default=True, editable=False)
    
    expires_at = models.DateTimeField(blank=True, null=True, verbose_name="Срок действия доступа")

    full_set_price = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=2500.00, 
        verbose_name="Цена за весь комплект"
    )

    def __str__(self):
        return self.title
    
    class Meta:
        verbose_name = "Папка (Общая)"
        verbose_name_plural = "Папки (Общие)"


# === 2. ПРОКСИ: САДИК (Корневая папка) ===
class Kindergarten(GroupingAlbum):
    class Meta:
        proxy = True
        verbose_name = "Садик"
        verbose_name_plural = "1. Садики"

# === 3. ПРОКСИ: ГРУППА (Вложенная папка) ===
class Group(GroupingAlbum):
    class Meta:
        proxy = True
        verbose_name = "Группа"
        verbose_name_plural = "2. Группы"

# === 4. ПРОКСИ: РЕБЁНОК (Альбом с фото) ===
class ChildAlbum(GroupingAlbum):
    class Meta:
        proxy = True
        verbose_name = "Ребёнок (Альбом)"
        verbose_name_plural = "3. Дети (Альбомы)"
    
    def save(self, *args, **kwargs):
        self.is_grouping = False # Это конечный альбом, в нем лежат фото
        super().save(*args, **kwargs)

# === 5. СЛУЖЕБНАЯ ПРОКСИ (Для совместимости) ===
class Album(GroupingAlbum):
    class Meta:
        proxy = True
        verbose_name = "Все объекты (Служебное)"
        verbose_name_plural = "Все объекты (Служебное)"
# Для совместимости со старыми ссылками
PhotoAlbum = ChildAlbum 


# === 6. МОДЕЛЬ ФОТОГРАФИИ ===
class Photo(models.Model):
    album = models.ForeignKey(
        'ChildAlbum', # Ссылаемся на ребенка
        related_name='photos',
        on_delete=models.CASCADE,
        verbose_name="Ребёнок",
        limit_choices_to={'is_grouping': False}
    )
    image = models.ImageField(upload_to='photos/originals/', verbose_name="Оригинальное фото")
    
    processed_image = models.ImageField(
        upload_to='photos/processed/',
        verbose_name="Превью (с водяным знаком)",
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
        return f"Фото #{self.id}"

    def save(self, *args, **kwargs):
        if self.image:
            if not self.processed_image:
                self.create_watermarked_thumbnail()
        super().save(*args, **kwargs)

    def create_watermarked_thumbnail(self):
        try:
            img = Image.open(self.image)
            img = ImageOps.exif_transpose(img) 

            if img.mode != 'RGB':
                img = img.convert('RGB')

            # Ресайз
            max_size = 1500
            ratio = min(max_size / img.width, max_size / img.height)
            if ratio < 1:
                new_size = (int(img.width * ratio), int(img.height * ratio))
                img = img.resize(new_size, Image.Resampling.LANCZOS)

            # Водяной знак
            overlay = Image.new('RGBA', img.size, (255, 255, 255, 0))
            draw = ImageDraw.Draw(overlay)
            width, height = img.size
            
            text = "photowatermark"
            font_size = int(width / 15)
            try: font = ImageFont.truetype("arial.ttf", font_size)
            except IOError: font = ImageFont.load_default()

            bbox = draw.textbbox((0, 0), text, font=font)
            text_w = bbox[2] - bbox[0]
            text_h = bbox[3] - bbox[1]
            padding_x = text_w * 0.8
            padding_y = text_h * 2.5

            y = 0
            while y < height:
                x = 0
                if int(y / padding_y) % 2 == 1: x = int(padding_x / 2)
                while x < width:
                    draw.text((x, y), text, font=font, fill=(255, 255, 255, 70))
                    x += text_w + padding_x
                y += text_h + padding_y

            # Крест
            draw.line((0, 0) + img.size, fill=(255, 255, 255, 50), width=2)
            draw.line((0, height) + (width, 0), fill=(255, 255, 255, 50), width=2)

            watermarked = Image.alpha_composite(img.convert('RGBA'), overlay)
            watermarked = watermarked.convert('RGB')

            thumb_io = BytesIO()
            watermarked.save(thumb_io, format='JPEG', quality=95, subsampling=0)

            file_name = os.path.basename(self.image.name)
            self.processed_image.save(
                f"watermarked_{file_name}",
                ContentFile(thumb_io.getvalue()),
                save=False
            )
        except Exception as e:
            print(f"Ошибка обработки фото {self.id}: {e}")
            pass