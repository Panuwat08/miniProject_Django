from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("shop.urls")),

    # orders หลัก
    path("orders/", include(("orders.urls", "orders"), namespace="orders")),

    # ✅ เพิ่ม alias ให้เข้าได้แบบเดิม
    path("", include("orders.urls")),  # ทำให้ /admin-panel/orders/ กลับมาใช้ได้
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)