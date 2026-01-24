from PIL import Image, ImageDraw, ImageFont
from .models import Photo
from django.core.files.base import ContentFile
import io
import os
import math

def process_image_for_preview(photo_instance):
    """
    Принимает объект Photo, открывает его ОРИГИНАЛЬНОЕ изображение,
    ухудшает качество, накладывает диагональную вотермарку и сохраняет
    в поле processed_image.
    """
    if not photo_instance.image:
        return

    try:
        # Открываем оригинальное изображение
        original_image = Image.open(photo_instance.image).convert("RGBA")
    except Exception as e:
        print(f"Ошибка при открытии изображения для обработки: {e}")
        return

    # --- Сжимаем изображение ОДИН РАЗ в самом начале ---
    # quality=60 сделает изображение заметно хуже качеством и легче по весу.
    # Можешь изменять это значение от 1 (ужасно) до 95 (отлично).
    buffer = io.BytesIO()
    original_image.convert("RGB").save(buffer, format='JPEG', quality=60)
    buffer.seek(0)
    base_image = Image.open(buffer).convert("RGBA")
    width, height = base_image.size

    # --- НОВАЯ ЛОГИКА ДЛЯ ДИАГОНАЛЬНОЙ ВОТЕРМАРКИ ---

    # 1. Создаем прозрачный слой для текста вотермарки
    watermark_layer = Image.new('RGBA', base_image.size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(watermark_layer)

    # 2. Подбираем шрифт и текст
    text = "watermark"
    try:
        # Убедись, что шрифт Arial доступен в системе. Если нет, Pillow использует шрифт по умолчанию.
        font_size = int(width / 15)  # Размер шрифта зависит от ширины изображения
        font = ImageFont.truetype("arial.ttf", size=font_size)
    except IOError:
        font = ImageFont.load_default()

    # 3. Рассчитываем размеры текстового блока
    # Используем textbbox для более точного расчета
    left, top, right, bottom = draw.textbbox((0, 0), text, font=font)
    text_width = right - left
    text_height = bottom - top

    # 4. Создаем небольшое "полотно" для одного слова вотермарки, поворачиваем его
    # Добавляем отступы, чтобы текст не обрезался при повороте
    padding = 20
    text_image_size = (text_width + padding * 2, text_height + padding * 2)
    text_image = Image.new('RGBA', text_image_size, (255, 255, 255, 0))
    text_draw = ImageDraw.Draw(text_image)
    
    # Увеличиваем значение альфа-канала с 80 до 128 для большей яркости
    text_draw.text((padding, padding), text, font=font, fill=(255, 255, 255, 128))

    # Поворачиваем текст на 45 градусов
    rotated_text = text_image.rotate(45, expand=1)

    # 5. "Замостим" (tile) все изображение повернутым текстом
    # Шаг по x и y будет равен диагонали текстового блока для плотного прилегания
    step_x = int(math.sqrt(rotated_text.width**2 / 2)) + 20 # небольшой доп. отступ
    step_y = int(math.sqrt(rotated_text.height**2 / 2)) - 60 # небольшой доп. отступ

    for x in range(-rotated_text.width, width + rotated_text.width, step_x):
        for y in range(-rotated_text.height, height + rotated_text.height, step_y):
            watermark_layer.paste(rotated_text, (x, y), rotated_text)
    
    # 6. Накладываем слой с вотермарками на сжатое изображение
    final_image = Image.alpha_composite(base_image, watermark_layer)

    # --- СОХРАНЕНИЕ РЕЗУЛЬТАТА ---
    final_buffer = io.BytesIO()
    # Сохраняем итоговое изображение с качеством 85. Этого достаточно для превью.
    final_image.convert("RGB").save(final_buffer, format='JPEG', quality=85)

    original_filename = os.path.basename(photo_instance.image.name)
    processed_filename = f"preview_{original_filename}"

    # Сохраняем в поле processed_image, НЕ вызывая повторно сигнал save
    photo_instance.processed_image.save(
        processed_filename,
        ContentFile(final_buffer.getvalue()),
        save=False  # Важно! save=False, чтобы избежать бесконечного цикла
    )
    # Обновляем поле в базе данных одним вызовом update
    Photo.objects.filter(pk=photo_instance.pk).update(processed_image=photo_instance.processed_image)
