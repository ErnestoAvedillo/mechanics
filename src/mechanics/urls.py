from django.urls import path, include
from django.views.i18n import JavaScriptCatalog

urlpatterns = [
    path('i18n/', include('django.conf.urls.i18n')),
    path('jsi18n/', JavaScriptCatalog.as_view(packages=['muelles', 'tolerances']), name='javascript-catalog'),
    path('', include('menuapp.urls')),
    path('muelles/', include('muelles.urls')),
    path('tolerances/', include('tolerances.urls')),
    path('specs/', include('specs.urls')),
]
