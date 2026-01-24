from django.urls import path
from . import views

app_name = 'orders'

urlpatterns = [
    path('cart/', views.cart_view, name='cart'),
    
    # URL для обновления кол-ва
    path('cart/update/', views.update_cart_view, name='update_cart'),
    
    # ===  НОВЫЙ URL ДЛЯ ПОЛНОГО УДАЛЕНИЯ ФОТО ===
    path('cart/remove-photo/', views.remove_photo_from_cart_view, name='remove_photo_from_cart'),
    
    path('create/', views.create_order_view, name='create_order'),
    path('add-full-set/<int:album_id>/', views.add_full_set_to_cart_view, name='add_full_set'),
    path('<int:order_id>/confirmation/', views.order_confirmation_view, name='order_confirmation'),
    path('<int:order_id>/upload_receipt/', views.upload_receipt_view, name='upload_receipt'),
    path('<int:order_id>/complete/', views.order_complete_view, name='order_complete'),
]


