from django.urls import path
from . import views

app_name = "products"

urlpatterns = [
    # [FR-05] หน้าหลักรายการสินค้าอุปกรณ์โรงแรม (Product Landing Page)
    path("", views.product_list, name="product_list"),

    # [FR-08] ระบบค้นหาสินค้า (Search Engine) 
    # หมายเหตุ: ต้องวางก่อน <slug> เพื่อป้องกันการสับสนของ URL Dispatcher
    path("search/", views.product_search, name="product_search"),

    # [FR-06] แสดงสินค้าแยกตามหมวดหมู่ (Category Filtering)
    # ใช้ <str:slug> เพื่อรองรับพารามิเตอร์ที่เป็นอักขระพิเศษหรือภาษาไทย
    path("category/<str:slug>/", views.product_by_category, name="product_by_category"),

    # [FR-07] หน้ารายละเอียดสินค้าเชิงลึก (Product Detail Page)
    path("<str:slug>/", views.product_detail, name="product_detail"),
]
