from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),

    path("cart/", views.cart_detail, name="cart_detail"),
    path("cart/add/<int:product_id>/", views.cart_add, name="cart_add"),
    path("cart/update/<int:item_id>/", views.cart_update_qty, name="cart_update_qty"),
    path("cart/remove/<int:item_id>/", views.cart_remove, name="cart_remove"),
]
