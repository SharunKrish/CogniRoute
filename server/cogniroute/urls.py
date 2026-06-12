from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.staticfiles.urls import staticfiles_urlpatterns

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Auth endpoints
    path('api/auth/', include('accounts.urls')),
    
    # Requests and classification endpoints
    path('api/', include('requests_app.urls')),
    
    # Direct index load to render dashboard frontend
    path('', TemplateView.as_view(template_name='index.html'), name='index'),
]

# Serve static files in development (and fallback in production if needed)
if settings.DEBUG:
    urlpatterns += staticfiles_urlpatterns()
else:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
