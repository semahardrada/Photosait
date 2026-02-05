from django.db import models
import uuid
from django.core.files.base import ContentFile
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont, ImageOps
import os

# === 1. ОСНОВНАЯ МОДЕЛЬ (ЕДИНАЯ ТАБЛИЦА) ===
class GroupingAlbum(models.Model):
    title = models.CharField(max_length=200, verbose_name="Название папки")
    
    # Ссылка на саму себя для вложенности
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
    
    # Уникальный токен
    access_token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, verbose_name="Access Token")
    
    # Флаг типа: True = Папка, False = Альбом с фото
    is_grouping = models.BooleanField(default=True, editable=False)
    
    expires_at = models.DateTimeField(blank=True, null=True, verbose_name="Срок действия доступа")

    # Цена здесь, чтобы не было ошибок прокси
    full_set_price = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=2500.00, 
        verbose_name="Цена за весь комплект"
    )

    def __str__(self):
        return self.title
    
    class Meta:
        verbose_name = "Папка"
        verbose_name_plural = "Папки"


# === 2. ПРОКСИ-МОДЕЛЬ ДЛЯ АЛЬБОМОВ ===
class PhotoAlbum(GroupingAlbum):
    class Meta:
        proxy = True
        verbose_name = "Альбом с фото"
        verbose_name_plural = "Альбомы с фото"


# === 3. СЛУЖЕБНАЯ ПРОКСИ-МОДЕЛЬ ===
class Album(GroupingAlbum):
    class Meta:
        proxy = True
        verbose_name = "Все объекты (Служебное)"
        verbose_name_plural = "Все объекты (Служебное)"


# === 4. МОДЕЛЬ ФОТОГРАФИИ (С ЗАЩИТОЙ) ===
class Photo(models.Model):
    album = models.ForeignKey(
        'PhotoAlbum',
        related_name='photos',
        on_delete=models.CASCADE,
        verbose_name="Альбом",
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

            max_size = 1500
            ratio = min(max_size / img.width, max_size / img.height)
            if ratio < 1:
                new_size = (int(img.width * ratio), int(img.height * ratio))
                img = img.resize(new_size, Image.Resampling.LANCZOS)

            overlay = Image.new('RGBA', img.size, (255, 255, 255, 0))
            draw_overlay = ImageDraw.Draw(overlay)
            width, height = img.size

            draw_overlay.line((0, 0) + img.size, fill=(255, 255, 255, 80), width=3)
            draw_overlay.line((0, height) + (width, 0), fill=(255, 255, 255, 80), width=3)

            text = "ОБРАЗЕЦ • НЕ КОПИРОВАТЬ"
            font_size = int(width / 15)
            try:
                font = ImageFont.truetype("arial.ttf", font_size)
            except IOError:
                font = ImageFont.load_default()

            bbox = draw_overlay.textbbox((0, 0), text, font=font)
            text_w = bbox[2] - bbox[0]
            text_h = bbox[3] - bbox[1]
            x = (width - text_w) / 2
            y = (height - text_h) / 2

            draw_overlay.text((x, y), text, font=font, fill=(255, 255, 255, 120))
            draw_overlay.text((x, y - height/3), "PHOTO-STUDIO", font=font, fill=(255, 255, 255, 70))
            draw_overlay.text((x, y + height/3), "ЗАЩИЩЕНО", font=font, fill=(255, 255, 255, 70))

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