from django.db import models
import uuid
from django.core.files.base import ContentFile
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont, ImageOps
import os

# === 1. ГЛАВНАЯ ТАБЛИЦА (GROUPING ALBUM) ===
class GroupingAlbum(models.Model):
    title = models.CharField(max_length=200, verbose_name="Название папки")
    
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
        verbose_name = "Папка"
        verbose_name_plural = "Папки"


# === 2. ПРОКСИ-МОДЕЛЬ ДЛЯ АЛЬБОМОВ ===
class PhotoAlbum(GroupingAlbum):
    class Meta:
        proxy = True
        verbose_name = "Альбом с фото"
        verbose_name_plural = "Альбомы с фото"
    
    def save(self, *args, **kwargs):
        self.is_grouping = False
        super().save(*args, **kwargs)


# === 3. СЛУЖЕБНАЯ ПРОКСИ-МОДЕЛЬ ===
class Album(GroupingAlbum):
    class Meta:
        proxy = True
        verbose_name = "Все объекты (Служебное)"
        verbose_name_plural = "Все объекты (Служебное)"


# === 4. МОДЕЛЬ ФОТОГРАФИИ (С НОВОЙ ЗАЩИТОЙ) ===
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
        """
        Создает качественное превью с водяным знаком 'photowatermark' по всей площади.
        """
        try:
            # 1. Открываем и поворачиваем
            img = Image.open(self.image)
            img = ImageOps.exif_transpose(img) 

            if img.mode != 'RGB':
                img = img.convert('RGB')

            # 2. Ресайз (до 1500px)
            max_size = 1500
            ratio = min(max_size / img.width, max_size / img.height)
            if ratio < 1:
                new_size = (int(img.width * ratio), int(img.height * ratio))
                img = img.resize(new_size, Image.Resampling.LANCZOS)

            # 3. ПОДГОТОВКА ВОДЯНОГО ЗНАКА (СЕТКА)
            width, height = img.size
            
            # Создаем прозрачный слой для рисования
            overlay = Image.new('RGBA', img.size, (255, 255, 255, 0))
            draw = ImageDraw.Draw(overlay)
            
            text = "photowatermark"
            
            # Подбираем шрифт (покрупнее)
            font_size = int(width / 15) 
            try:
                font = ImageFont.truetype("arial.ttf", font_size)
            except IOError:
                font = ImageFont.load_default()

            # Вычисляем размер одного блока текста
            bbox = draw.textbbox((0, 0), text, font=font)
            text_w = bbox[2] - bbox[0]
            text_h = bbox[3] - bbox[1]
            
            # Отступы между надписями
            padding_x = text_w * 0.8
            padding_y = text_h * 2.5

            # Рисуем сетку текста
            # Мы идем циклом по всей ширине и высоте картинки
            y = 0
            while y < height:
                x = 0
                # Сдвигаем каждый второй ряд для "шахматного" порядка
                if int(y / padding_y) % 2 == 1:
                    x = int(padding_x / 2)
                
                while x < width:
                    # Рисуем текст (полупрозрачный белый)
                    draw.text((x, y), text, font=font, fill=(255, 255, 255, 70))
                    x += text_w + padding_x
                y += text_h + padding_y

            # Добавляем центральный крест (тонкий, но заметный)
            draw.line((0, 0) + img.size, fill=(255, 255, 255, 50), width=2)
            draw.line((0, height) + (width, 0), fill=(255, 255, 255, 50), width=2)

            # Накладываем слой
            watermarked = Image.alpha_composite(img.convert('RGBA'), overlay)
            watermarked = watermarked.convert('RGB')

            # 4. Сохраняем
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