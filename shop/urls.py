from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("product/<int:product_id>/", views.product_detail, name="product_detail"),

    path("cart/", views.cart_detail, name="cart_detail"),
    path("cart/add/<int:product_id>/", views.cart_add, name="cart_add"),
    path("cart/update/<int:item_id>/", views.cart_update_qty, name="cart_update_qty"),
    path("cart/remove/<int:item_id>/", views.cart_remove, name="cart_remove"),

    # Admin product URLs
    path("admin-panel/products/", views.admin_product_list, name="admin_product_list"),
    path("product/create/", views.product_create, name="product_create"),
    path("product/update/<int:pk>/", views.product_update, name="product_update"),
    path("product/delete/<int:pk>/", views.product_delete, name="product_delete"),
]
