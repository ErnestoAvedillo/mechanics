from django import forms
from .models import UserDocument

class DocumentUploadForm(forms.ModelForm):
    company = forms.CharField(
        max_length=100, 
        required=False, 
        widget=forms.TextInput(attrs={'placeholder': 'Ej. VW, BMW, ISO...'})
    )
    pdf_file = forms.FileField()

    class Meta:
        model = UserDocument
        fields = ['company']
