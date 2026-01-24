from django.urls import path
from . import views

app_name = 'gallery'

urlpatterns = [
    # Главная страница (Лендинг)
    path('', views.landing_page, name='landing'),
    
    # Секретный список для админа
    path('admin-albums-overview/', views.album_list, name='album_list'),

    # Основной маршрут для доступа к альбомам (uuid токен)
    path('album/<uuid:access_token>/', views.album_detail, name='album_detail'),
]