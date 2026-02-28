from django.contrib import admin
from .models import Category, Product

# [กลุ่มที่ 2] การตั้งค่าหน้า Admin สำหรับจัดการสินค้าอุปกรณ์โรงแรม

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "slug", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    # รวมฟิลด์สำคัญจากทั้งระบบแสดงผลและระบบสต็อก
    list_display = ("id", "name", "category", "price", "stock_qty", "is_active", "created_at")
    list_filter = ("is_active", "category")
    search_fields = ("name", "description")
    prepopulated_fields = {"slug": ("name",)}
    list_select_related = ("category",)
