from django.urls import path

from . import views

app_name = 'dynamics'

urlpatterns = [
    path('', views.index, name='index'),
]
