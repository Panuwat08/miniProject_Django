from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction

from shop.models import Cart
from .models import ShippingAddress, Order, OrderItem, PaymentSlip, PaymentMethod, OrderStatus, Notification

@login_required
def checkout(request):
    cart = Cart.objects.get(user=request.user)
    if cart.items.count() == 0:
        messages.error(request, "ตะกร้าว่าง")
        return redirect("cart_detail")

    if request.method == "POST":
        full_name = request.POST.get("full_name", "").strip()
        phone = request.POST.get("phone", "").strip()
        address_line = request.POST.get("address_line", "").strip()
        payment_method = request.POST.get("payment_method")

        if not full_name or not phone or not address_line:
            messages.error(request, "กรอกข้อมูลจัดส่งให้ครบ")
            return redirect("checkout")

        if payment_method not in [m[0] for m in PaymentMethod.choices]:
            messages.error(request, "เลือกวิธีชำระเงินไม่ถูกต้อง")
            return redirect("checkout")

        try:
            with transaction.atomic():
                shipping = ShippingAddress.objects.create(
                    user=request.user, full_name=full_name, phone=phone, address_line=address_line
                )

                order = Order.objects.create(
                    user=request.user,
                    shipping=shipping,
                    payment_method=payment_method,
                    status=OrderStatus.PENDING,
                    total=cart.total_price()
                )

                # ย้ายของจาก cart -> order items และตัดสต็อก
                for ci in cart.items.select_related("product"):
                    if ci.qty > ci.product.stock:
                        raise ValueError(f"สินค้า {ci.product.name} สต็อกไม่พอ")

                    OrderItem.objects.create(
                        order=order,
                        product=ci.product,
                        price=ci.product.price,
                        qty=ci.qty
                    )

                    ci.product.stock -= ci.qty
                    ci.product.save()

                cart.items.all().delete()

            Notification.objects.create(
                user=request.user,
                title="สร้างคำสั่งซื้อสำเร็จ",
                message=f"คำสั่งซื้อ #{order.id} ถูกสร้างแล้ว"
            )

            return redirect("order_detail", order_id=order.id)

        except Exception as e:
            messages.error(request, f"ไม่สามารถสร้างคำสั่งซื้อได้: {e}")
            return redirect("checkout")

    return render(request, "orders/checkout.html", {"methods": PaymentMethod.choices, "cart": cart})

@login_required
def order_detail(request, order_id):
    order = get_object_or_404(Order.objects.select_related("shipping"), id=order_id, user=request.user)

    qr_code_img = None
    account_name = None

    if order.status == OrderStatus.PENDING and order.payment_method == PaymentMethod.ONLINE:
        try:
            from promptpay import qrcode as pp_qrcode
            import qrcode
            import base64
            from io import BytesIO
            from django.conf import settings

            # Generate PromptPay Payload
            # ID: Phone or Citizen ID
            payload = pp_qrcode.generate_payload(settings.PROMPTPAY_ID, float(order.total))
            
            # Generate QR Image
            img = qrcode.make(payload)
            buffer = BytesIO()
            img.save(buffer, format="PNG")
            qr_code_img = base64.b64encode(buffer.getvalue()).decode()
            
            account_name = getattr(settings, "PROMPTPAY_NAME", "")
        except Exception as e:
            print(f"Error generating QR: {e}")

    return render(request, "orders/order_detail.html", {
        "order": order,
        "qr_code_img": qr_code_img,
        "account_name": account_name
    })

@login_required
def upload_slip(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)

    if order.payment_method not in [PaymentMethod.TRANSFER, PaymentMethod.ONLINE]:
        messages.error(request, "ออเดอร์นี้ไม่ต้องอัปโหลดสลิป")
        return redirect("order_detail", order_id=order.id)

    if request.method == "POST":
        img = request.FILES.get("slip")
        if not img:
            messages.error(request, "กรุณาเลือกไฟล์รูปสลิป")
            return redirect("upload_slip", order_id=order.id)

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
        return redirect("order_detail", order_id=order.id)

    return render(request, "orders/upload_slip.html", {"order": order})

@login_required
def remove_slip(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    if request.method == "POST":
        if hasattr(order, 'slip'):
            order.slip.delete()
            # Refund status to pending if it was rejected or paid? 
            # Usually if removing slip, we might want to ensure status is PENDING.
            if order.status == OrderStatus.REJECTED: # If it was rejected, resetting gives a chance to upload a new one cleanly
                order.status = OrderStatus.PENDING
                order.save()
            
            messages.success(request, "ลบสลิปเรียบร้อยแล้ว")
        else:
            messages.error(request, "ไม่พบสลิป")
            
    return redirect("order_detail", order_id=order.id)
