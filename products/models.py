from django.db import models
from django.utils.text import slugify

# [กลุ่มที่ 2] ระบบจัดการสินค้าและหมวดหมู่ (แสดงสินค้า - หมวดอุปกรณ์โรงแรม)
# รายละเอียดความต้องการ (Requirements):
# FR-05: ระบบต้องแสดงรายการสินค้า (Product List)
# FR-06: ระบบต้องแสดงสินค้าแยกตามหมวด (Category Filter)
# FR-07: ระบบต้องแสดงรายละเอียดสินค้า (Product Detail)
# FR-08: ระบบต้องรองรับการค้นหาสินค้า (Search System)

class Category(models.Model):
    """
    [FR-06] หมวดหมู่สินค้า: ใช้หลักการแยกแยะสินค้าตามประเภทการใช้งาน (เช่น ของใช้ในห้องน้ำ, เครื่องนอน)
    """
    name = models.CharField("ชื่อหมวดหมู่", max_length=255, unique=True)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    image = models.ImageField("รูปหมวดหมู่", upload_to="categories/", null=True, blank=True)
    is_active = models.BooleanField("เปิดใช้งาน", default=True) # สถานะเปิด/ปิดการแสดงผล
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "หมวดหมู่"
        verbose_name_plural = "หมวดหมู่"
        ordering = ["name"] # เรียงตามชื่อเพื่อให้อ่านง่าย

    def save(self, *args, **kwargs):
        # สร้าง Slug อัตโนมัติจากชื่อสินค้าเพื่อความสวยงามของ URL (SEO-Friendly)
        if not self.slug:
            self.slug = slugify(self.name, allow_unicode=True)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Product(models.Model):
    """
    [FR-05, FR-07, FR-20, FR-21, FR-22] สินค้าอุปกรณ์โรงแรม: เก็บข้อมูลเชิงลึกสำหรับผู้ซื้อเชิงพาณิชย์และการจัดการสต็อก
    """
    # เชื่อมโยงกับหมวดหมู่ (FR-06)
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="products",
        verbose_name="หมวดหมู่",
    )
    name = models.CharField("ชื่อสินค้า", max_length=255)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    description = models.TextField("รายละเอียด", blank=True, default="")
    price = models.DecimalField("ราคา", max_digits=10, decimal_places=2)
    
    # ส่วนจัดการสต็อก (FR-21, FR-22) - ใช้ชื่อ stock_qty ตามกลุ่มจัดการสต็อก
    stock_qty = models.PositiveIntegerField("จำนวนสต็อก", default=0) 
    
    # รูปภาพ
    image = models.ImageField("รูปสินค้า", upload_to="products/", null=True, blank=True)
    
    # สถานะ (FR-20: Soft Delete)
    is_active = models.BooleanField("เปิดใช้งาน", default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "สินค้า"
        verbose_name_plural = "สินค้า"
        ordering = ["-created_at"] # สินค้าใหม่จะอยู่ด้านบนสุด

    def save(self, *args, **kwargs):
        # สร้าง Slug อัตโนมัติ รองรับภาษาไทยใน URL
        if not self.slug:
            self.slug = slugify(self.name, allow_unicode=True)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    # ฟังก์ชันเช็คสต็อกก่อนขาย (FR-22)
    def can_sell(self, amount):
        return self.stock_qty >= amount and self.is_active
