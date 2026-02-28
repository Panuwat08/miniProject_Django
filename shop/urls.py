# ==========================================
# urls.py — กำหนดเส้นทาง URL ของแอป shop
# แบ่งเป็น 3 กลุ่ม: หน้าร้าน, ตะกร้า, จัดการสินค้า (Admin)
# ==========================================

from django.urls import path
from . import views

urlpatterns = [
    # ==========================================
    # เส้นทางหน้าร้าน (Storefront URLs)
    # ==========================================
    path("", views.home, name="home"),                                    # หน้าแรก: แสดงรายการสินค้า
    path("product/<int:product_id>/", views.product_detail, name="product_detail"),  # หน้ารายละเอียดสินค้า

    # ==========================================
    # เส้นทางตะกร้าสินค้า (Cart URLs)
    # ==========================================
    path("cart/", views.cart_detail, name="cart_detail"),                  # หน้าตะกร้าสินค้า
    path("cart/add/<int:product_id>/", views.cart_add, name="cart_add"),   # เพิ่มสินค้าลงตะกร้า
    path("cart/update/<int:item_id>/", views.cart_update_qty, name="cart_update_qty"),  # อัปเดตจำนวนในตะกร้า
    path("cart/remove/<int:item_id>/", views.cart_remove, name="cart_remove"),          # ลบสินค้าออกจากตะกร้า

    # ==========================================
    # เส้นทางจัดการสินค้า — Admin Panel
    # เฉพาะ Superuser เท่านั้น
    # ==========================================
    path("admin-panel/products/", views.admin_product_list, name="admin_product_list"),  # หน้ารายการสินค้า (Admin)
    path("product/create/", views.product_create, name="product_create"),                # เพิ่มสินค้าใหม่
    path("product/update/<int:pk>/", views.product_update, name="product_update"),       # แก้ไขสินค้า
    path("product/delete/<int:pk>/", views.product_delete, name="product_delete"),       # ลบสินค้า (Soft Delete)
]
