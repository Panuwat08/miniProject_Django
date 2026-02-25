from django.apps import AppConfig


class ProductsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "products"
    
    # [กลุ่มที่ 2] แสดงชื่อแอปในหน้า Admin ให้ชัดเจน
    verbose_name = "กลุ่ม 2: ระบบจัดการสินค้าและอุปกรณ์โรงแรม"
