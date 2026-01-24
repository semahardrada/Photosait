from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.contrib import messages
from .models import Album, Photo, GroupingAlbum
from django.urls import reverse

# === 1. ГЛАВНАЯ СТРАНИЦА (ЛЕНДИНГ) ===
def landing_page(request):
    if request.method == 'POST':
        access_code = request.POST.get('access_code', '').strip()
        if access_code:
            try:
                album = Album.objects.filter(access_token=access_code).first()
                if album:
                    return redirect('gallery:album_detail', access_token=album.access_token)
                else:
                    messages.error(request, "Альбом с таким кодом не найден.")
            except Exception:
                messages.error(request, "Неверный формат кода.")
        else:
            messages.warning(request, "Пожалуйста, введите код доступа.")

    return render(request, 'gallery/landing.html')


# === 2. СПИСОК ПАПОК (ТОЛЬКО ДЛЯ АДМИНА) ===
def album_list(request):
    if not request.user.is_staff:
        return redirect('gallery:landing')
        
    albums = GroupingAlbum.objects.filter(is_grouping=True, parent__isnull=True).order_by('-created_at')
    
    return render(request, 'gallery/album_list.html', {
        'albums': albums, 
        'page_title': "Все папки (Режим Админа)"
    })


# === 3. ПРОСМОТР АЛЬБОМА (ИСПРАВЛЕННАЯ ЛОГИКА) ===
def album_detail(request, access_token):
    """
    Страница папки или альбома.
    """
    album = get_object_or_404(Album, access_token=access_token)
    
    # --- ПРОВЕРКА СРОКА ДЕЙСТВИЯ ---
    expired_message = ""
    is_expired = False
    if album.expires_at and timezone.now() > album.expires_at:
        is_expired = True
        expired_message = f"Срок доступа истек {album.expires_at.strftime('%d.%m.%Y')}."

    # === ЛОГИКА №1: ЕСЛИ ЭТО ПАПКА ===
    if album.is_grouping:
        # Показываем список вложенных альбомов (как меню)
        sub_albums = album.sub_albums.all().order_by('title')
        context = {
            'album': album,
            'albums': sub_albums,
            'page_title': album.title,
            'expired_message': expired_message,
            'is_expired': is_expired,
        }
        return render(request, 'gallery/album_list.html', context)
    
    # === ЛОГИКА №2: ЕСЛИ ЭТО АЛЬБОМ С ФОТО ===
    else:
        # ИСПРАВЛЕНИЕ ЗДЕСЬ:
        # 1. Получаем список ID всех фотографий в этом альбоме
        # values_list возвращает список чисел [1, 2, 5, 8...]
        all_photo_ids = list(album.photos.values_list('id', flat=True))
        
        # 2. Формируем корзину, добавляя туда ВСЕ эти ID
        request.session['cart'] = {
            'album_id': album.id,
            'buy_full_set': False,  # Ставим False, чтобы отобразился список фото, а не блок "купить все"
            'photo_ids': all_photo_ids, # Загружаем все фото в корзину
            'item_quantities': {}   # Количества пока по нулям, клиент сам выберет
        }
        request.session.modified = True
        
        # 3. Редирект в корзину, где теперь отобразятся все фото
        return redirect('orders:cart')