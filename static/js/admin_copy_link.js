function copyToClipboard(relativePath, btnElement) {
    // 1. Формируем полную ссылку
    const origin = window.location.origin;
    const fullUrl = origin + relativePath;

    // 2. Копируем в буфер (современный способ)
    if (navigator.clipboard && window.isSecureContext) {
        navigator.clipboard.writeText(fullUrl).then(() => {
            showSuccess(btnElement);
        });
    } else {
        // Фоллбэк для старых браузеров
        let textArea = document.createElement("textarea");
        textArea.value = fullUrl;
        textArea.style.position = "fixed";
        textArea.style.left = "-9999px";
        document.body.appendChild(textArea);
        textArea.focus();
        textArea.select();
        try {
            document.execCommand('copy');
            showSuccess(btnElement);
        } catch (err) {
            console.error('Не удалось скопировать', err);
            alert('Ошибка копирования: ' + fullUrl);
        }
        document.body.removeChild(textArea);
    }
}

function showSuccess(btn) {
    const originalText = btn.innerHTML;
    btn.innerHTML = "✅ Скопировано!";
    btn.style.backgroundColor = "#28a745";
    btn.style.color = "white";
    
    setTimeout(() => {
        btn.innerHTML = originalText;
        btn.style.backgroundColor = "#eee"; // Возвращаем серый цвет
        btn.style.color = "#333";
    }, 2000);
}