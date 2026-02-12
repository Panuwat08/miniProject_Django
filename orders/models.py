from django.db import models
from django.contrib.auth.models import User
from shop.models import Product

class PaymentMethod(models.TextChoices):
    COD = "COD", "เก็บเงินปลายทาง"
    TRANSFER = "TRANSFER", "โอนเงิน"
    ONLINE = "ONLINE", "ออนไลน์"

class OrderStatus(models.TextChoices):
    PENDING = "PENDING", "รอชำระเงิน/รอตรวจสอบ"
    PAID = "PAID", "ชำระแล้ว"
    REJECTED = "REJECTED", "สลิปไม่ถูกต้อง"
    SHIPPED = "SHIPPED", "จัดส่งแล้ว"
    COMPLETED = "COMPLETED", "สำเร็จ"
    CANCELLED = "CANCELLED", "ยกเลิก"

class ShippingAddress(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    full_name = models.CharField(max_length=255)
    phone = models.CharField(max_length=30)
    address_line = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

class Order(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    shipping = models.ForeignKey(ShippingAddress, on_delete=models.PROTECT)
    payment_method = models.CharField(max_length=20, choices=PaymentMethod.choices)
    status = models.CharField(max_length=20, choices=OrderStatus.choices, default=OrderStatus.PENDING)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)

class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name="items", on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    qty = models.PositiveIntegerField()

    def subtotal(self):
        return self.price * self.qty

class PaymentSlip(models.Model):
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name="slip")
    image = models.ImageField(upload_to="slips/")
    approved = models.BooleanField(null=True, blank=True)  # None=ยังไม่ตรวจ, True=ผ่าน, False=ไม่ผ่าน
    note = models.TextField(blank=True, default="")
    checked_at = models.DateTimeField(null=True, blank=True)

class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
