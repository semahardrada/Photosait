from django.db import models
from gallery.models import Photo, Album
from django.contrib import admin
import os

class ProductFormat(models.Model):
    name = models.CharField(max_length=100, verbose_name="Название формата")
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Цена")
    is_collage = models.BooleanField(
        default=False, 
        verbose_name="Это Коллаж?", 
        help_text="Если галочка стоит, цена будет браться только 1 раз за весь заказ."
    )

    class Meta:
        verbose_name = "Формат продукции"
        verbose_name_plural = "Форматы продукции"

    def __str__(self):
        return f"{self.name} ({self.price} руб.)"


class Order(models.Model):
    STATUS_CHOICES = (
        ('new', 'Новый'),
        ('paid', 'Оплачен'),
        ('processing', 'В обработке'),
        ('completed', 'Завершен'),
    )
    first_name = models.CharField(max_length=100, verbose_name="Имя клиента")
    last_name = models.CharField(max_length=100, verbose_name="Фамилия клиента", blank=True)
    
    # === ИЗМЕНЕНИЕ: blank=True, null=True ===
    email = models.EmailField(verbose_name="Email", blank=True, null=True)
    phone = models.CharField(max_length=20, verbose_name="Телефон", blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new', verbose_name="Статус")
    receipt = models.FileField(upload_to='receipts/', blank=True, null=True, verbose_name="Квитанция об оплате")

    received_bonus = models.BooleanField(default=False, verbose_name="Бонус получен?")

    class Meta:
        verbose_name = "Заказ"
        verbose_name_plural = "Заказы"
        ordering = ['-created_at']

    def __str__(self):
        return f"Заказ #{self.id} от {self.first_name}"

    @admin.display(description='Клиент')
    def get_full_name(self):
        return f"{self.first_name} {self.last_name or ''}"
    
    @admin.display(description='Бонус?', boolean=True)
    def get_bonus_status(self):
        return self.received_bonus


class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE, verbose_name="Заказ")
    photo = models.ForeignKey(Photo, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Фотография")
    product_format = models.ForeignKey(ProductFormat, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Формат продукции")
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Цена")
    quantity = models.PositiveIntegerField(default=1, verbose_name="Количество")
    
    is_full_set = models.BooleanField(default=False, verbose_name="Весь комплект?")
    album_set = models.ForeignKey(Album, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Альбом (для комплекта)")

    class Meta:
        verbose_name = "Позиция заказа"
        verbose_name_plural = "Позиции заказа"

    def get_cost(self):
        return self.price * self.quantity

    @admin.display(description="Продукт")
    def get_product_name(self):
        if self.is_full_set and self.album_set:
            return f"Весь комплект '{self.album_set.title}'"
        if self.photo and self.product_format:
            return f"{self.product_format.name}"
        if self.photo:
            return "Фото (без формата)"
        return "Неизвестный товар"

    @admin.display(description="Имя файла")
    def get_file_name(self):
        if self.photo and self.photo.image:
            return os.path.basename(self.photo.image.name)
        return "N/A (Комплект)"

    @admin.display(description="Альбом")
    def get_album_title(self):
        if self.is_full_set and self.album_set:
            return self.album_set.title
        if self.photo and self.photo.album:
            return self.photo.album.title
        return "N/A"

    @admin.display(description="ID Заказа")
    def get_order_id(self):
        return self.order.id

    @admin.display(description="Клиент")
    def get_customer_name(self):
        return self.order.get_full_name()
    
    @admin.display(description="Email")
    def get_customer_email(self):
        return self.order.email or "-"

    @admin.display(description="Дата заказа")
    def get_order_date(self):
        return self.order.created_at

    @admin.display(description="Статус")
    def get_order_status(self):
        return self.order.get_status_display()

    @admin.display(description="Бонус?", boolean=True)
    def get_bonus_status(self):
        return self.order.received_bonus