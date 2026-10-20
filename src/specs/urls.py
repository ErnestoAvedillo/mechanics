from django.urls import path
from . import views


app_name = 'specs'

urlpatterns = [
    path('index/', views.index, name='index'),
    path('demo/', views.demo_start, name='demo_start'),
    path('handling/', views.document_list, name='handling'),
    path('handling/view/<int:doc_id>/', views.document_view, name='document_view'),
    path('handling/delete/<int:doc_id>/', views.document_delete, name='document_delete'),
    path('handling/update/<int:doc_id>/', views.document_update, name='document_update'),
    path('handling/review/<int:doc_id>/', views.document_review, name='document_review'),
    path('upload/', views.upload_document, name='upload_document'),
    path('chat/', views.chat_view, name='chat_view'),
    path('chat/query/', views.chat_query, name='chat_query'),
]
