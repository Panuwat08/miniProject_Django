"""มุมมองของระบบคำสั่งซื้อ เช่น checkout รายละเอียดออเดอร์ สลิป และเอกสารคำสั่งซื้อ"""

import os

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from shop.models import Cart

from .models import (
    cancel_expired_online_orders,
    Notification,
    Order,
    OrderItem,
    OrderStatus,
    PaymentMethod,
    PaymentSlip,
    ShippingAddress,
)


CUSTOMER_CANCEL_REASONS = [
    "สั่งซื้อผิดรายการ",
    "ต้องการเปลี่ยนสินค้า",
    "เปลี่ยนใจยังไม่ต้องการสินค้า",
    "ต้องการแก้ไขข้อมูลจัดส่ง",
    "พบราคาหรือรายละเอียดไม่ตรงตามต้องการ",
]


def _register_thai_pdf_fonts():
    """ลงทะเบียนฟอนต์ภาษาไทยสำหรับการสร้าง PDF ด้วย ReportLab"""
    regular_name = "TahomaThai"
    bold_name = "TahomaThai-Bold"

    if regular_name not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont(regular_name, os.path.join(os.environ["WINDIR"], "Fonts", "tahoma.ttf")))

    if bold_name not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont(bold_name, os.path.join(os.environ["WINDIR"], "Fonts", "tahomabd.ttf")))

    return regular_name, bold_name


def _require_customer(request):
    """บังคับให้ flow คำสั่งซื้อใช้งานได้เฉพาะลูกค้า"""
    if not request.user.is_authenticated:
        messages.error(request, "กรุณาเข้าสู่ระบบก่อนใช้งาน")
        return redirect("login")
    if not request.user.profile.is_customer():
        return redirect("dashboard")
    return None


def deduct_order_stock(order):
    """ตัดสต็อกจากรายการสินค้าในออเดอร์เมื่อออเดอร์ได้รับการอนุมัติ"""
    if order.stock_deducted:
        return

    # ตรวจสอบก่อนว่าทุกสินค้ามีจำนวนเพียงพอสำหรับตัดสต็อกจริง
    for item in order.items.select_related("product"):
        if item.qty > item.product.stock:
            raise ValueError(f"สินค้า {item.product.name} สต็อกไม่พอ")

    # เมื่อผ่านการตรวจสอบแล้วจึงค่อยลดสต็อกทีละรายการ
    for item in order.items.select_related("product"):
        item.product.stock -= item.qty
        item.product.save()

    order.stock_deducted = True
    order.save(update_fields=["stock_deducted"])


def restore_order_stock(order):
    """คืนสต็อกกลับในกรณีที่ต้องย้อนสถานะออเดอร์ที่เคยตัดสต็อกไปแล้ว"""
    if not order.stock_deducted:
        return

    for item in order.items.select_related("product"):
        item.product.stock += item.qty
        item.product.save()

    order.stock_deducted = False
    order.save(update_fields=["stock_deducted"])


@login_required
def checkout(request):
    """สร้างคำสั่งซื้อจากตะกร้า พร้อมบันทึกที่อยู่จัดส่งและวิธีชำระเงิน"""
    blocked = _require_customer(request)
    if blocked:
        return blocked

    cart = get_object_or_404(Cart, user=request.user)
    if cart.items.count() == 0:
        messages.error(request, "ตะกร้าว่าง")
        return redirect("cart_detail")

    initial_full_name = request.user.get_full_name().strip() or request.user.username
    initial_phone = getattr(request.user.profile, "phone", "") or ""
    initial_address = ""

    # ดึงข้อมูลจัดส่งล่าสุดมาเติมฟอร์มให้ลูกค้าเพื่อลดการกรอกซ้ำ
    latest_shipping = ShippingAddress.objects.filter(user=request.user).order_by("-created_at").first()
    if latest_shipping:
        if not initial_full_name or initial_full_name == request.user.username:
            initial_full_name = latest_shipping.full_name
        if not initial_phone:
            initial_phone = latest_shipping.phone
        initial_address = latest_shipping.address_line

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
                # ใช้ transaction เพื่อไม่ให้เกิดออเดอร์ค้างครึ่งทาง
                shipping = ShippingAddress.objects.create(
                    user=request.user,
                    full_name=full_name,
                    phone=phone,
                    address_line=address_line,
                )

                order = Order.objects.create(
                    user=request.user,
                    shipping=shipping,
                    payment_method=payment_method,
                    status=OrderStatus.PENDING,
                    total=cart.total_price(),
                )

                for ci in cart.items.select_related("product"):
                    # ตรวจสต็อกอีกครั้งก่อนย้ายรายการจากตะกร้ามาเป็นออเดอร์
                    if ci.qty > ci.product.stock:
                        raise ValueError(f"สินค้า {ci.product.name} สต็อกไม่พอ")

                    OrderItem.objects.create(
                        order=order,
                        product=ci.product,
                        price=ci.product.price,
                        cost=ci.product.cost,
                        qty=ci.qty,
                    )

                # ล้างตะกร้าหลังสร้างออเดอร์สำเร็จแล้วเท่านั้น
                cart.items.all().delete()

            Notification.objects.create(
                user=request.user,
                title="สร้างคำสั่งซื้อสำเร็จ",
                message=f"คำสั่งซื้อ #{order.id} ถูกสร้างแล้ว",
            )
            return redirect("order_detail", order_id=order.id)
        except Exception as e:
            messages.error(request, f"ไม่สามารถสร้างคำสั่งซื้อได้: {e}")
            return redirect("checkout")

    return render(
        request,
        "orders/checkout.html",
        {
            "methods": PaymentMethod.choices,
            "cart": cart,
            "initial_full_name": initial_full_name,
            "initial_phone": initial_phone,
            "initial_address": initial_address,
        },
    )


@login_required
def order_detail(request, order_id):
    """แสดงรายละเอียดคำสั่งซื้อ สถานะ และ QR Code สำหรับออเดอร์ออนไลน์"""
    blocked = _require_customer(request)
    if blocked:
        return blocked

    cancel_expired_online_orders()

    order = get_object_or_404(Order.objects.select_related("shipping"), id=order_id, user=request.user)
    qr_code_img = None
    account_name = None

    if order.status == OrderStatus.PENDING and order.payment_method == PaymentMethod.ONLINE:
        # สร้าง QR Code แบบ base64 เพื่อฝังภาพลงหน้าเว็บได้ทันที
        try:
            import base64
            from io import BytesIO

            import qrcode
            from django.conf import settings
            from promptpay import qrcode as pp_qrcode

            payload = pp_qrcode.generate_payload(settings.PROMPTPAY_ID, float(order.total))
            img = qrcode.make(payload)
            buffer = BytesIO()
            img.save(buffer, format="PNG")
            qr_code_img = base64.b64encode(buffer.getvalue()).decode()
            account_name = getattr(settings, "PROMPTPAY_NAME", "")
        except Exception:
            qr_code_img = None

    return render(
        request,
        "orders/order_detail.html",
        {
            "order": order,
            "qr_code_img": qr_code_img,
            "account_name": account_name,
            "customer_cancel_reasons": CUSTOMER_CANCEL_REASONS,
        },
    )


@login_required
def cancel_order(request, order_id):
    """เปิดให้ลูกค้ายกเลิกคำสั่งซื้อที่ยังรอดำเนินการ พร้อมบันทึกเหตุผล"""
    blocked = _require_customer(request)
    if blocked:
        return blocked

    cancel_expired_online_orders()

    order = get_object_or_404(Order, id=order_id, user=request.user)
    if request.method != "POST":
        return redirect("order_detail", order_id=order.id)

    if not order.can_customer_cancel():
        messages.error(request, "คำสั่งซื้อนี้ไม่สามารถยกเลิกได้แล้ว")
        return redirect("order_detail", order_id=order.id)

    selected_reasons = request.POST.getlist("cancel_reasons")
    other_reason = request.POST.get("cancel_reason_other", "").strip()

    if not selected_reasons and not other_reason:
        messages.error(request, "กรุณาเลือกหรือระบุเหตุผลในการยกเลิกคำสั่งซื้อ")
        return redirect("order_detail", order_id=order.id)

    reason_parts = selected_reasons[:]
    if other_reason:
        reason_parts.append(f"อื่น ๆ: {other_reason}")

    order.status = OrderStatus.CANCELLED
    order.review_note = "ลูกค้ายกเลิกคำสั่งซื้อ เนื่องจาก " + ", ".join(reason_parts)
    order.save(update_fields=["status", "review_note"])

    Notification.objects.create(
        user=request.user,
        title="ยกเลิกคำสั่งซื้อสำเร็จ",
        message=f"คำสั่งซื้อ {order.order_code} ถูกยกเลิกเรียบร้อยแล้ว",
    )

    messages.success(request, "ยกเลิกคำสั่งซื้อเรียบร้อยแล้ว")
    return redirect("order_detail", order_id=order.id)


@login_required
def order_receipt(request, order_id):
    """แสดงหน้าใบสั่งซื้อสินค้าสำหรับออเดอร์ที่ผ่านเงื่อนไขการออกเอกสารแล้ว"""
    blocked = _require_customer(request)
    if blocked:
        return blocked

    cancel_expired_online_orders()

    order = get_object_or_404(Order.objects.select_related("shipping"), id=order_id, user=request.user)
    if not order.can_download_purchase_order():
        messages.error(request, "ไม่พบเอกสารคำสั่งซื้อ")
        return redirect("order_detail", order_id=order.id)

    return render(
        request,
        "orders/receipt.html",
        {
            "order": order,
            "shop_name": getattr(settings, "PROMPTPAY_NAME", "Hotel Shop"),
            "shop_email": getattr(settings, "DEFAULT_FROM_EMAIL", "Hotel Shop"),
        },
    )


@login_required
def download_receipt(request, order_id):
    """สร้างใบสั่งซื้อสินค้า PDF ให้ลูกค้าดาวน์โหลดเก็บไว้"""
    blocked = _require_customer(request)
    if blocked:
        return blocked

    cancel_expired_online_orders()

    order = get_object_or_404(
        Order.objects.select_related("shipping").prefetch_related("items__product"),
        id=order_id,
        user=request.user,
    )
    if not order.can_download_purchase_order():
        messages.error(request, "ไม่พบเอกสารคำสั่งซื้อ")
        return redirect("order_detail", order_id=order.id)

    regular_font, bold_font = _register_thai_pdf_fonts()
    logo_path = settings.BASE_DIR / "static" / "img" / "logo.png"
    response = HttpResponse(content_type="application/pdf")
    purchase_order_code = order.order_code.replace("ORD", "PO", 1)
    response["Content-Disposition"] = f'attachment; filename="{purchase_order_code}.pdf"'

    document = SimpleDocTemplate(
        response,
        pagesize=A4,
        leftMargin=30,
        rightMargin=30,
        topMargin=30,
        bottomMargin=30,
    )

    styles = getSampleStyleSheet()
    styles["Title"].fontName = bold_font
    styles["Title"].fontSize = 18
    styles["Normal"].fontName = regular_font
    styles["Normal"].fontSize = 10

    label_style = styles["Normal"].clone("OrderDocumentLabel")
    label_style.fontName = bold_font
    label_style.fontSize = 10

    value_style = styles["Normal"].clone("OrderDocumentValue")
    value_style.fontName = regular_font
    value_style.fontSize = 10

    price_style = styles["Normal"].clone("OrderDocumentPrice")
    price_style.fontName = regular_font
    price_style.fontSize = 10
    price_style.alignment = TA_RIGHT

    # วางโครงเอกสารคำสั่งซื้อเป็นส่วนหัว ข้อมูลลูกค้า ตารางรายการ และสรุปยอด
    elements = []

    if logo_path.exists():
        logo = Image(str(logo_path), width=72, height=72)
        logo.hAlign = "LEFT"
        elements.extend([logo, Spacer(1, 8)])

    title_table = Table(
        [
            [
                Paragraph("ใบสั่งซื้อสินค้า", styles["Title"]),
                Paragraph(
                    f'<para align="right"><font name="{bold_font}" size="9" color="white"><nobr>{purchase_order_code}</nobr></font></para>',
                    styles["Normal"],
                ),
            ]
        ],
        colWidths=[360, 140],
    )
    title_table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("BACKGROUND", (1, 0), (1, 0), colors.black),
                ("LEFTPADDING", (1, 0), (1, 0), 12),
                ("RIGHTPADDING", (1, 0), (1, 0), 12),
                ("TOPPADDING", (1, 0), (1, 0), 8),
                ("BOTTOMPADDING", (1, 0), (1, 0), 8),
            ]
        )
    )
    elements.extend([title_table, Spacer(1, 18)])

    shop_info = [
        Paragraph("ร้านค้าที่ให้บริการ", label_style),
        Paragraph(getattr(settings, "PROMPTPAY_NAME", "Hotel Shop"), value_style),
        Paragraph("ระบบขายสินค้าโรงแรม", value_style),
        Paragraph("อีเมลติดต่อ: hotelshop@gmail.com", value_style),
    ]
    customer_info = [
        Paragraph("รายละเอียดลูกค้าคนสำคัญ", label_style),
        Paragraph(order.shipping.full_name, value_style),
        Paragraph(f"วันที่สั่งซื้อ {order.created_at.strftime('%d/%m/%Y %H:%M')} น.", value_style),
        Paragraph(f"เบอร์โทร {order.shipping.phone}", value_style),
    ]
    info_table = Table([[shop_info, customer_info]], colWidths=[245, 255])
    info_table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    elements.extend([info_table, Spacer(1, 18)])

    table_data = [[Paragraph("จำนวน", label_style), Paragraph("รายการสินค้า", label_style), Paragraph("ราคา", price_style)]]
    for index, item in enumerate(order.items.select_related("product"), start=1):
        table_data.append(
            [
                Paragraph(str(item.qty), value_style),
                Paragraph(item.product.name, value_style),
                Paragraph(f"{float(item.subtotal()):,.2f}", price_style),
            ]
        )

    order_table = Table(table_data, colWidths=[80, 335, 120])
    order_table.setStyle(
        TableStyle(
            [
                ("LINEABOVE", (0, 0), (-1, 0), 1.1, colors.black),
                ("LINEBELOW", (0, 0), (-1, 0), 1.1, colors.black),
                ("LINEBELOW", (0, -1), (-1, -1), 1.1, colors.black),
                ("FONTNAME", (0, 0), (-1, 0), bold_font),
                ("FONTNAME", (0, 1), (-1, -1), regular_font),
                ("ALIGN", (0, 0), (0, -1), "LEFT"),
                ("ALIGN", (1, 0), (1, -1), "LEFT"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN", (2, 0), (2, -1), "RIGHT"),
                ("LEFTPADDING", (0, 0), (0, -1), 6),
                ("LEFTPADDING", (1, 0), (1, -1), 8),
                ("RIGHTPADDING", (2, 0), (2, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    elements.extend([order_table, Spacer(1, 16)])

    note_box = Table(
        [[Paragraph("หมายเหตุ", label_style)], [Paragraph(order.review_note or "-", value_style)]],
        colWidths=[240],
        rowHeights=[26, 80],
    )
    note_box.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f3f4f6")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )

    summary_table = Table(
        [
            [Paragraph("ทั้งหมด", value_style), Paragraph(f"{float(order.total):,.2f} บาท", value_style)],
            [Paragraph("ส่วนลด", value_style), Paragraph("0.00 บาท", value_style)],
            [Paragraph("ค่าจัดส่ง", value_style), Paragraph("0.00 บาท", value_style)],
            [Paragraph("รวมราคาสุทธิ", label_style), Paragraph(f"{float(order.total):,.2f} บาท", label_style)],
        ],
        colWidths=[160, 120],
    )
    summary_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 3), (-1, 3), colors.HexColor("#f3f4f6")),
                ("FONTNAME", (0, 0), (-1, -1), regular_font),
                ("FONTNAME", (0, 3), (-1, 3), bold_font),
                ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )

    footer_table = Table([[note_box, summary_table]], colWidths=[250, 250])
    footer_table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )

    elements.extend(
        [
            footer_table,
            Spacer(1, 18),
            Paragraph(
                f'<para align="center"><font name="{regular_font}" size="10">ขอบคุณที่ใช้บริการ (Thank you)</font></para>',
                styles["Normal"],
            ),
        ]
    )

    document.build(elements)
    return response


@login_required
def orders_list(request):
    """แสดงรายการคำสั่งซื้อทั้งหมดของลูกค้าปัจจุบัน"""
    blocked = _require_customer(request)
    if blocked:
        return blocked

    cancel_expired_online_orders()

    orders = (
        Order.objects.filter(user=request.user)
        .select_related("shipping")
        .prefetch_related("items__product")
        .order_by("-created_at")
    )
    return render(request, "orders/orders_list.html", {"orders": orders})


@login_required
def upload_slip(request, order_id):
    """อัปโหลดหรือเปลี่ยนสลิปสำหรับคำสั่งซื้อแบบ QR Code"""
    blocked = _require_customer(request)
    if blocked:
        return blocked

    cancel_expired_online_orders()

    order = get_object_or_404(Order, id=order_id, user=request.user)

    if order.payment_method != PaymentMethod.ONLINE:
        messages.error(request, "ออเดอร์นี้ไม่ต้องอัปโหลดสลิป")
        return redirect("order_detail", order_id=order.id)

    if request.method == "POST":
        img = request.FILES.get("slip")
        if not img:
            messages.error(request, "กรุณาเลือกไฟล์รูปสลิป")
            return redirect("upload_slip", order_id=order.id)

        # รองรับทั้งการอัปโหลดครั้งแรกและการอัปเดตสลิปเดิม
        slip, _ = PaymentSlip.objects.get_or_create(order=order)
        slip.image = img
        slip.approved = None
        slip.note = ""
        slip.checked_at = None
        slip.save()

        if order.status == OrderStatus.REJECTED:
            order.status = OrderStatus.PENDING
            order.save(update_fields=["status"])

        Notification.objects.create(
            user=request.user,
            title="อัปโหลดสลิปสำเร็จ",
            message=f"ระบบได้รับสลิปของคำสั่งซื้อ #{order.id} แล้ว กำลังรอตรวจสอบ",
        )

        messages.success(request, "อัปโหลดสลิปสำเร็จ")
        return redirect("upload_slip", order_id=order.id)

    return render(request, "orders/upload_slip.html", {"order": order})


@login_required
def remove_slip(request, order_id):
    """ลบสลิปการชำระเงินออกจากออเดอร์ของลูกค้า"""
    blocked = _require_customer(request)
    if blocked:
        return blocked

    cancel_expired_online_orders()

    order = get_object_or_404(Order, id=order_id, user=request.user)

    if request.method == "POST":
        if hasattr(order, "slip"):
            order.slip.delete()
            if order.status == OrderStatus.REJECTED:
                order.status = OrderStatus.PENDING
                order.save(update_fields=["status"])
            messages.success(request, "ลบสลิปเรียบร้อยแล้ว")
        else:
            messages.error(request, "ไม่พบสลิป")

    return redirect("order_detail", order_id=order.id)
