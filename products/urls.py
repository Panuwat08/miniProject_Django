from django.urls import path
from . import views

app_name = "products"

urlpatterns = [
    # --- ส่วนลูกค้า (User Display) ---
    
    # [FR-05] หน้าหลักรายการสินค้าอุปกรณ์โรงแรม (Product Landing Page)
    path("", views.product_list, name="product_list"),

    # [FR-08] ระบบค้นหาสินค้า (Search Engine) 
    path("search/", views.product_search, name="product_search"),

    # [FR-06] แสดงสินค้าแยกตามหมวดหมู่ (Category Filtering)
    path("category/<str:slug>/", views.product_by_category, name="product_by_category"),

    # [FR-07] หน้ารายละเอียดสินค้าเชิงลึก (Product Detail Page)
    path("<str:slug>/", views.product_detail, name="product_detail"),

    # --- ส่วนจัดการระบบ (Admin/Stock Management - FR-20, 21, 22) ---
    
    # ลิงก์สร้างสินค้า: /products/manage/create/
    path('manage/create/', views.product_create, name='product_create'),
    
    # ลิงก์แก้ไขสินค้า: /products/manage/update/1/
    path('manage/update/<int:pk>/', views.product_update, name='product_update'),
    
    # ลิงก์ลบสินค้า (Soft Delete): /products/manage/delete/1/
    path('manage/delete/<int:pk>/', views.product_delete, name='product_delete'),
]
