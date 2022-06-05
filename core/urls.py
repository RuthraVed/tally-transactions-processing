from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    # path(r"", include(("xml_processing_app.urls", "xml_processing_app"), namespace="api")),
    path('api/', include('rest_framework.urls')),
    path('', include('xml_processing_app.urls')),
]


# Below lines are settings for serving files uploaded by a user when in development. 
# This is not recommended for production.
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
