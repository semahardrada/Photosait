from django.contrib import admin
from django.urls import path, reverse
from django.shortcuts import render
from django.contrib import messages
from django.utils.html import format_html
from django.http import HttpResponseRedirect

from .models import Photo, Album, GroupingAlbum, PhotoAlbum
from .forms import MultiplePhotoUploadForm

# === БАЗОВЫЙ КЛАСС (ОБЩИЕ НАСТРОЙКИ) ===
class BaseAlbumAdmin(admin.ModelAdmin):
    list_display = ('title', 'cover_thumbnail', 'parent_link', 'expires_at', 'created_at')
    search_fields = ('title',)
    readonly_fields = ('access_token', 'cover_preview')
    list_per_page = 25
    save_on_top = True

    # --- ВИЗУАЛИЗАЦИЯ ---
    @admin.display(description="Обложка")
    def cover_preview(self, obj):
        if obj.cover_image:
            return format_html('<img src="{}" style="max-height: 200px; border-radius: 5px;">', obj.cover_image.url)
        return "Нет обложки"

    @admin.display(description="Обложка")
    def cover_thumbnail(self, obj):
        if obj.cover_image:
            return format_html('<img src="{}" width="50" style="border-radius: 3px;">', obj.cover_image.url)
        return "—"

    @admin.display(description="Родительская папка", ordering='parent')
    def parent_link(self, obj):
        if obj.parent:
            url = reverse("admin:gallery_groupingalbum_change", args=[obj.parent.id])
            return format_html('<a href="{}">📁 {}</a>', url, obj.parent.title)
        return "-"

    class Media:
        js = ('js/admin_copy_link.js',)


# === INLINES (Вложенные альбомы) ===
class PhotoAlbumInline(admin.TabularInline):
    model = PhotoAlbum
    fk_name = 'parent'
    extra = 1
    fields = ('title', 'cover_image', 'go_to_album')
    readonly_fields = ('go_to_album',)
    show_change_link = True
    verbose_name = "Вложенный альбом"
    verbose_name_plural = "Вложенные альбомы"

    def get_queryset(self, request):
        return super().get_queryset(request).filter(is_grouping=False)

    @admin.display(description="Действия")
    def go_to_album(self, obj):
        if obj.id:
             url = reverse("admin:gallery_photoalbum_change", args=[obj.id])
             return format_html('<a href="{}" class="button" style="padding:3px 8px;">Редактировать</a>', url)
        return "-"

    def save_model(self, request, obj, form, change):
        obj.is_grouping = False
        super().save_model(request, obj, form, change)


# === ПАПКИ (ЕСТЬ ССЫЛКИ!) ===
@admin.register(GroupingAlbum)
class GroupingAlbumAdmin(BaseAlbumAdmin):
    list_display = ('title', 'cover_thumbnail', 'copy_link_button', 'parent_link', 'created_at')
    
    readonly_fields = BaseAlbumAdmin.readonly_fields + ('copy_link_button_large',)
    
    list_filter = ('created_at',)
    exclude = ('is_grouping', 'full_set_price') 
    inlines = [PhotoAlbumInline]

    def get_queryset(self, request):
        return super().get_queryset(request).filter(is_grouping=True)
    
    # --- ГЕНЕРАТОР ССЫЛОК (ТОЛЬКО ДЛЯ ПАПОК) ---
    @admin.display(description="Ссылка для клиента")
    def copy_link_button(self, obj):
        path = reverse('gallery:album_detail', args=[obj.access_token])
        return format_html(
            '''
            <button type="button" class="button" 
                    onclick="copyToClipboard('{}', this)"
                    style="background-color: #f0f0f0; color: #333; border: 1px solid #ccc; cursor: pointer; border-radius: 4px;">
               📋 Скопировать
            </button>
            ''',
            path
        )

    @admin.display(description="Ссылка на папку")
    def copy_link_button_large(self, obj):
        path = reverse('gallery:album_detail', args=[obj.access_token])
        return format_html(
            '''
            <div style="display: flex; gap: 10px; align-items: center;">
                <input type="text" value="{}" id="link-input-{}" readonly style="width: 350px; padding: 6px; border: 1px solid #ccc; border-radius: 4px;">
                <button type="button" class="button" 
                        onclick="copyToClipboard('{}', this)"
                        style="background-color: #28a745; color: white; padding: 6px 15px; border: none; border-radius: 4px; cursor: pointer;">
                   📋 Скопировать ссылку
                </button>
            </div>
            ''',
            path, obj.id, path
        )

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "parent":
            kwargs["queryset"] = GroupingAlbum.objects.filter(is_grouping=True)
            kwargs["label"] = "Родительская папка"
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def save_model(self, request, obj, form, change):
        obj.is_grouping = True
        super().save_model(request, obj, form, change)


# === ФОТО-АЛЬБОМЫ ===
@admin.register(PhotoAlbum)
class PhotoAlbumAdmin(BaseAlbumAdmin):
    # copy_link_button УБРАН
    list_display = ('title', 'parent_link', 'photo_count', 'upload_action', 'created_at')
    
    list_filter = ('parent', 'created_at')
    exclude = ('is_grouping', 'full_set_price')
    
    readonly_fields = BaseAlbumAdmin.readonly_fields + ('upload_action_large',)

    def get_queryset(self, request):
        return super().get_queryset(request).filter(is_grouping=False).prefetch_related('photos')
    
    @admin.display(description="Фотографий")
    def photo_count(self, obj):
        count = obj.photos.count()
        style = "color: red; font-weight: bold;" if count == 0 else "color: green;"
        return format_html('<span style="{}">{} шт.</span>', style, count)

    @admin.display(description="Быстрая загрузка")
    def upload_action(self, obj):
        url = reverse('admin:gallery_photo_upload_multiple') + f'?album_id={obj.id}'
        return format_html(
            '<a class="button" href="{}" style="background-color: #417690; color: white;">+ Загрузить фото</a>',
            url
        )
    
    @admin.display(description="Загрузка фотографий")
    def upload_action_large(self, obj):
        url = reverse('admin:gallery_photo_upload_multiple') + f'?album_id={obj.id}'
        return format_html(
            '''<div style="padding: 10px; background: #f8f8f8; border: 1px solid #ddd; border-radius: 4px;">
                <strong>Нужно добавить фотографии?</strong><br>
                <a class="button" href="{}" style="margin-top:5px; background-color: #28a745; color: white; font-size: 14px;">
                🚀 Перейти к массовой загрузке для этого альбома</a>
            </div>''',
            url
        )

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "parent":
            kwargs["queryset"] = GroupingAlbum.objects.all()
            kwargs["label"] = "Папка"
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
    
    def save_model(self, request, obj, form, change):
        obj.is_grouping = False
        super().save_model(request, obj, form, change)


# === ФОТОГРАФИИ ===
@admin.register(Photo)
class PhotoAdmin(admin.ModelAdmin):
    exclude = ('processed_image',)
    list_display = ('photo_thumbnail', 'album_link', 'uploaded_at')
    list_filter = ('album',)
    list_select_related = ('album',)
    list_per_page = 40
    
    def add_view(self, request, form_url='', extra_context=None):
        url = reverse('admin:gallery_photo_upload_multiple')
        return HttpResponseRedirect(url)

    @admin.display(description="Альбом")
    def album_link(self, obj):
        url = reverse("admin:gallery_photoalbum_change", args=[obj.album.id])
        return format_html('<a href="{}">{}</a>', url, obj.album.title)

    @admin.display(description="Превью")
    def photo_thumbnail(self, obj):
        if obj.processed_image:
            return format_html('<img src="{}" height="60" style="border-radius: 3px;">', obj.processed_image.url)
        elif obj.image:
            return format_html('<img src="{}" height="60" style="opacity: 0.5;">', obj.image.url)
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
                album = PhotoAlbum.objects.get(id=preselected_album_id)
                initial_data['album'] = album
            except PhotoAlbum.DoesNotExist:
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
                
                self.message_user(request, f'Успешно загружено {count} фото в "{album.title}".', messages.SUCCESS)
                return HttpResponseRedirect(reverse('admin:gallery_photoalbum_change', args=[album.id]))
                
        else:
            form = MultiplePhotoUploadForm(initial=initial_data)
        
        context = dict(
           self.admin_site.each_context(request),
           form=form,
           opts=self.model._meta,
           title="Массовая загрузка фотографий"
        )
        return render(request, 'admin/gallery/photo/upload_multiple.html', context)