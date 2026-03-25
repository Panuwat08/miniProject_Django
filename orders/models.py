"""โมเดลของระบบคำสั่งซื้อ การชำระเงิน และข้อมูลจัดส่ง"""

from datetime import timedelta

from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone

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

    def can_download_purchase_order(self):
        return self.pk is not None

    def can_issue_receipt(self):
        return self.can_download_purchase_order()

    def can_customer_cancel(self):
        return self.status == OrderStatus.PENDING

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

    def has_uploaded_slip(self):
        """ตรวจสอบว่าออเดอร์นี้มีการอัปโหลดสลิปแล้วหรือยัง"""
        return hasattr(self, "slip") and bool(getattr(self.slip, "image", None))

    def status_label(self):
        if self.payment_method == PaymentMethod.COD:
            if self.status == OrderStatus.PENDING:
                return "รอตรวจสอบข้อมูล"
            if self.status == OrderStatus.PAID:
                return "รอเก็บเงิน"
        if self.payment_method == PaymentMethod.ONLINE and self.status == OrderStatus.PENDING:
            if self.has_uploaded_slip():
                return "รอตรวจสอบ"
            return "รอชำระเงิน"
        if self.status == OrderStatus.CANCELLED:
            return "ยกเลิกสินค้า"
        return self.get_status_display()

    def payment_deadline(self):
        """คืนค่าวันเวลาสิ้นสุดการชำระสำหรับออเดอร์ QR Code"""
        if self.payment_method != PaymentMethod.ONLINE:
            return None
        return self.created_at + timedelta(days=3)

    def remaining_payment_seconds(self):
        """คืนค่าจำนวนวินาทีที่เหลือก่อนหมดเวลาชำระเงิน"""
        deadline = self.payment_deadline()
        if not deadline or self.status != OrderStatus.PENDING:
            return None
        return max(0, int((deadline - timezone.now()).total_seconds()))

    def payment_time_left_label(self):
        """แปลงเวลาที่เหลือเป็นข้อความ วัน และ ชั่วโมง สำหรับแสดงบนหน้าเว็บ"""
        remaining = self.remaining_payment_seconds()
        if remaining is None:
            return ""

        days = remaining // 86400
        hours = (remaining % 86400) // 3600
        return f"{days} วัน {hours} ชม."

    def review_deadline(self):
        """คืนค่าวันเวลาสิ้นสุดกรอบตรวจสอบ 24 ชั่วโมงหลังอัปโหลดสลิป"""
        if not self.has_uploaded_slip() or self.status != OrderStatus.PENDING:
            return None
        return self.slip.created_at + timedelta(hours=24)

    def remaining_review_seconds(self):
        """คืนค่าจำนวนวินาทีที่เหลือในกรอบรอตรวจสอบ 24 ชั่วโมง"""
        deadline = self.review_deadline()
        if not deadline:
            return None
        return max(0, int((deadline - timezone.now()).total_seconds()))

    def review_time_left_label(self):
        """แปลงเวลาที่เหลือของการรอตรวจสอบเป็นข้อความ วัน และ ชั่วโมง"""
        remaining = self.remaining_review_seconds()
        if remaining is None:
            return ""

        days = remaining // 86400
        hours = (remaining % 86400) // 3600
        return f"{days} วัน {hours} ชม."


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
    created_at = models.DateTimeField(default=timezone.now)


class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)


def cancel_expired_online_orders():
    """ยกเลิกออเดอร์ QR Code ที่ยังไม่ชำระและค้างเกิน 3 วัน"""
    expired_orders = (
        Order.objects.filter(
            payment_method=PaymentMethod.ONLINE,
            status=OrderStatus.PENDING,
            created_at__lte=timezone.now() - timedelta(days=3),
        )
        .select_related("user")
    )

    cancelled_count = 0
    for order in expired_orders:
        order.status = OrderStatus.CANCELLED
        if not order.review_note:
            order.review_note = "ระบบยกเลิกอัตโนมัติ เนื่องจากไม่ชำระเงินภายใน 3 วัน"
        order.save(update_fields=["status", "review_note"])

        Notification.objects.get_or_create(
            user=order.user,
            title="คำสั่งซื้อถูกยกเลิกอัตโนมัติ",
            message=(
                f"คำสั่งซื้อ {order.order_code} ถูกยกเลิกอัตโนมัติ "
                f"เนื่องจากยังไม่ชำระเงินภายใน 3 วัน"
            ),
        )
        cancelled_count += 1

    return cancelled_count
