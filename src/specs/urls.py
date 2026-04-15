from django.urls import path
from . import views

app_name = 'specs'

urlpatterns = [
    path('', views.document_list, name='document_list'),
    path('upload/', views.upload_document, name='upload_document'),
]
