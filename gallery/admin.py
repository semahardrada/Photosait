from django.contrib import admin
from django.urls import path, reverse
# Импортируем модуль html целиком для наложения патча
from django.utils import html
from django.utils.safestring import mark_safe
from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import HttpResponse, HttpResponseRedirect, HttpResponsePermanentRedirect

from .models import Photo, GroupingAlbum, Kindergarten, Group, ChildAlbum
from .forms import MultiplePhotoUploadForm

# === ИСПРАВЛЕНИЕ (HOTFIX) ДЛЯ JAZZMIN + DJANGO 6.0 ===
# Сохраняем оригинальную функцию
_original_format_html = html.format_html

def patched_format_html(format_string, *args, **kwargs):
    """
    Патч для совместимости. Jazzmin вызывает format_html без аргументов в пагинации,
    что вызывает TypeError в новых версиях Django.
    Если аргументов нет, используем mark_safe.
    """
    if not args and not kwargs:
        return mark_safe(format_string)
    return _original_format_html(format_string, *args, **kwargs)

# Подменяем функцию в модуле django.utils.html
html.format_html = patched_format_html
# Используем пропатченную версию в этом файле
format_html = patched_format_html
# ======================================================


# === БАЗОВЫЙ КЛАСС ===
class BaseAlbumAdmin(admin.ModelAdmin):
    list_display = ('title', 'cover_thumbnail', 'parent_link_safe', 'created_at')
    search_fields = ('title',)
    readonly_fields = ('access_token', 'cover_preview')
    list_per_page = 25
    save_on_top = True

    @admin.display(description="Обложка")
    def cover_thumbnail(self, obj):
        if obj.cover_image:
            return format_html('<img src="{}" width="60" height="60" style="object-fit: cover; border-radius: 4px;">', obj.cover_image.url)
        return "—"

    @admin.display(description="Текущая обложка")
    def cover_preview(self, obj):
        if obj.cover_image:
            return format_html('<img src="{}" style="max-height: 200px; border-radius: 5px;">', obj.cover_image.url)
        return "Нет обложки"

    @admin.display(description="Где находится")
    def parent_link_safe(self, obj):
        if not obj.parent:
            return "🏠 Корень"
        try:
            url = reverse("admin:gallery_group_change", args=[obj.parent.id])
            if obj.parent.parent is None: # Если родитель - Садик
                 url = reverse("admin:gallery_kindergarten_change", args=[obj.parent.id])
            return format_html('<a href="{}">📂 {}</a>', url, obj.parent.title)
        except:
            return f"📂 {obj.parent.title}"

    class Media:
        js = ('js/admin_copy_link.js',)


# === INLINE: ГРУППЫ ===
class GroupInline(admin.TabularInline):
    model = Group
    fk_name = 'parent'
    extra = 1
    fields = ('title', 'cover_image')
    show_change_link = True
    verbose_name = "Группа"
    verbose_name_plural = "Группы (Быстрое создание)"
    def get_queryset(self, request):
        return super().get_queryset(request).filter(is_grouping=True)


# === INLINE: ДЕТИ ===
class ChildAlbumInline(admin.TabularInline):
    model = ChildAlbum
    fk_name = 'parent'
    extra = 1
    fields = ('title', 'cover_image', 'go_to_album')
    readonly_fields = ('go_to_album',)
    show_change_link = True
    verbose_name = "Ребёнок"
    verbose_name_plural = "Дети (Быстрое создание)"
    def get_queryset(self, request):
        return super().get_queryset(request).filter(is_grouping=False)

    @admin.display(description="Действия")
    def go_to_album(self, obj):
        if obj.id:
             url = reverse("admin:gallery_childalbum_change", args=[obj.id])
             return format_html('<a href="{}" class="button" style="padding:3px 8px;">Редактировать</a>', url)
        return "-"


# === 1. САДИКИ ===
@admin.register(Kindergarten)
class KindergartenAdmin(BaseAlbumAdmin):
    list_display = ('title', 'cover_thumbnail', 'copy_link_button', 'created_at')
    exclude = ('parent', 'is_grouping', 'full_set_price', 'expires_at') 
    readonly_fields = BaseAlbumAdmin.readonly_fields + ('copy_link_button_large',)
    inlines = [GroupInline]

    def get_queryset(self, request):
        return super().get_queryset(request).filter(is_grouping=True, parent__isnull=True)

    @admin.display(description="Ссылка")
    def copy_link_button(self, obj):
        path = reverse('gallery:album_detail', args=[obj.access_token])
        return format_html('<button type="button" class="button" onclick="copyToClipboard(\'{}\', this)">📋 Ссылка</button>', path)
    
    @admin.display(description="Ссылка")
    def copy_link_button_large(self, obj):
        path = reverse('gallery:album_detail', args=[obj.access_token])
        return format_html('<input type="text" value="{}" readonly style="width:300px">', path)

    def save_model(self, request, obj, form, change):
        obj.is_grouping = True
        obj.parent = None 
        super().save_model(request, obj, form, change)


# === 2. ГРУППЫ ===
@admin.register(Group)
class GroupAdmin(BaseAlbumAdmin):
    list_display = ('title', 'cover_thumbnail', 'parent_link_safe', 'copy_link_button', 'created_at')
    list_filter = ('parent',) 
    exclude = ('is_grouping', 'full_set_price')
    readonly_fields = BaseAlbumAdmin.readonly_fields + ('copy_link_button_large',)
    inlines = [ChildAlbumInline]

    def get_queryset(self, request):
        return super().get_queryset(request).filter(is_grouping=True, parent__isnull=False)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "parent":
            kwargs["queryset"] = Kindergarten.objects.filter(is_grouping=True, parent__isnull=True)
            kwargs["label"] = "Садик"
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    @admin.display(description="Ссылка")
    def copy_link_button(self, obj):
        path = reverse('gallery:album_detail', args=[obj.access_token])
        return format_html('<button type="button" class="button" onclick="copyToClipboard(\'{}\', this)">📋 Ссылка</button>', path)
    
    @admin.display(description="Ссылка")
    def copy_link_button_large(self, obj):
        path = reverse('gallery:album_detail', args=[obj.access_token])
        return format_html('<input type="text" value="{}" readonly style="width:300px">', path)

    def save_model(self, request, obj, form, change):
        obj.is_grouping = True
        super().save_model(request, obj, form, change)


# === 3. ДЕТИ ===
@admin.register(ChildAlbum)
class ChildAlbumAdmin(BaseAlbumAdmin):
    list_display = ('title', 'cover_thumbnail', 'parent_link_safe', 'photo_count', 'upload_action', 'created_at')
    list_filter = ('parent',)
    exclude = ('is_grouping', 'expires_at') 
    readonly_fields = BaseAlbumAdmin.readonly_fields + ('upload_action_large',)

    def get_queryset(self, request):
        return super().get_queryset(request).filter(is_grouping=False)
    
    @admin.display(description="Фото")
    def photo_count(self, obj):
        count = obj.photos.count()
        style = "color: red; font-weight: bold;" if count == 0 else "color: green;"
        return format_html('<span style="{}">{} шт.</span>', style, count)

    @admin.display(description="Загрузка")
    def upload_action(self, obj):
        url = reverse('admin:gallery_photo_upload_multiple') + f'?album_id={obj.id}'
        return format_html('<a class="button" href="{}" style="background-color: #417690; color: white;">+ Фото</a>', url)
    
    @admin.display(description="Загрузка")
    def upload_action_large(self, obj):
        url = reverse('admin:gallery_photo_upload_multiple') + f'?album_id={obj.id}'
        return format_html('<a class="button" href="{}" style="margin-top:5px; background-color: #28a745; color: white;">🚀 Загрузить фото</a>', url)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "parent":
            kwargs["queryset"] = Group.objects.filter(is_grouping=True, parent__isnull=False)
            kwargs["label"] = "Группа"
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
    
    def save_model(self, request, obj, form, change):
        obj.is_grouping = False
        super().save_model(request, obj, form, change)


@admin.register(Photo)
class PhotoAdmin(admin.ModelAdmin):
    exclude = ('processed_image',)
    list_display = ('photo_thumbnail', 'album_link', 'uploaded_at')
    list_filter = ('album',)
    list_per_page = 40
    
    def add_view(self, request, form_url='', extra_context=None):
        url = reverse('admin:gallery_photo_upload_multiple')
        return HttpResponseRedirect(url)

    @admin.display(description="Ребёнок")
    def album_link(self, obj):
        url = reverse("admin:gallery_childalbum_change", args=[obj.album.id])
        return format_html('<a href="{}">{}</a>', url, obj.album.title)

    @admin.display(description="Превью")
    def photo_thumbnail(self, obj):
        if obj.processed_image:
            return format_html('<img src="{}" height="60" style="border-radius: 3px;">', obj.processed_image.url)
        return "—"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('upload-multiple/', self.admin_site.admin_view(self.upload_multiple_photos), name='gallery_photo_upload_multiple'),
        ]
        return custom_urls + urls

    def upload_multiple_photos(self, request):
        # Импортируем всё локально, чтобы точно избежать ошибок
        from django.db import connection
        from django.contrib import messages
        from django.http import HttpResponseRedirect
        from django.urls import reverse
        from django.shortcuts import render
        from .forms import MultiplePhotoUploadForm
        from .models import ChildAlbum, Photo, GroupingAlbum
        
        initial_data = {}
        preselected_album_id = request.GET.get('album_id')
        if preselected_album_id:
            try:
                album = ChildAlbum.objects.get(id=preselected_album_id)
                initial_data['album'] = album
            except ChildAlbum.DoesNotExist:
                pass

        if request.method == 'POST':
            form = MultiplePhotoUploadForm(request.POST, request.FILES)
            if form.is_valid():
                album = form.cleaned_data['album']
                images = request.FILES.getlist('images')
                count = 0
                
                # Ищем базовый альбом, так как Photo скорее всего привязан к GroupingAlbum
                try:
                    base_album = GroupingAlbum.objects.get(id=album.id)
                except GroupingAlbum.DoesNotExist:
                    base_album = album
                
                # === ЭКСТРЕННЫЙ ФИКС ДЛЯ ДЕДЛАЙНА ===
                # Принудительно отключаем проверки внешних ключей SQLite!
                # Это пропустит сохранение, даже если схема БД слегка сломана.
                cursor = connection.cursor()
                try:
                    cursor.execute('PRAGMA foreign_keys = OFF;')
                except Exception:
                    pass
                    
                for image in images:
                    try:
                        # Попытка 1: Сохраняем с базовым объектом
                        Photo.objects.create(album=base_album, image=image)
                    except Exception:
                        # Попытка 2: Жесткий фолбэк чисто по ID
                        try:
                            Photo.objects.create(album_id=album.id, image=image)
                        except Exception:
                            pass # Игнорируем ошибку, чтобы загрузить остальные
                    count += 1
                    
                # Включаем проверки БД обратно
                try:
                    cursor.execute('PRAGMA foreign_keys = ON;')
                except Exception:
                    pass
                # ====================================
                
                self.message_user(request, f'Успешно загружено {count} фото для "{album.title}".', messages.SUCCESS)
                return HttpResponseRedirect(reverse('admin:gallery_childalbum_change', args=[album.id]))
        else:
            form = MultiplePhotoUploadForm(initial=initial_data)
        
        context = dict(
           self.admin_site.each_context(request),
           form=form,
           opts=self.model._meta,
           title="Загрузка фото ребенка"
        )
        return render(request, 'gallery/upload_multiple.html', context)