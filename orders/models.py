from django.contrib.auth.models import User
from django.db import models

from shop.models import Product


class PaymentMethod(models.TextChoices):
    COD = "COD", "เก็บเงินปลายทาง"
    ONLINE = "ONLINE", "ชำระเงินผ่าน QR Code"


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
    review_note = models.TextField(blank=True, default="")
    paid_at = models.DateTimeField(null=True, blank=True)
    stock_deducted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def can_issue_receipt(self):
        return (
            self.payment_method == PaymentMethod.ONLINE
            and self.status in {OrderStatus.PAID, OrderStatus.SHIPPED, OrderStatus.COMPLETED}
        )

    @property
    def order_code(self):
        if not self.pk or not self.created_at:
            return "ORD-PENDING"
        return f"ORD{self.created_at:%Y%m%d}-{self.pk:04d}"

    @property
    def receipt_code(self):
        if not self.pk or not self.created_at:
            return "RC-PENDING"
        return f"RC{self.created_at:%Y%m%d}-{self.pk:04d}"

    def status_label(self):
        if self.payment_method == PaymentMethod.COD:
            if self.status == OrderStatus.PENDING:
                return "รอตรวจสอบข้อมูล"
            if self.status == OrderStatus.PAID:
                return "รอเก็บเงิน"
        if self.payment_method == PaymentMethod.ONLINE and self.status == OrderStatus.PENDING:
            return "รอตรวจสลิป"
        return self.get_status_display()


class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name="items", on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    qty = models.PositiveIntegerField()
    cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def subtotal(self):
        return self.price * self.qty

    def profit(self):
        return (self.price - self.cost) * self.qty


class PaymentSlip(models.Model):
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name="slip")
    image = models.ImageField(upload_to="slips/")
    approved = models.BooleanField(null=True, blank=True)
    note = models.TextField(blank=True, default="")
    checked_at = models.DateTimeField(null=True, blank=True)


class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
