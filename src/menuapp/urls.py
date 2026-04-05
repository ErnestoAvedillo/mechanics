from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('editor/<str:datos>/<str:filename>/', views.editor, name='editor'),
    path('editor-session/<str:data_id>/<str:filename>/', views.editor_with_session, name='editor_with_session'),
    path('open/<str:filename>/', views.abrir, name='abrir'),
    path('abrir/<path:folder>/<str:group_name>/', views.abrir_carpeta, name='abrir_carpeta'),
    path('guarda/', views.guarda, name='guarda'),
    path('bloques-editor/', views.bloques_editor, name='bloques_editor'),
    path('visualizador-json/', views.json_visualizer, name='json_visualizer'),
]
