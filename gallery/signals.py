from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Photo
from .utils import process_image_for_preview

@receiver(post_save, sender=Photo)
def photo_post_save(sender, instance, created, **kwargs):
    """
    Этот сигнал срабатывает ПОСЛЕ сохранения объекта Photo.
    Если фото только что создано и у него еще нет обработанной версии,
    запускаем функцию обработки.
    """
    if created and not instance.processed_image:
        process_image_for_preview(instance)