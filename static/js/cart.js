document.addEventListener('DOMContentLoaded', () => {
    const photoGrid = document.getElementById('photo-grid');
    if (!photoGrid) return; // Если мы не на странице галереи, ничего не делаем

    const orderPanel = document.getElementById('order-panel');
    const selectedCountSpan = document.getElementById('selected-count');
    const totalPriceSpan = document.getElementById('total-price');
    const formatSelect = document.getElementById('product-format');
    const checkoutButton = document.getElementById('checkout-button');
    const orderForm = document.getElementById('order-form');
    const formPhotosInput = document.getElementById('form-photos');
    const formFormatIdInput = document.getElementById('form-format-id');

    // Состояние нашего заказа
    let selectedPhotos = new Set();
    let currentFormatPrice = 0;
    let currentFormatId = null;

    // Функция для обновления UI
    const updateUI = () => {
        // Обновляем количество
        const count = selectedPhotos.size;
        selectedCountSpan.textContent = count;

        // Показываем/скрываем иконки выбора на фото
        document.querySelectorAll('.photo-card').forEach(card => {
            const photoId = card.dataset.photoId;
            const icon = card.querySelector('.selected-icon');
            if (selectedPhotos.has(photoId)) {
                icon.classList.remove('hidden');
                card.classList.add('selected'); // Добавим класс для стилизации, если нужно
            } else {
                icon.classList.add('hidden');
                card.classList.remove('selected');
            }
        });

        // Обновляем цену
        const selectedOption = formatSelect.options[formatSelect.selectedIndex];
        currentFormatPrice = parseFloat(selectedOption.dataset.price);
        currentFormatId = selectedOption.value;
        const totalPrice = count * currentFormatPrice;
        totalPriceSpan.textContent = totalPrice.toFixed(2);
        
        // Показываем/скрываем панель заказа
        if (count > 0) {
            orderPanel.classList.remove('hidden');
            orderPanel.style.transform = 'translateY(0)';
        } else {
            orderPanel.style.transform = 'translateY(100%)';
            // Можно добавить setTimeout, чтобы скрыть после анимации
        }
    };

    // Обработчик клика по фотографии
    photoGrid.addEventListener('click', (event) => {
        const card = event.target.closest('.photo-card');
        if (!card) return;

        const photoId = card.dataset.photoId;
        if (selectedPhotos.has(photoId)) {
            selectedPhotos.delete(photoId);
        } else {
            selectedPhotos.add(photoId);
        }
        updateUI();
    });

    // Обработчик изменения формата
    formatSelect.addEventListener('change', updateUI);
    
    // Обработчик кнопки оформления заказа
    checkoutButton.addEventListener('click', () => {
        if (selectedPhotos.size === 0) {
            alert('Пожалуйста, выберите хотя бы одну фотографию.');
            return;
        }
        // Заполняем и отправляем скрытую форму
        formPhotosInput.value = JSON.stringify(Array.from(selectedPhotos));
        formFormatIdInput.value = currentFormatId;
        orderForm.submit();
    });

    // Инициализация при загрузке страницы
    updateUI();
});
