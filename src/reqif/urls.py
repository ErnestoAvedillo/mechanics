from django.urls import path
from . import views

app_name = 'reqif'

urlpatterns = [
    path('', views.upload_view, name='upload'),
    path('documentos/', views.documents_view, name='documents'),
    path('documentos/<int:index>/', views.edit_document_view, name='edit_document'),
    path('documentos/<int:index>/excel/', views.export_excel_view, name='export_excel'),
    path('documentos/<int:index>/excel/subir/', views.import_excel_view, name='import_excel'),
    path('descargar/', views.download_view, name='download'),
    path('adjunto/<path:rel_path>', views.attachment_view, name='attachment'),
]
