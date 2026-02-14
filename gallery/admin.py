from django.contrib import admin
from django.urls import path, reverse
from django.utils.html import format_html
from django.http import HttpResponseRedirect
from django.shortcuts import render, redirect  # <--- ВЕРНУЛ ЭТОТ ИМПОРТ
from django.contrib import messages            # <--- ВЕРНУЛ ЭТОТ ИМПОРТ

# Импортируем все модели, включая новые прокси
from .models import Photo, GroupingAlbum, Kindergarten, Group, ChildAlbum
from .forms import MultiplePhotoUploadForm

# === БАЗОВЫЙ КЛАСС (Общие настройки для всех папок) ===
class BaseAlbumAdmin(admin.ModelAdmin):
    list_display = ('title', 'cover_thumbnail', 'parent_link', 'created_at')
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

    @admin.display(description="Где находится", ordering='parent')
    def parent_link(self, obj):
        if obj.parent:
            # Ссылка ведет на общую форму редактирования
            url = reverse("admin:gallery_groupingalbum_change", args=[obj.parent.id])
            return format_html('<a href="{}">📂 {}</a>', url, obj.parent.title)
        return "🏠 Корень (Садик)"

    class Media:
        js = ('js/admin_copy_link.js',)


# === INLINES (Чтобы видеть детей внутри группы) ===
class PhotoAlbumInline(admin.TabularInline):
    model = ChildAlbum
    fk_name = 'parent'
    extra = 1
    fields = ('title', 'cover_image', 'go_to_album')
    readonly_fields = ('go_to_album',)
    show_change_link = True
    verbose_name = "Ребёнок"
    verbose_name_plural = "Дети (Быстрое добавление)"

    def get_queryset(self, request):
        return super().get_queryset(request).filter(is_grouping=False)

    @admin.display(description="Действия")
    def go_to_album(self, obj):
        if obj.id:
             url = reverse("admin:gallery_childalbum_change", args=[obj.id])
             return format_html('<a href="{}" class="button" style="padding:3px 8px;">Редактировать</a>', url)
        return "-"


# === 1. САДИКИ (КОРЕНЬ) ===
@admin.register(Kindergarten)
class KindergartenAdmin(BaseAlbumAdmin):
    list_display = ('title', 'cover_thumbnail', 'copy_link_button', 'created_at')
    # Садик не имеет родителя, поэтому скрываем parent
    exclude = ('parent', 'is_grouping', 'full_set_price', 'expires_at') 
    readonly_fields = BaseAlbumAdmin.readonly_fields + ('copy_link_button_large',)

    def get_queryset(self, request):
        # Показываем только корневые папки (Садики)
        return super().get_queryset(request).filter(is_grouping=True, parent__isnull=True)

    @admin.display(description="Ссылка для родителей")
    def copy_link_button(self, obj):
        path = reverse('gallery:album_detail', args=[obj.access_token])
        return format_html(
            '''<button type="button" class="button" onclick="copyToClipboard('{}', this)" style="background-color: #f0f0f0; border: 1px solid #ccc; border-radius: 4px;">📋 Скопировать</button>''',
            path
        )
    
    @admin.display(description="Ссылка на Садик")
    def copy_link_button_large(self, obj):
        path = reverse('gallery:album_detail', args=[obj.access_token])
        return format_html(
            '''<div style="display: flex; gap: 10px; align-items: center;"><input type="text" value="{}" readonly style="width: 350px; padding: 6px;"><button type="button" class="button" onclick="copyToClipboard('{}', this)" style="background-color: #28a745; color: white;">📋 Скопировать ссылку</button></div>''',
            path, path
        )

    def save_model(self, request, obj, form, change):
        obj.is_grouping = True
        obj.parent = None # Садик всегда корень
        super().save_model(request, obj, form, change)


# === 2. ГРУППЫ (ВНУТРИ САДИКОВ) ===
@admin.register(Group)
class GroupAdmin(BaseAlbumAdmin):
    list_display = ('title', 'cover_thumbnail', 'parent_link', 'copy_link_button', 'created_at')
    list_filter = ('parent',) # Фильтр по Садикам
    exclude = ('is_grouping', 'full_set_price')
    readonly_fields = BaseAlbumAdmin.readonly_fields + ('copy_link_button_large',)
    
    # Включаем Inline, чтобы видеть детей прямо внутри группы
    inlines = [PhotoAlbumInline]

    def get_queryset(self, request):
        # Показываем папки, у которых ЕСТЬ родитель (значит это Группы)
        return super().get_queryset(request).filter(is_grouping=True, parent__isnull=False)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "parent":
            # Родителем группы может быть только Садик (корневая папка)
            kwargs["queryset"] = Kindergarten.objects.filter(is_grouping=True, parent__isnull=True)
            kwargs["label"] = "Садик"
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    @admin.display(description="Ссылка для родителей")
    def copy_link_button(self, obj):
        path = reverse('gallery:album_detail', args=[obj.access_token])
        return format_html(
            '''<button type="button" class="button" onclick="copyToClipboard('{}', this)" style="background-color: #f0f0f0; border: 1px solid #ccc; border-radius: 4px;">📋 Скопировать</button>''',
            path
        )
    
    @admin.display(description="Ссылка на Группу")
    def copy_link_button_large(self, obj):
        path = reverse('gallery:album_detail', args=[obj.access_token])
        return format_html(
            '''<div style="display: flex; gap: 10px; align-items: center;"><input type="text" value="{}" readonly style="width: 350px; padding: 6px;"><button type="button" class="button" onclick="copyToClipboard('{}', this)" style="background-color: #28a745; color: white;">📋 Скопировать ссылку</button></div>''',
            path, path
        )

    def save_model(self, request, obj, form, change):
        obj.is_grouping = True
        super().save_model(request, obj, form, change)


# === 3. ДЕТИ (АЛЬБОМЫ С ФОТО) ===
@admin.register(ChildAlbum)
class ChildAlbumAdmin(BaseAlbumAdmin):
    list_display = ('title', 'cover_thumbnail', 'parent_link', 'photo_count', 'upload_action', 'created_at')
    list_filter = ('parent',) # Фильтр по Группам
    exclude = ('is_grouping', 'expires_at') # У ребенка нет таймера
    readonly_fields = BaseAlbumAdmin.readonly_fields + ('upload_action_large',)

    def get_queryset(self, request):
        return super().get_queryset(request).filter(is_grouping=False).prefetch_related('photos')
    
    @admin.display(description="Фото")
    def photo_count(self, obj):
        count = obj.photos.count()
        style = "color: red; font-weight: bold;" if count == 0 else "color: green;"
        return format_html('<span style="{}">{} шт.</span>', style, count)

    @admin.display(description="Загрузка")
    def upload_action(self, obj):
        url = reverse('admin:gallery_photo_upload_multiple') + f'?album_id={obj.id}'
        return format_html('<a class="button" href="{}" style="background-color: #417690; color: white;">+ Фото</a>', url)
    
    @admin.display(description="Загрузка фотографий")
    def upload_action_large(self, obj):
        url = reverse('admin:gallery_photo_upload_multiple') + f'?album_id={obj.id}'
        return format_html(
            '''<div style="padding: 10px; background: #f8f8f8; border: 1px solid #ddd; border-radius: 4px;">
            <strong>Добавить фото ребенка?</strong><br>
            <a class="button" href="{}" style="margin-top:5px; background-color: #28a745; color: white;">🚀 Загрузить</a>
            </div>''',
            url
        )

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "parent":
            # Родителем ребенка может быть только Группа (не Садик и не другой ребенок)
            # Группа - это папка (is_grouping=True), у которой есть родитель (parent__isnull=False)
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

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context['template_name'] = 'admin/gallery/photo/change_list.html'
        return super().changelist_view(request, extra_context=extra_context)

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('upload-multiple/', self.admin_site.admin_view(self.upload_multiple_photos), name='gallery_photo_upload_multiple'),
        ]
        return custom_urls + urls

    def upload_multiple_photos(self, request):
        initial_data = {}
        preselected_album_id = request.GET.get('album_id')
        if preselected_album_id:
            try:
                # Используем ChildAlbum, так как фото грузим только детям
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
                for image in images:
                    Photo.objects.create(album=album, image=image)
                    count += 1
                
                self.message_user(request, f'Успешно загружено {count} фото для "{album.title}".', messages.SUCCESS)
                # Редирект в альбом ребенка
                return HttpResponseRedirect(reverse('admin:gallery_childalbum_change', args=[album.id]))
                
        else:
            form = MultiplePhotoUploadForm(initial=initial_data)
        
        context = dict(
           self.admin_site.each_context(request),
           form=form,
           opts=self.model._meta,
           title="Загрузка фото ребенка"
        )
        return render(request, 'admin/gallery/photo/upload_multiple.html', context)