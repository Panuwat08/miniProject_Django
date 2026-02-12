from django.urls import path
from . import views
from . import admin_views

urlpatterns = [
    path("checkout/", views.checkout, name="checkout"),
    path("order/<int:order_id>/", views.order_detail, name="order_detail"),
    path("order/<int:order_id>/slip/", views.upload_slip, name="upload_slip"),

    path("admin-panel/orders/", admin_views.admin_orders, name="admin_orders"),
    path("admin-panel/orders/<int:order_id>/check-slip/", admin_views.admin_check_slip, name="admin_check_slip"),
]
