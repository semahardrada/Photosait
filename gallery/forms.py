from django import forms
from .models import Album

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
    album = forms.ModelChoiceField(
        queryset=Album.objects.filter(is_grouping=False),
        label="Выберите альбом для загрузки",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    # Теперь здесь наше кастомное поле, которое все умеет
    images = MultipleFileField(
        label="Выберите фотографии (можно несколько)",
        required=True, # Делаем поле обязательным
        widget=MultipleFileInput(attrs={'multiple': True, 'class': 'form-control'})
    )