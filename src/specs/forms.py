from django import forms
from django.utils.translation import gettext_lazy as _
from .languages import language_choices
from .metadata import normalize_issuer, normalize_number
from .models import Document, UserDocument

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


class MetadataReviewForm(forms.ModelForm):
    """The uploader reviews the standard's metadata proposed by the LLM and confirms it."""

    class Meta:
        model = Document
        fields = ['spec_issuer', 'spec_number', 'title', 'edition_date', 'language', 'original_language']
        labels = {
            'spec_issuer': _('Emisor / OEM'),
            'spec_number': _('Número de norma'),
            'title': _('Título'),
            'edition_date': _('Fecha de edición'),
        }
        widgets = {'edition_date': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d')}

    # Selectors, not free text: the language decides which variant of a standard is searched.
    # The user sees the full name; the ISO code is what gets stored.
    language = forms.ChoiceField(label=_('Idioma de este documento'))
    original_language = forms.ChoiceField(required=False, label=_('Idioma original que prevalece (si es una traducción)'))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in ('spec_issuer', 'spec_number'):
            self.fields[name].required = True
        # Keep a value outside the list (e.g. detected by the LLM) selectable so it is never lost
        in_use = {self.instance.language, self.instance.original_language}
        choices = language_choices(extra=in_use)
        self.fields['language'].choices = [('', _('Selecciona un idioma'))] + choices
        self.fields['original_language'].choices = [('', _('Igual que el idioma de este documento'))] + choices
        for field in self.fields.values():
            field.widget.attrs.setdefault('class', 'form-control')

    def clean_spec_issuer(self):
        return normalize_issuer(self.cleaned_data['spec_issuer'])

    def clean_spec_number(self):
        number = normalize_number(self.cleaned_data['spec_number'])
        if not number:
            raise forms.ValidationError(_("Introduce el número de la norma."))
        return number

    def clean_original_language(self):
        # Empty means the document is the original: its own language prevails
        return self.cleaned_data.get('original_language') or self.cleaned_data.get('language', '')
