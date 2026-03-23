from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),

    # accounts: /login /register /logout /dashboard
    path("", include("accounts.urls")),

    # shop: / (home) + /cart...
    path("", include("shop.urls")),

    # orders: /checkout /order/...
    path("", include("orders.urls")),

    # report
    path('reports/', include('reports.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
