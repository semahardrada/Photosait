from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.contrib import messages
from .models import Album, Photo, GroupingAlbum, ChildAlbum
from django.urls import reverse

# === 1. ГЛАВНАЯ СТРАНИЦА ===
def landing_page(request):
    if request.method == 'POST':
        access_code = request.POST.get('access_code', '').strip()
        if access_code:
            try:
                # Ищем среди всех альбомов/папок
                album = GroupingAlbum.objects.filter(access_token=access_code).first()
                if album:
                    # При новом входе сбрасываем корзину
                    if 'cart' in request.session:
                        del request.session['cart']
                    return redirect('gallery:album_detail', access_token=album.access_token)
                else:
                    messages.error(request, "Код не найден.")
            except Exception:
                messages.error(request, "Ошибка кода.")
        else:
            messages.warning(request, "Введите код.")

    return render(request, 'gallery/landing.html')


# === 2. АДМИН СПИСОК (Скрытый) ===
def album_list(request):
    if not request.user.is_staff:
        return redirect('gallery:landing')
    # Показываем только Садики
    albums = GroupingAlbum.objects.filter(is_grouping=True, parent__isnull=True).order_by('-created_at')
    return render(request, 'gallery/album_list.html', {'albums': albums, 'page_title': "Садики (Админ)"})


# === 3. ПРОСМОТР АЛЬБОМА/ПАПКИ ===
def album_detail(request, access_token):
    album = get_object_or_404(GroupingAlbum, access_token=access_token)
    
    # Проверка срока
    expired_message = ""
    is_expired = False
    if album.expires_at and timezone.now() > album.expires_at:
        is_expired = True
        expired_message = f"Срок доступа истек {album.expires_at.strftime('%d.%m.%Y')}."

    # === ЕСЛИ ЭТО ПАПКА (Садик или Группа) ===
    if album.is_grouping:
        sub_albums = album.sub_albums.all().order_by('title')
        context = {
            'album': album,
            'albums': sub_albums,
            'page_title': album.title,
            'expired_message': expired_message,
            'is_expired': is_expired,
        }
        return render(request, 'gallery/album_list.html', context)
    
    # === ЕСЛИ ЭТО РЕБЁНОК (Конечный альбом) ===
    else:
        # ИСПРАВЛЕНИЕ: Собираем ID фото для корзины
        # Используем related_name='photos' из модели Photo
        all_photo_ids = list(Photo.objects.filter(album=album).values_list('id', flat=True))
        
        # Обновляем корзину
        request.session['cart'] = {
            'album_id': album.id,
            'buy_full_set': False, 
            'photo_ids': all_photo_ids, # <-- Вот здесь были проблемы, теперь исправлено
            'item_quantities': {}
        }
        request.session.modified = True
        
        return redirect('orders:cart')