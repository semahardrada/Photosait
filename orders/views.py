from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from .models import Order, OrderItem, ProductFormat
from gallery.models import Album, Photo
import json
from django.http import JsonResponse, HttpResponseBadRequest
from decimal import Decimal
from django.views.decorators.http import require_POST

def cart_view(request):
    cart_data = request.session.get('cart', {})
    if not cart_data.get('photo_ids') and not cart_data.get('buy_full_set'):
        return render(request, 'orders/cart.html', {'photos_with_formats': []})

    album = None
    if cart_data.get('album_id'):
        try:
            album = Album.objects.get(pk=cart_data.get('album_id'))
        except Album.DoesNotExist:
             request.session.pop('cart', None)
             return render(request, 'orders/cart.html', {'photos_with_formats': []})
    
    all_formats = ProductFormat.objects.all()
    photos_with_formats = []
    grand_total = Decimal('0.00')
    bonus_threshold = Decimal('2500.00') 
    
    if cart_data.get('buy_full_set') and album:
        photos_with_formats.append({
            'is_full_set': True,
            'photo_obj': {
                'id': 'full_set',
                'name': f"Все фото Online '{album.title}' ({album.photos.count()} шт.)",
                'image_url': album.photos.first().processed_image.url if album.photos.exists() else '',
            },
            'full_set_price': album.full_set_price
        })
        grand_total = album.full_set_price
    else:
        photo_ids = cart_data.get('photo_ids', [])
        item_quantities = cart_data.get('item_quantities', {})
        valid_photo_ids = []
        
        # === ЛОГИКА КОЛЛАЖА: Запоминаем, за какие коллажи мы уже взяли деньги ===
        charged_collage_format_ids = set()

        for photo_id in photo_ids:
            try:
                photo = Photo.objects.select_related('album').get(pk=photo_id)
                formats_list = []
                
                for fmt in all_formats:
                    key = f"{photo_id}_{fmt.id}"
                    quantity = item_quantities.get(key, 0)
                    
                    # === НОВАЯ ЛОГИКА ЦЕНЫ ===
                    effective_price = fmt.price
                    
                    if fmt.is_collage and quantity > 0:
                        # Если это коллаж и он выбран (>0)
                        if fmt.id in charged_collage_format_ids:
                            # Мы уже взяли деньги за этот тип коллажа в этом заказе
                            # Значит, для этого фото добавка в коллаж БЕСПЛАТНАЯ
                            effective_price = Decimal('0.00')
                        else:
                            # Это первое фото для коллажа, берем полную цену
                            # И запоминаем, что оплата взята
                            charged_collage_format_ids.add(fmt.id)
                    
                    row_total = effective_price * quantity
                    # ========================

                    formats_list.append({
                        'format_obj': fmt,
                        'price': fmt.price, # Оригинальная цена (для отображения)
                        'effective_price': effective_price, # Реальная цена для итога
                        'quantity': quantity,
                        'row_total': row_total
                    })
                    grand_total += row_total
                
                photos_with_formats.append({
                    'is_full_set': False,
                    'photo_obj': photo,
                    'formats': formats_list
                })
                valid_photo_ids.append(photo_id)
            
            except Photo.DoesNotExist:
                continue 
        
        if len(valid_photo_ids) < len(photo_ids):
            cart_data['photo_ids'] = valid_photo_ids
            request.session.modified = True

    context = {
        'photos_with_formats': photos_with_formats,
        'grand_total': grand_total,
        'bonus_threshold': bonus_threshold,
        'album': album, 
        'cart': cart_data
    }
    return render(request, 'orders/cart.html', context)

@require_POST
def add_full_set_to_cart_view(request, album_id):
    album = get_object_or_404(Album, pk=album_id)
    cart = {
        'album_id': album_id,
        'buy_full_set': True,
        'photo_ids': [],
        'item_quantities': {}
    }
    request.session['cart'] = cart
    return redirect('orders:cart')

@require_POST
def update_cart_view(request):
    try:
        data = json.loads(request.body)
        photo_id = str(data.get('photo_id'))
        format_id = str(data.get('format_id'))
        quantity = int(data.get('quantity'))

        if quantity < 0:
            quantity = 0
            
        # Для коллажа количество может быть только 0 или 1
        # (Мы не добавляем одну и ту же фотку в коллаж дважды)
        # Но проверку сделаем на фронте, здесь оставим как есть.

        cart = request.session.get('cart', {})
        if 'item_quantities' not in cart:
            cart['item_quantities'] = {}

        key = f"{photo_id}_{format_id}"
        cart['item_quantities'][key] = quantity
        
        request.session.modified = True
        return JsonResponse({'status': 'ok'})
    except (json.JSONDecodeError, TypeError, ValueError):
        return HttpResponseBadRequest('Invalid JSON')

@require_POST
def remove_photo_from_cart_view(request):
    try:
        data = json.loads(request.body)
        photo_id_to_remove = str(data.get('photo_id'))

        cart = request.session.get('cart', {})
        if not cart:
            return JsonResponse({'status': 'ok', 'message': 'Cart already empty'})

        if 'photo_ids' in cart and photo_id_to_remove in cart['photo_ids']:
            cart['photo_ids'].remove(photo_id_to_remove)
        
        if 'item_quantities' in cart:
            keys_to_delete = []
            for key in cart['item_quantities']:
                if key.startswith(f"{photo_id_to_remove}_"):
                    keys_to_delete.append(key)
            
            for key in keys_to_delete:
                del cart['item_quantities'][key]

        request.session.modified = True
        return JsonResponse({'status': 'ok'})

    except (json.JSONDecodeError, TypeError, ValueError):
        return HttpResponseBadRequest('Invalid JSON')
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

def create_order_view(request):
    if request.method != 'POST': return redirect('gallery:album_list')

    cart_data = request.session.get('cart', {})
    if not cart_data: return redirect('gallery:album_list')
    
    full_name = request.POST.get('customer_name', '').split()
    order = Order.objects.create(
        first_name=full_name[0] if full_name else 'Имя',
        last_name=' '.join(full_name[1:]) if len(full_name) > 1 else 'Фамилия',
        email=request.POST.get('customer_email'), 
        phone=request.POST.get('customer_phone'),
    )
    
    album = None
    if cart_data.get('album_id'):
        album = get_object_or_404(Album, pk=cart_data.get('album_id'))
    
    total_price = Decimal('0.00')
    bonus_threshold = Decimal('2500.00')

    if cart_data.get('buy_full_set') and album:
        item_price = album.full_set_price
        OrderItem.objects.create(
            order=order, 
            price=item_price, 
            quantity=1, 
            is_full_set=True, 
            album_set=album
        )
        total_price = item_price
    else:
        item_quantities = cart_data.get('item_quantities', {})
        
        # === ЛОГИКА ДЛЯ СОЗДАНИЯ ЗАКАЗА (КОЛЛАЖ) ===
        charged_collage_format_ids = set()

        # Важно пройтись по тому же порядку или логике, что и в cart_view, 
        # но так как item_quantities это словарь без порядка, мы будем просто проверять.
        
        # Чтобы гарантировать, что цена спишется ровно 1 раз, нам нужно быть аккуратными.
        # Пройдемся по item_quantities
        
        for key, quantity in item_quantities.items():
            if quantity <= 0:
                continue
            
            try:
                photo_id, format_id = key.split('_')
                photo = Photo.objects.get(pk=photo_id)
                product_format = ProductFormat.objects.get(pk=format_id)
                
                # Рассчитываем цену для БД
                item_price = product_format.price
                
                if product_format.is_collage:
                    # Если это коллаж
                    if int(format_id) in charged_collage_format_ids:
                        # Уже платили за этот формат в этом заказе -> цена 0
                        item_price = Decimal('0.00')
                    else:
                        # Первая встреча -> платим полную цену
                        charged_collage_format_ids.add(int(format_id))
                
                OrderItem.objects.create(
                    order=order, photo=photo, product_format=product_format,
                    price=item_price, quantity=quantity
                )
                total_price += item_price * quantity
            except (ValueError, Photo.DoesNotExist, ProductFormat.DoesNotExist):
                continue 

    if total_price >= bonus_threshold:
        order.received_bonus = True
        order.save()

    if 'cart' in request.session: del request.session['cart']
    return redirect(reverse('orders:order_confirmation', args=[order.id]))

def order_confirmation_view(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    total_price = sum(item.get_cost() for item in order.items.all())
    context = {'order': order, 'total_price': total_price}
    return render(request, 'orders/order_confirmation.html', context)

def upload_receipt_view(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    if request.method == 'POST' and request.FILES.get('receipt'):
        order.receipt = request.FILES['receipt']; order.status = 'paid'; order.save()
        return redirect(reverse('orders:order_complete', args=[order.id]))
    return redirect(reverse('orders:order_confirmation', args=[order.id]))

def order_complete_view(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    return render(request, 'orders/order_complete.html', {'order': order})