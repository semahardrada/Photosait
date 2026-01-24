from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),

    # ПРАВИЛЬНАЯ СТРОКА:
    # Мы подключаем все URL из 'gallery.urls' к корневому пути ''
    path('', include('gallery.urls')),

    # URL для заказов остаются с префиксом 'order/'
    path('order/', include('orders.urls')),
]

# Это нужно для того, чтобы в режиме разработки Django мог отдавать медиа-файлы
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)