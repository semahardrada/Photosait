from django import forms
from .models import Album, ChildAlbum

class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True

class MultipleFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        # Присваиваем виджет по умолчанию
        kwargs.setdefault("widget", MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            # Если файлов несколько, "чистим" (проверяем) каждый из них
            result = [single_file_clean(d, initial) for d in data]
        else:
            # Если файл один, просто проверяем его
            result = single_file_clean(data, initial)
        return result

class MultiplePhotoUploadForm(forms.Form):
    # ИСПРАВЛЕНИЕ ОШИБКИ IntegrityError (FOREIGN KEY constraint failed)
    # Используем ChildAlbum вместо базового Album, чтобы БД корректно создавала связи
    album = forms.ModelChoiceField(
        queryset=ChildAlbum.objects.all(),
        label="Выберите альбом для загрузки",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    # Теперь здесь наше кастомное поле, которое все умеет
    images = MultipleFileField(
        label="Выберите фотографии (можно несколько)",
        required=True, # Делаем поле обязательным
        widget=MultipleFileInput(attrs={'multiple': True, 'class': 'form-control'})
    )