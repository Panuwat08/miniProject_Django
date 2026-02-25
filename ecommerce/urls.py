from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),

    # shop: / (home) + /cart...
    path("", include("shop.urls")),

    # orders: /checkout /order/...
    path("", include("orders.urls")),

    # products: /products/... (แสดงสินค้าอุปกรณ์โรงแรม)
    path("products/", include("products.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
