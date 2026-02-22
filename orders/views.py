from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction

from shop.models import Cart
from .models import (
    ShippingAddress, Order, OrderItem, PaymentSlip,
    PaymentMethod, OrderStatus, Notification
)

import io
import qrcode
from decimal import Decimal, InvalidOperation
from django.http import HttpResponse
from django.views.decorators.http import require_GET


@login_required
def checkout(request):
    cart, _ = Cart.objects.get_or_create(user=request.user)
    cart_items_qs = cart.items.select_related("product").all()

    if cart_items_qs.count() == 0:
        messages.error(request, "ตะกร้าว่าง")
        return redirect("cart_detail")

    try:
        total = cart.total_price() if callable(getattr(cart, "total_price", None)) else cart.total_price
    except Exception:
        total = 0

    if request.method == "POST":
        full_name = request.POST.get("full_name", "").strip()
        phone = request.POST.get("phone", "").strip()
        address_line = request.POST.get("address_line", "").strip()
        payment_method = (request.POST.get("payment_method") or "").strip()

        slip_img = request.FILES.get("slip")  # ✅ รับสลิปจากหน้า checkout

        if not full_name or not phone or not address_line:
            messages.error(request, "กรอกข้อมูลจัดส่งให้ครบ")
            return redirect("orders:checkout")

        valid_methods = [m[0] for m in PaymentMethod.choices]
        if payment_method not in valid_methods:
            messages.error(request, "เลือกวิธีชำระเงินไม่ถูกต้อง")
            return redirect("orders:checkout")

        # ✅ ถ้าเลือก TRANSFER ต้องแนบสลิป
        if payment_method == PaymentMethod.TRANSFER:
            if not slip_img:
                messages.error(request, "กรุณาแนบสลิปการชำระเงิน")
                return redirect("orders:checkout")
            if not (slip_img.content_type or "").startswith("image/"):
                messages.error(request, "ไฟล์สลิปต้องเป็นรูปภาพเท่านั้น")
                return redirect("orders:checkout")

        try:
            with transaction.atomic():
                shipping = ShippingAddress.objects.create(
                    user=request.user,
                    full_name=full_name,
                    phone=phone,
                    address_line=address_line
                )

                order = Order.objects.create(
                    user=request.user,
                    shipping=shipping,
                    payment_method=payment_method,
                    status=OrderStatus.PENDING,  # ของคุณ: รอชำระเงิน/รอตรวจสอบ
                    total=total
                )

                for ci in cart_items_qs:
                    if ci.qty > ci.product.stock:
                        raise ValueError(f"สินค้า {ci.product.name} สต็อกไม่พอ (คงเหลือ {ci.product.stock})")

                    OrderItem.objects.create(
                        order=order,
                        product=ci.product,
                        price=ci.product.price,
                        qty=ci.qty
                    )

                    ci.product.stock -= ci.qty
                    ci.product.save(update_fields=["stock"])

                # ✅ ถ้าเป็นโอนเงิน -> เก็บสลิปตั้งแต่ checkout
                if payment_method == PaymentMethod.TRANSFER and slip_img:
                    PaymentSlip.objects.create(
                        order=order,
                        image=slip_img,
                        approved=None,
                        note="",
                        checked_at=None
                    )

                cart.items.all().delete()

            Notification.objects.create(
                user=request.user,
                title="สร้างคำสั่งซื้อสำเร็จ",
                message=f"คำสั่งซื้อ #{order.id} ถูกสร้างแล้ว"
            )

            return redirect("orders:order_detail", order_id=order.id)

        except Exception as e:
            messages.error(request, f"ไม่สามารถสร้างคำสั่งซื้อได้: {e}")
            return redirect("orders:checkout")

    return render(request, "orders/checkout.html", {
        "cart": cart,
        "items": cart_items_qs,
        "total": total,
        "PaymentMethod": PaymentMethod,  # ✅ จำเป็นสำหรับ dropdown + JS
    })

@login_required
def order_detail(request, order_id):
    order = get_object_or_404(
        Order.objects.select_related("shipping"),
        id=order_id,
        user=request.user
    )
    return render(request, "orders/order_detail.html", {"order": order})


@login_required
def upload_slip(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)

    # ✅ แก้เงื่อนไขให้ตรงกับวิธีชำระเงินจริงของคุณ
    # ถ้า PROMPTPAY ต้องอัปโหลดสลิป แต่ COD ไม่ต้อง
    if order.payment_method == PaymentMethod.COD:
        messages.error(request, "ออเดอร์นี้ไม่ต้องอัปโหลดสลิป (เก็บเงินปลายทาง)")
        return redirect("orders:order_detail", order_id=order.id)

    if request.method == "POST":
        img = request.FILES.get("slip")
        if not img:
            messages.error(request, "กรุณาเลือกไฟล์รูปสลิป")
            return redirect("orders:upload_slip", order_id=order.id)

        # ✅ validate เบื้องต้น
        if not (img.content_type or "").startswith("image/"):
            messages.error(request, "ไฟล์ต้องเป็นรูปภาพเท่านั้น")
            return redirect("orders:upload_slip", order_id=order.id)

        slip, _ = PaymentSlip.objects.get_or_create(order=order)
        slip.image = img
        slip.approved = None
        slip.note = ""
        slip.checked_at = None
        slip.save()

        Notification.objects.create(
            user=request.user,
            title="อัปโหลดสลิปสำเร็จ",
            message=f"ระบบได้รับสลิปของคำสั่งซื้อ #{order.id} แล้ว กำลังรอตรวจสอบ"
        )

        messages.success(request, "อัปโหลดสลิปสำเร็จ")
        return redirect("orders:order_detail", order_id=order.id)

    return render(request, "orders/upload_slip.html", {"order": order})


from decimal import Decimal, ROUND_HALF_UP

def _tlv(tag: str, value: str) -> str:
    length = len(value)
    return f"{tag}{length:02d}{value}"

def _crc16_ccitt_false(data: str) -> str:
    # CRC-16/CCITT-FALSE (poly 0x1021, init 0xFFFF)
    crc = 0xFFFF
    for ch in data.encode("ascii"):
        crc ^= (ch << 8)
        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) ^ 0x1021) & 0xFFFF
            else:
                crc = (crc << 1) & 0xFFFF
    return f"{crc:04X}"

def _format_amount(amount: Decimal) -> str:
    # ให้เป็น 2 ตำแหน่งเสมอ
    amt = amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return f"{amt:.2f}"

def _normalize_promptpay_id(promptpay_id: str, id_type: str) -> str:
    """
    id_type:
      - "PHONE": เบอร์มือถือไทย เช่น 0812345678
      - "NID": เลขบัตรประชาชน 13 หลัก
    """
    raw = "".join([c for c in str(promptpay_id) if c.isdigit()])

    if id_type == "PHONE":
        # รับรูปแบบ 0812345678 หรือ 66812345678 ก็ได้
        if raw.startswith("66"):
            # 66xxxxxxxxx (11 หลัก) -> เติม 00 ให้ครบ 13
            # ให้กลายเป็น 0066 + 9หลักมือถือ
            phone9 = raw[2:]
            if len(phone9) != 9:
                raise ValueError("เบอร์พร้อมเพย์ไม่ถูกต้อง")
            return "0066" + phone9

        # 0xxxxxxxxx (10 หลัก) -> เอา 0 ออก เหลือ 9
        if raw.startswith("0") and len(raw) == 10:
            return "0066" + raw[1:]

        raise ValueError("เบอร์พร้อมเพย์ไม่ถูกต้อง (ควรเป็น 10 หลัก เช่น 0812345678)")

    if id_type == "NID":
        if len(raw) != 13:
            raise ValueError("เลขบัตรประชาชนต้อง 13 หลัก")
        return raw

    raise ValueError("id_type ต้องเป็น PHONE หรือ NID")

def build_promptpay_payload(promptpay_id: str, amount: Decimal, id_type: str = "PHONE") -> str:
    """
    สร้าง PromptPay QR (Thai QR Payment) แบบสแกนจ่ายได้จริง
    - promptpay_id: เบอร์โทรหรือเลขบัตร
    - amount: ยอดเงิน (ถ้าใส่ 0 จะเป็น static QR บางธนาคารจะให้กรอกยอดเอง)
    - id_type: "PHONE" หรือ "NID"
    """
    # 00: Payload Format Indicator
    payload = _tlv("00", "01")

    # 01: Point of Initiation Method
    # 11 = static, 12 = dynamic (มี amount)
    point = "12" if amount and amount > 0 else "11"
    payload += _tlv("01", point)

    # 29: Merchant Account Information (PromptPay)
    gui = _tlv("00", "A000000677010111")  # PromptPay AID
    normalized = _normalize_promptpay_id(promptpay_id, id_type)

    # subtag: 01 = phone, 02 = national id
    subtag = "01" if id_type == "PHONE" else "02"
    acc = gui + _tlv(subtag, normalized)
    payload += _tlv("29", acc)

    # 52: Merchant Category Code
    payload += _tlv("52", "0000")
    # 53: Transaction Currency (764 = THB)
    payload += _tlv("53", "764")
    # 58: Country Code
    payload += _tlv("58", "TH")

    # 54: Transaction Amount (optional)
    if amount and amount > 0:
        payload += _tlv("54", _format_amount(amount))

    # 63: CRC (ต้องต่อ "6304" ก่อนคำนวณ)
    payload_for_crc = payload + "6304"
    crc = _crc16_ccitt_false(payload_for_crc)
    payload += "63" + "04" + crc

    return payload


@require_GET
def promptpay_qr(request):
    amount_str = request.GET.get("amount", "0")

    try:
        amount = Decimal(amount_str)
        if amount < 0:
            amount = Decimal("0")
    except (InvalidOperation, ValueError):
        amount = Decimal("0")

    promptpay_id = "0647810688"
    payload = build_promptpay_payload(promptpay_id, amount)

    img = qrcode.make(payload)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return HttpResponse(buf.getvalue(), content_type="image/png")