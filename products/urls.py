# ไฟล์: products/urls.py (สร้างใหม่)
from django.urls import path
from . import views

urlpatterns = [
    # ลิงก์เข้าหน้าแรกของสินค้า (localhost:8000/products/)
    path('', views.product_list, name='product_list'),
    
    # ลิงก์สร้างสินค้า (localhost:8000/products/create/)
    path('create/', views.product_create, name='product_create'),
    
    # ลิงก์แก้ไข (localhost:8000/products/update/1/)
    path('update/<int:pk>/', views.product_update, name='product_update'),
    
    # ลิงก์ลบ (localhost:8000/products/delete/1/)
    path('delete/<int:pk>/', views.product_delete, name='product_delete'),
]