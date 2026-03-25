"""มุมมองฝั่งผู้ดูแลสำหรับตรวจสอบ อนุมัติ หรือปฏิเสธคำสั่งซื้อ"""

from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.core.mail import send_mail
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .models import Notification, Order, OrderStatus, PaymentMethod, cancel_expired_online_orders
from .views import deduct_order_stock, restore_order_stock


def _build_result_message(is_qr_order, approved):
    """สร้างข้อความผลลัพธ์ให้เหมาะกับประเภทการชำระเงินและผลตรวจสอบ"""
    if approved:
        if is_qr_order:
            return "สลิปผ่านการตรวจสอบแล้ว"
        return "ข้อมูลคำสั่งซื้อผ่านการตรวจสอบแล้ว"

    if is_qr_order:
        return "สลิปไม่ถูกต้อง กรุณาอัปโหลดใหม่"
    return "คำสั่งซื้อแบบเก็บเงินปลายทางไม่ผ่านการตรวจสอบข้อมูล"


def _build_notification_title(approved):
    """กำหนดหัวข้อแจ้งเตือนตามผลการตรวจสอบคำสั่งซื้อ"""
    if approved:
        return "คำสั่งซื้อได้รับการอนุมัติแล้ว"
    return "คำสั่งซื้อถูกปฏิเสธ"


def _build_notification_message(order, result_message, note):
    """ประกอบข้อความแจ้งเตือนในระบบที่ส่งกลับไปยังลูกค้า"""
    message = f"คำสั่งซื้อ {order.order_code}: {result_message}"
    if note:
        message += f" หมายเหตุ: {note}"
    return message


def _send_order_status_email(order, approved, result_message, note):
    """ส่งอีเมลแจ้งลูกค้าเมื่อออเดอร์ถูกอนุมัติหรือปฏิเสธ"""
    if not order.user.email:
        return

    subject = f"{_build_notification_title(approved)} - {order.order_code}"
    approval_text = "อนุมัติแล้ว" if approved else "ปฏิเสธแล้ว"
    body_lines = [
        f"เรียน {order.shipping.full_name or order.user.username}",
        "",
        "ระบบ Hotel Shop แจ้งอัปเดตสถานะคำสั่งซื้อของคุณ",
        "",
        f"รหัสคำสั่งซื้อ: {order.order_code}",
        f"ชื่อผู้รับสินค้า: {order.shipping.full_name}",
        f"วันที่สั่งซื้อ: {order.created_at.strftime('%d/%m/%Y %H:%M')} น.",
        f"ราคารวมสินค้า: {order.total:.2f} บาท",
        f"สถานะคำสั่งซื้อ: {approval_text}",
        f"สถานะล่าสุดในระบบ: {order.status_label()}",
        f"รายละเอียดเพิ่มเติม: {result_message}",
    ]
    if note:
        body_lines.extend(["", f"หมายเหตุจากผู้ดูแลระบบ: {note}"])
    body_lines.extend(["", "Hotel Shop"])

    send_mail(
        subject=subject,
        message="\n".join(body_lines),
        from_email=None,
        recipient_list=[order.user.email],
        fail_silently=True,
    )


@staff_member_required
def admin_orders(request):
    """หน้ารวมคำสั่งซื้อฝั่งผู้ดูแล พร้อมตัวเลขสรุปสถานะหลัก"""
    cancel_expired_online_orders()

    orders = (
        Order.objects.select_related("user", "shipping")
        .prefetch_related("items__product")
        .order_by("-created_at")
    )
    # รวมตัวเลขสำหรับแสดงบนการ์ดสรุปด้านบนของหน้า
    summary = orders.aggregate(
        total_orders=Count("id"),
        pending_orders=Count("id", filter=Q(status=OrderStatus.PENDING)),
        paid_orders=Count(
            "id",
            filter=Q(status__in=[OrderStatus.PAID, OrderStatus.SHIPPED, OrderStatus.COMPLETED]),
        ),
        rejected_orders=Count(
            "id",
            filter=Q(status__in=[OrderStatus.REJECTED, OrderStatus.CANCELLED]),
        ),
        slip_waiting=Count(
            "id",
            filter=Q(
                payment_method=PaymentMethod.ONLINE,
                status=OrderStatus.PENDING,
                slip__approved__isnull=True,
                slip__isnull=False,
            ),
        ),
        cod_waiting=Count(
            "id",
            filter=Q(payment_method=PaymentMethod.COD, status=OrderStatus.PENDING),
        ),
    )
    return render(
        request,
        "admin/orders_list.html",
        {
            "orders": orders,
            "summary": summary,
            "PaymentMethod": PaymentMethod,
            "OrderStatus": OrderStatus,
        },
    )


@staff_member_required
def admin_check_slip(request, order_id):
    """หน้าตรวจสลิปหรืออนุมัติออเดอร์ COD แล้วแจ้งผลกลับหาลูกค้า"""
    cancel_expired_online_orders()

    order = get_object_or_404(
        Order.objects.select_related("user", "shipping").prefetch_related("items__product"),
        id=order_id,
    )
    slip = getattr(order, "slip", None)
    is_qr_order = order.payment_method == PaymentMethod.ONLINE
    is_cod_order = order.payment_method == PaymentMethod.COD
    is_reviewable = order.status == OrderStatus.PENDING

    if request.method == "POST":
        if not is_reviewable:
            messages.info(request, "คำสั่งซื้อนี้ถูกตรวจสอบแล้ว สามารถดูข้อมูลได้อย่างเดียว")
            return redirect("admin_check_slip", order_id=order.id)

        action = request.POST.get("action")
        note = request.POST.get("note", "").strip()

        if is_qr_order and not slip and action in {"approve", "reject"}:
            messages.error(request, "คำสั่งซื้อนี้ยังไม่มีสลิปให้ตรวจสอบ")
            return redirect("admin_orders")

        if action == "approve":
            try:
                # ตัดสต็อกทันทีเมื่อผู้ดูแลอนุมัติคำสั่งซื้อ
                deduct_order_stock(order)
            except ValueError as exc:
                messages.error(request, str(exc))
                return redirect("admin_check_slip", order_id=order.id)

            order.status = OrderStatus.PAID
            order.paid_at = timezone.now()
            order.review_note = note
            order.save(update_fields=["status", "paid_at", "review_note"])

            if is_qr_order and slip:
                slip.approved = True
                slip.note = note
                slip.checked_at = timezone.now()
                slip.save(update_fields=["approved", "note", "checked_at", "image"])

            result_message = _build_result_message(is_qr_order=is_qr_order, approved=True)
            Notification.objects.create(
                user=order.user,
                title=_build_notification_title(approved=True),
                message=_build_notification_message(order, result_message, note),
            )
            _send_order_status_email(order, approved=True, result_message=result_message, note=note)
            messages.success(request, result_message)
            return redirect("admin_orders")

        if action == "reject":
            # ฝั่ง QR จะปฏิเสธสลิป ส่วน COD จะปฏิเสธข้อมูลคำสั่งซื้อแทน
            if is_qr_order and slip:
                slip.approved = False
                slip.note = note
                slip.checked_at = timezone.now()
                slip.save(update_fields=["approved", "note", "checked_at", "image"])
                order.status = OrderStatus.REJECTED
            else:
                order.status = OrderStatus.CANCELLED

            order.review_note = note
            order.save(update_fields=["status", "review_note"])

            result_message = _build_result_message(is_qr_order=is_qr_order, approved=False)
            Notification.objects.create(
                user=order.user,
                title=_build_notification_title(approved=False),
                message=_build_notification_message(order, result_message, note),
            )
            _send_order_status_email(order, approved=False, result_message=result_message, note=note)
            messages.warning(request, result_message)
            return redirect("admin_orders")

        if action == "delete" and is_qr_order and slip:
            slip.delete()
            order.status = OrderStatus.PENDING
            order.review_note = ""
            order.save(update_fields=["status", "review_note"])
            Notification.objects.create(
                user=order.user,
                title="สลิปถูกลบ",
                message=f"คำสั่งซื้อ {order.order_code}: ผู้ดูแลระบบลบสลิปแล้ว กรุณาอัปโหลดใหม่",
            )
            messages.info(request, "ลบสลิปเรียบร้อยแล้ว")
            return redirect("admin_orders")

        return redirect("admin_orders")

    return render(
        request,
        "admin/check_slip.html",
        {
            "order": order,
            "slip": slip,
            "is_qr_order": is_qr_order,
            "is_cod_order": is_cod_order,
            "is_reviewable": is_reviewable,
            "OrderStatus": OrderStatus,
        },
    )


@staff_member_required
def admin_delete_order(request, order_id):
    """ลบคำสั่งซื้อและคืนสต็อกถ้าออเดอร์นั้นเคยตัดสต็อกไปแล้ว"""
    order = get_object_or_404(Order, id=order_id)

    if request.method == "POST":
        restore_order_stock(order)
        order_num = order.id
        user = order.user
        order.delete()

        Notification.objects.create(
            user=user,
            title="คำสั่งซื้อถูกลบ",
            message=f"คำสั่งซื้อ #{order_num} ถูกลบโดยผู้ดูแลระบบ",
        )
        messages.success(request, f"ลบคำสั่งซื้อ #{order_num} เรียบร้อยแล้ว")

    return redirect("admin_orders")
