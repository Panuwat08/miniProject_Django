from django.db import models

class Product(models.Model):
    # ข้อมูลทั่วไปของสินค้า (ใช้ร่วมกับกลุ่ม 2)
    name = models.CharField(max_length=200, verbose_name="ชื่อสินค้า")
    description = models.TextField(verbose_name="รายละเอียดสินค้า", blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="ราคา (บาท)")
    
    # รูปภาพ (สำคัญมากสำหรับหน้าเว็บ)
    image = models.ImageField(upload_to='product_images/', verbose_name="รูปสินค้า", null=True, blank=True)
    
    # ส่วนจัดการสต็อก (งานหลักของคุณ FR-21, FR-22)
    stock_qty = models.IntegerField(default=0, verbose_name="จำนวนคงเหลือ")
    
    # ส่วน Soft Delete (FR-20: ลบสินค้าแบบไม่หายจริง) [cite: 40]
    is_active = models.BooleanField(default=True, verbose_name="สถานะการขาย") 
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    # ฟังก์ชันเช็คสต็อกก่อนขาย (FR-22)
    def can_sell(self, amount):
        return self.stock_qty >= amount and self.is_active