"""
Django settings for photographer_project project.
PRODUCTION VERSION (BEGET)
"""
import os
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# --- БЕЗОПАСНОСТЬ ---

# SECRET_KEY должен быть секретным!
# На сервере мы создадим файл .env и положим ключ туда.
# Если ключа нет в окружении, используется временный (небезопасно, но сработает для первого старта)
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'django-insecure-change-me-immediately-on-production')

# В ПРОДАКШЕНЕ DEBUG ВСЕГДА FALSE
# Мы можем переключить его в True только через переменную окружения на сервере
DEBUG = os.environ.get('DJANGO_DEBUG', 'False') == 'True'

# --- ХОСТЫ ---
# Здесь мы разрешаем доступ по IP и Домену
# os.environ.get('DJANGO_ALLOWED_HOSTS') позволит передать список через запятую
allowed_hosts_env = os.environ.get('DJANGO_ALLOWED_HOSTS')
if allowed_hosts_env:
    ALLOWED_HOSTS = allowed_hosts_env.split(',')
else:
    # Если переменная не задана, разрешаем всё (удобно для первого запуска по IP)
    # ПОТОМ ЛУЧШЕ ЗАМЕНИТЬ НА КОНКРЕТНЫЙ IP И ДОМЕН
    ALLOWED_HOSTS = ['*']

# Доверенные источники для CSRF (чтобы работали формы через https)
CSRF_TRUSTED_ORIGINS = []
if os.environ.get('MY_DOMAIN'):
    CSRF_TRUSTED_ORIGINS.append(f"https://{os.environ.get('MY_DOMAIN')}")


# Application definition
INSTALLED_APPS = [
    'jazzmin',  # Админка (Jazzmin должен быть первым)
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Твои приложения
    'gallery',
    'orders',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'photographer_project.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'photographer_project.wsgi.application'

# Database
# Для 50 заказов в день SQLite вполне хватит и его проще бэкапить (просто скачать файл)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Internationalization
LANGUAGE_CODE = 'ru-ru'
TIME_ZONE = 'Europe/Moscow'
USE_I18N = True
USE_TZ = True

# --- STATIC & MEDIA FILES (ВАЖНО ДЛЯ СЕРВЕРА) ---

# URL, по которому файлы доступны в браузере
STATIC_URL = '/static/'

# Папка, где лежат статические файлы разработки
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static'),
]
# STATICFILES_DIRS = [BASE_DIR / "static"]

# Папка, куда Django соберет ВСЕ статические файлы (включая админку) командой collectstatic
# Именно эту папку будет раздавать Nginx
STATIC_ROOT = BASE_DIR / 'static_root'

# Медиа файлы (загруженные пользователем)
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'


DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# # === EMAIL SETTINGS (ДЛЯ УВЕДОМЛЕНИЙ) ===
# # Для начала выводим в консоль, чтобы сайт не падал без настроек SMTP
# EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
# # Когда будешь готов, раскомментируй строки ниже и впиши данные почты:
# # EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
# # EMAIL_HOST = 'smtp.yandex.ru'
# # EMAIL_PORT = 465
# # EMAIL_USE_SSL = True
# # EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER')
# # EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD')
# # DEFAULT_FROM_EMAIL = os.environ.get('EMAIL_HOST_USER')


# === JAZZMIN SETTINGS (ТВОЯ КРАСИВАЯ АДМИНКА) ===
JAZZMIN_SETTINGS = {
    "site_title": "Фото-Студия Admin",
    "site_header": "Управление Студией",
    "site_brand": "Панель Фотографа",
    "welcome_sign": "Вход в систему управления",
    "copyright": "Фото-Студия",
    "search_model": ["orders.Order", "gallery.Album"],
    "user_avatar": None,
    "topmenu_links": [
        {"name": "Главная", "url": "admin:index", "permissions": ["auth.view_user"]},
        {"name": "Открыть сайт", "url": "/", "new_window": True},
        {"model": "orders.Order"},
    ],
    "icons": {
        "auth": "fas fa-users-cog",
        "auth.user": "fas fa-user",
        "auth.Group": "fas fa-users",
        "gallery.GroupingAlbum": "fas fa-folder",
        "gallery.PhotoAlbum": "fas fa-images",
        "gallery.Photo": "fas fa-camera",
        "gallery.Album": "fas fa-layer-group",
        "orders.Order": "fas fa-shopping-cart",
        "orders.OrderItem": "fas fa-list",
        "orders.ProductFormat": "fas fa-ruler-combined",
    },
    "order_with_respect_to": ["orders", "gallery", "auth"],
    "show_sidebar": True,
    "navigation_expanded": True,
    "custom_css": "css/custom_admin.css",
}

JAZZMIN_UI_TWEAKS = {
    "theme": "flatly",
    "navbar": "navbar-dark bg-primary",
    "sidebar": "sidebar-dark-primary",
    "sidebar_nav_child_indent": True,
}