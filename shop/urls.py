from django.contrib.admin.views.decorators import staff_member_required
from django.urls import path

from . import views


urlpatterns = [
    path("", views.home, name="home"),
    path("product/<int:product_id>/", views.product_detail, name="product_detail"),

    path("cart/", views.cart_detail, name="cart_detail"),
    path("cart/add/<int:product_id>/", views.cart_add, name="cart_add"),
    path("cart/update/<int:item_id>/", views.cart_update_qty, name="cart_update_qty"),
    path("cart/remove/<int:item_id>/", views.cart_remove, name="cart_remove"),

    path("admin-panel/products/", staff_member_required(views.admin_product_list), name="admin_product_list"),
    path("admin-panel/categories/", staff_member_required(views.admin_category_list), name="admin_category_list"),
    path("admin-panel/categories/create/", staff_member_required(views.category_create), name="category_create"),
    path("admin-panel/categories/update/<int:pk>/", staff_member_required(views.category_update), name="category_update"),
    path("admin-panel/categories/delete/<int:pk>/", staff_member_required(views.category_delete), name="category_delete"),
    path("admin-panel/categories/enable/<int:pk>/", staff_member_required(views.category_enable), name="category_enable"),
    path("admin-panel/categories/remove/<int:pk>/", staff_member_required(views.category_remove), name="category_remove"),

    path("product/create/", staff_member_required(views.product_create), name="product_create"),
    path("product/update/<int:pk>/", staff_member_required(views.product_update), name="product_update"),
    path("product/delete/<int:pk>/", staff_member_required(views.product_delete), name="product_delete"),
]
