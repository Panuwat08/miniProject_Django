from django.contrib import admin
from .models import Product

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'stock_qty', 'is_active') # โชว์คอลัมน์เหล่านี้
    search_fields = ('name',)
    list_filter = ('is_active',) # กรองดูสินค้าที่ลบ/ไม่ลบ