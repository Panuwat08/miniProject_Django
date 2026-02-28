# ==========================================
# models.py — โมเดลฐานข้อมูลของแอป shop
# กำหนดโครงสร้างตาราง: สินค้า (Product), ตะกร้า (Cart), รายการในตะกร้า (CartItem)
# ==========================================

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


# ==========================================
# โมเดลสินค้า (Product)
# เก็บข้อมูลสินค้าทั้งหมด: ชื่อ, ราคา, สต็อก, รูปภาพ, สถานะ
# ==========================================
class Product(models.Model):
    name = models.CharField(max_length=255)                          # ชื่อสินค้า
    price = models.DecimalField(max_digits=10, decimal_places=2)     # ราคา (ทศนิยม 2 ตำแหน่ง)
    stock = models.PositiveIntegerField(default=0)                   # จำนวนสต็อก (ต้อง >= 0)
    image = models.ImageField(upload_to="products/", null=True, blank=True)  # รูปภาพสินค้า (ไม่บังคับ)
    description = models.TextField(blank=True)                       # รายละเอียดสินค้า (ไม่บังคับ)
    is_active = models.BooleanField(default=True)                    # สถานะ: True=ขายอยู่, False=ถูกลบ (Soft Delete)
    created_at = models.DateTimeField(default=timezone.now)          # วันที่สร้าง
    updated_at = models.DateTimeField(auto_now=True)                 # วันที่อัปเดตล่าสุด (อัปเดตอัตโนมัติ)

    def __str__(self):
        """แสดงชื่อสินค้าเมื่อเรียกใช้ str()"""
        return self.name


# ==========================================
# โมเดลตะกร้าสินค้า (Cart)
# ผู้ใช้ 1 คนมีตะกร้า 1 ใบ (OneToOne)
# ==========================================
class Cart(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)  # เจ้าของตะกร้า (ลบ User = ลบตะกร้า)
    updated_at = models.DateTimeField(auto_now=True)             # วันที่อัปเดตล่าสุด

    def total_price(self):
        """คำนวณราคารวมทั้งหมดในตะกร้า (รวม subtotal ของทุกรายการ)"""
        return sum([item.subtotal() for item in self.items.select_related("product")])


# ==========================================
# โมเดลรายการในตะกร้า (CartItem)
# เก็บว่าตะกร้าไหนมีสินค้าอะไรบ้าง จำนวนเท่าไร
# ==========================================
class CartItem(models.Model):
    cart = models.ForeignKey(Cart, related_name="items", on_delete=models.CASCADE)  # ตะกร้าที่มีรายการนี้
    product = models.ForeignKey(Product, on_delete=models.CASCADE)                  # สินค้าในรายการ
    qty = models.PositiveIntegerField(default=1)                                    # จำนวนสินค้า

    class Meta:
        unique_together = ("cart", "product")  # ป้องกันสินค้าซ้ำในตะกร้าเดียวกัน

    def subtotal(self):
        """คำนวณราคารวมของรายการนี้ (ราคา × จำนวน)"""
        return self.product.price * self.qty
