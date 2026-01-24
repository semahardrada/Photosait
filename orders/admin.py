import openpyxl
from django.contrib import admin
from django.http import HttpResponse
from .models import Order, OrderItem, ProductFormat
from gallery.models import Album
import os

class AlbumFilter(admin.SimpleListFilter):
    title = 'Альбом'
    parameter_name = 'album'

    def lookups(self, request, model_admin):
        albums = Album.objects.filter(is_grouping=False)
        return [(a.id, a.title) for a in albums]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(
                items__photo__album__id=self.value()
            ).distinct()
        return queryset

@admin.action(description='Экспорт выбранных заказов в Excel')
def export_to_excel(modeladmin, request, queryset):
    opts = modeladmin.model._meta
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename={opts.verbose_name_plural}.xlsx'
    
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Заказы"

    headers = [
        "ID Заказа", "Клиент", "Email", "Телефон", "Дата заказа", "Статус", 
        "Бонус?", "Продукт", "Альбом", "Имя файла", "Кол-во", "Сумма"
    ]
    ws.append(headers)

    orders = queryset.prefetch_related(
        'items__photo__album', 
        'items__product_format', 
        'items__album_set'
    )

    for order in orders:
        for item in order.items.all():
            row = [
                order.id,
                order.get_full_name(),
                order.email,
                order.phone,
                order.created_at.strftime('%Y-%m-%d %H:%M'),
                order.get_status_display(),
                "Да" if order.get_bonus_status() else "Нет",
                item.get_product_name(),
                item.get_album_title(),
                item.get_file_name(),
                item.quantity,
                item.get_cost()
            ]
            ws.append(row)
    
    wb.save(response)
    return response

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    raw_id_fields = ['photo']
    extra = 0
    fields = ('get_product_name', 'quantity', 'price')
    readonly_fields = ('get_product_name', 'price')

    def get_product_name(self, obj):
        return obj.get_product_name()
    get_product_name.short_description = 'Продукт'

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'get_full_name', 'email', 'status', 
        'get_bonus_status',
        'created_at', 
        'get_photo_count', 'get_albums_list'
    )
    list_filter = (AlbumFilter, 'status', 'created_at', 'received_bonus')
    search_fields = ['id', 'first_name', 'last_name', 'email', 'phone'] 
    inlines = [OrderItemInline]
    actions = [export_to_excel]

    @admin.display(description='Кол-во фото')
    def get_photo_count(self, obj):
        count = 0
        for item in obj.items.all():
            if item.is_full_set and item.album_set:
                count += item.album_set.photos.count()
            elif item.photo:
                count += item.quantity
        return count

    @admin.display(description='Альбомы в заказе')
    def get_albums_list(self, obj):
        album_ids = set()
        for item in obj.items.all():
            if item.is_full_set and item.album_set:
                album_ids.add(item.album_set.id)
            elif item.photo and item.photo.album:
                album_ids.add(item.photo.album.id)
        
        albums = Album.objects.filter(id__in=album_ids)
        if not albums:
            return "N/A"
        return ", ".join([a.title for a in albums])

@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = (
        'get_order_id',
        'get_customer_name',
        'get_customer_email',
        'get_order_date',
        'get_order_status',
        'get_bonus_status',
        'get_album_title',
        'get_file_name',
        'get_product_name',
        'quantity',
        'price'
    )
    list_filter = (
        'order__status', 
        'order__created_at', 
        'order__received_bonus',
        'product_format',
        'photo__album'
    )
    search_fields = (
        'order__id',
        'order__first_name',
        'order__last_name',
        'order__email',
        'photo__image'
    )
    
    def has_add_permission(self, request):
        return False
    def has_change_permission(self, request, obj=None):
        return False
    def has_delete_permission(self, request, obj=None):
        return False

@admin.register(ProductFormat)
class ProductFormatAdmin(admin.ModelAdmin):
    # Добавили 'is_collage' в отображение
    list_display = ('name', 'price', 'is_collage')
    list_filter = ('is_collage',)
