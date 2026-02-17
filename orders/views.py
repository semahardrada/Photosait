from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from .models import Order, OrderItem, ProductFormat
from gallery.models import Album, Photo, ChildAlbum
import json
from django.http import JsonResponse, HttpResponseBadRequest
from decimal import Decimal
from django.views.decorators.http import require_POST
from django.core.mail import send_mail
from django.conf import settings
import threading

class EmailThread(threading.Thread):
    def __init__(self, order):
        self.order = order
        threading.Thread.__init__(self)

    def run(self):
        try:
            if settings.EMAIL_HOST_USER:
                send_mail(f'💰 Заказ #{self.order.id}', f'Клиент: {self.order.get_full_name()}', settings.DEFAULT_FROM_EMAIL, [settings.EMAIL_HOST_USER])
            if self.order.email:
                send_mail(f'Заказ #{self.order.id} принят', f'Сумма: {self.order.get_total_cost()} руб.', settings.DEFAULT_FROM_EMAIL, [self.order.email])
        except Exception: pass

def cart_view(request):
    cart_data = request.session.get('cart', {})
    photo_ids = cart_data.get('photo_ids', [])
    buy_full_set = cart_data.get('buy_full_set', False)

    if not photo_ids and not buy_full_set:
        return render(request, 'orders/cart.html', {'photos_with_formats': []})

    album = None
    if cart_data.get('album_id'):
        # Используем ChildAlbum для поиска
        try: album = ChildAlbum.objects.get(pk=cart_data.get('album_id'))
        except ChildAlbum.DoesNotExist:
             request.session.pop('cart', None)
             return render(request, 'orders/cart.html', {'photos_with_formats': []})
    
    all_formats = ProductFormat.objects.all()
    photos_with_formats = []
    grand_total = Decimal('0.00')
    bonus_threshold = Decimal('2500.00') 
    
    if buy_full_set and album:
        photos_with_formats.append({
            'is_full_set': True,
            'photo_obj': {
                'id': 'full_set', 
                'name': f"Все фото '{album.title}'", 
                # Проверка на наличие фото перед обращением к [0]
                'image_url': album.photos.first().processed_image.url if album.photos.exists() else ''
            },
            'full_set_price': album.full_set_price
        })
        grand_total = album.full_set_price
    else:
        item_quantities = cart_data.get('item_quantities', {})
        valid_photo_ids = []
        charged_collage_format_ids = set()

        # Фильтруем фото по ID из сессии
        photos = Photo.objects.filter(id__in=photo_ids)
        # Создаем словарь для быстрого доступа, чтобы сохранить порядок (если важно) или просто итерируем
        
        for photo in photos:
            try:
                formats_list = []
                for fmt in all_formats:
                    key = f"{photo.id}_{fmt.id}"
                    quantity = item_quantities.get(key, 0)
                    effective_price = fmt.price
                    if fmt.is_collage and quantity > 0:
                        if fmt.id in charged_collage_format_ids: effective_price = Decimal('0.00')
                        else: charged_collage_format_ids.add(fmt.id)
                    row_total = effective_price * quantity
                    formats_list.append({'format_obj': fmt, 'price': fmt.price, 'effective_price': effective_price, 'quantity': quantity, 'row_total': row_total})
                    grand_total += row_total
                photos_with_formats.append({'is_full_set': False, 'photo_obj': photo, 'formats': formats_list})
                valid_photo_ids.append(str(photo.id))
            except Exception: continue
        
        # Если список валидных фото изменился, обновляем сессию
        # if len(valid_photo_ids) < len(photo_ids): ... (можно опустить для скорости)

    context = {'photos_with_formats': photos_with_formats, 'grand_total': grand_total, 'bonus_threshold': bonus_threshold, 'album': album, 'cart': cart_data}
    return render(request, 'orders/cart.html', context)

# ... (Остальные функции add_full_set, update, remove, create_order - используй из предыдущего ответа, они корректны) ...
# ВАЖНО: Вставь сюда create_order_view и другие функции, которые я присылал ранее.
# Они не менялись, главное - cart_view выше.

@require_POST
def add_full_set_to_cart_view(request, album_id):
    album = get_object_or_404(ChildAlbum, pk=album_id)
    cart = {'album_id': album_id, 'buy_full_set': True, 'photo_ids': [], 'item_quantities': {}}
    request.session['cart'] = cart
    return redirect('orders:cart')

@require_POST
def update_cart_view(request):
    try:
        data = json.loads(request.body)
        photo_id = str(data.get('photo_id'))
        format_id = str(data.get('format_id'))
        quantity = int(data.get('quantity'))
        if quantity < 0: quantity = 0
        cart = request.session.get('cart', {})
        if 'item_quantities' not in cart: cart['item_quantities'] = {}
        key = f"{photo_id}_{format_id}"
        cart['item_quantities'][key] = quantity
        request.session.modified = True
        return JsonResponse({'status': 'ok'})
    except: return HttpResponseBadRequest()

@require_POST
def remove_photo_from_cart_view(request):
    try:
        data = json.loads(request.body)
        photo_id = str(data.get('photo_id'))
        cart = request.session.get('cart', {})
        if 'photo_ids' in cart:
            # photo_ids может быть списком чисел или строк, приводим к строкам для удаления
            cart['photo_ids'] = [str(pid) for pid in cart['photo_ids']]
            if str(photo_id) in cart['photo_ids']:
                cart['photo_ids'].remove(str(photo_id))
        request.session.modified = True
        return JsonResponse({'status': 'ok'})
    except: return HttpResponseBadRequest()

def create_order_view(request):
    if request.method != 'POST': return redirect('gallery:landing')
    cart_data = request.session.get('cart', {})
    if not cart_data: return redirect('gallery:landing')
    
    full_name = request.POST.get('customer_name', 'Клиент').split()
    order = Order.objects.create(
        first_name=full_name[0] if full_name else 'Без имени',
        last_name=' '.join(full_name[1:]) if len(full_name) > 1 else '',
        email=request.POST.get('customer_email') or None, 
        phone=request.POST.get('customer_phone') or None,
    )
    
    album = None
    if cart_data.get('album_id'): 
        album = get_object_or_404(ChildAlbum, pk=cart_data.get('album_id'))
    
    total_price = Decimal('0.00')
    bonus_threshold = Decimal('2500.00')
    charged_collage_format_ids = set()
    
    if cart_data.get('buy_full_set') and album:
        item_price = album.full_set_price
        OrderItem.objects.create(order=order, price=item_price, quantity=1, is_full_set=True, album_set=album)
        total_price = item_price
    else:
        item_quantities = cart_data.get('item_quantities', {})
        for key, quantity in item_quantities.items():
            if quantity <= 0: continue
            try:
                parts = key.split('_')
                if len(parts) < 2: continue
                photo_id, format_id = parts[0], parts[1]
                photo = Photo.objects.get(pk=photo_id)
                product_format = ProductFormat.objects.get(pk=format_id)
                item_price = product_format.price
                if product_format.is_collage:
                    if int(format_id) in charged_collage_format_ids: item_price = Decimal('0.00')
                    else: charged_collage_format_ids.add(int(format_id))
                OrderItem.objects.create(order=order, photo=photo, product_format=product_format, price=item_price, quantity=quantity)
                total_price += item_price * quantity
            except: continue

    if total_price >= bonus_threshold: order.received_bonus = True; order.save()
    if 'cart' in request.session: del request.session['cart']
    EmailThread(order).start()
    return redirect(reverse('orders:order_confirmation', args=[order.id]))

def order_confirmation_view(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    total_price = sum(item.get_cost() for item in order.items.all())
    return render(request, 'orders/order_confirmation.html', {'order': order, 'total_price': total_price})

def upload_receipt_view(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    if request.method == 'POST' and request.FILES.get('receipt'):
        order.receipt = request.FILES['receipt']; order.status = 'paid'; order.save()
        return redirect(reverse('orders:order_complete', args=[order.id]))
    return redirect(reverse('orders:order_confirmation', args=[order.id]))

def order_complete_view(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    return render(request, 'orders/order_complete.html', {'order': order})