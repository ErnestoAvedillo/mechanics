from django import forms
from django.utils.translation import gettext_lazy as _
from .models import UserDocument

class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True

class MultipleFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            result = [single_file_clean(d, initial) for d in data]
        else:
            result = single_file_clean(data, initial)
        return result

class DocumentUploadForm(forms.ModelForm):
    company = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'placeholder': _('Ej. VW, BMW, ISO...')})
    )
    pdf_file = MultipleFileField(required=True)

    class Meta:
        model = UserDocument
        fields = ['company']
