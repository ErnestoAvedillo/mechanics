from django.urls import path, include

urlpatterns = [
    path('', include('menuapp.urls')),
    path('muelles/', include('muelles.urls')),
    path('tolerances/', include('tolerances.urls')),
]
