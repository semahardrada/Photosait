from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from .models import Order, OrderItem, ProductFormat
from gallery.models import Album, Photo
import json
from django.http import JsonResponse, HttpResponseBadRequest
from decimal import Decimal
from django.views.decorators.http import require_POST
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
import threading

# === ПОЧТОВЫЙ ПОТОК ===
class EmailThread(threading.Thread):
    def __init__(self, order):
        self.order = order
        threading.Thread.__init__(self)

    def run(self):
        try:
            # 1. Письмо АДМИНУ
            if settings.EMAIL_HOST_USER:
                subject_admin = f'💰 Новый заказ #{self.order.id} ({self.order.get_full_name()})'
                message_admin = f"""
                Поступил новый заказ #{self.order.id}.
                Клиент: {self.order.get_full_name()}
                Телефон: {self.order.phone or "Не указан"}
                Email: {self.order.email or "Не указан"}
                Сумма: {self.order.get_total_cost() if hasattr(self.order, 'get_total_cost') else '---'} руб.
                
                Проверьте оплату в админке!
                """
                send_mail(subject_admin, message_admin, settings.DEFAULT_FROM_EMAIL, [settings.EMAIL_HOST_USER])
            
            # 2. Письмо КЛИЕНТУ (Только если есть Email)
            if self.order.email:
                subject_client = f'Ваш заказ #{self.order.id} принят'
                message_client = f"""
                Здравствуйте, {self.order.first_name}!
                
                Ваш заказ #{self.order.id} успешно оформлен.
                
                После оплаты, пожалуйста, вернитесь на сайт и прикрепите чек.
                """
                send_mail(subject_client, message_client, settings.DEFAULT_FROM_EMAIL, [self.order.email])
        except Exception as e:
            print(f"Ошибка отправки почты: {e}")

def cart_view(request):
    cart_data = request.session.get('cart', {})
    photo_ids = cart_data.get('photo_ids', [])
    buy_full_set = cart_data.get('buy_full_set', False)

    if not photo_ids and not buy_full_set:
        return render(request, 'orders/cart.html', {'photos_with_formats': []})

    album = None
    if cart_data.get('album_id'):
        try: album = Album.objects.get(pk=cart_data.get('album_id'))
        except Album.DoesNotExist:
             request.session.pop('cart', None)
             return render(request, 'orders/cart.html', {'photos_with_formats': []})
    
    all_formats = ProductFormat.objects.all()
    photos_with_formats = []
    grand_total = Decimal('0.00')
    bonus_threshold = Decimal('2500.00') 
    
    if buy_full_set and album:
        photos_with_formats.append({
            'is_full_set': True,
            'photo_obj': {'id': 'full_set', 'name': f"Все фото '{album.title}'", 'image_url': album.photos.first().processed_image.url if album.photos.exists() else ''},
            'full_set_price': album.full_set_price
        })
        grand_total = album.full_set_price
    else:
        item_quantities = cart_data.get('item_quantities', {})
        valid_photo_ids = []
        charged_collage_format_ids = set()

        for photo_id in photo_ids:
            try:
                photo = Photo.objects.select_related('album').get(pk=int(photo_id))
                formats_list = []
                for fmt in all_formats:
                    key = f"{photo_id}_{fmt.id}"
                    quantity = item_quantities.get(key, 0)
                    effective_price = fmt.price
                    if fmt.is_collage and quantity > 0:
                        if fmt.id in charged_collage_format_ids: effective_price = Decimal('0.00')
                        else: charged_collage_format_ids.add(fmt.id)
                    row_total = effective_price * quantity
                    formats_list.append({'format_obj': fmt, 'price': fmt.price, 'effective_price': effective_price, 'quantity': quantity, 'row_total': row_total})
                    grand_total += row_total
                photos_with_formats.append({'is_full_set': False, 'photo_obj': photo, 'formats': formats_list})
                valid_photo_ids.append(photo_id)
            except (Photo.DoesNotExist, ValueError): continue 
        
        if len(valid_photo_ids) < len(photo_ids):
            cart_data['photo_ids'] = valid_photo_ids
            request.session.modified = True

    context = {'photos_with_formats': photos_with_formats, 'grand_total': grand_total, 'bonus_threshold': bonus_threshold, 'album': album, 'cart': cart_data}
    return render(request, 'orders/cart.html', context)

@require_POST
def add_full_set_to_cart_view(request, album_id):
    album = get_object_or_404(Album, pk=album_id)
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
    except Exception: return HttpResponseBadRequest('Invalid JSON')

@require_POST
def remove_photo_from_cart_view(request):
    try:
        data = json.loads(request.body)
        photo_id = str(data.get('photo_id'))
        cart = request.session.get('cart', {})
        if 'photo_ids' in cart and photo_id in cart['photo_ids']: cart['photo_ids'].remove(photo_id)
        keys_to_del = [k for k in cart.get('item_quantities', {}) if k.startswith(f"{photo_id}_")]
        for k in keys_to_del: del cart['item_quantities'][k]
        request.session.modified = True
        return JsonResponse({'status': 'ok'})
    except Exception: return HttpResponseBadRequest('Error')

def create_order_view(request):
    if request.method != 'POST': return redirect('gallery:landing')
    cart_data = request.session.get('cart', {})
    if not cart_data: return redirect('gallery:landing')
    
    full_name = request.POST.get('customer_name', 'Клиент').split()
    
    # === ИЗМЕНЕНИЕ: Email и Phone могут быть None ===
    order = Order.objects.create(
        first_name=full_name[0] if full_name else 'Без имени',
        last_name=' '.join(full_name[1:]) if len(full_name) > 1 else '',
        email=request.POST.get('customer_email') or None, 
        phone=request.POST.get('customer_phone') or None,
    )
    
    album = None
    if cart_data.get('album_id'): album = get_object_or_404(Album, pk=cart_data.get('album_id'))
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
            except Exception: continue

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