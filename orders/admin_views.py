from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required
from django.utils import timezone

from .models import Order, OrderStatus, Notification

@staff_member_required
def admin_orders(request):
    orders = Order.objects.select_related("user").order_by("-created_at")
    return render(request, "admin/orders_list.html", {"orders": orders})

@staff_member_required
def admin_check_slip(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    slip = getattr(order, "slip", None)

    if request.method == "POST":
        if not slip:
            return redirect("admin_orders")

        action = request.POST.get("action")  # approve/reject
        note = request.POST.get("note", "").strip()

        if action == "approve":
            slip.approved = True
            order.status = OrderStatus.PAID
            msg = "สลิปผ่านการตรวจสอบแล้ว"
        elif action == "reject":
            slip.approved = False
            order.status = OrderStatus.REJECTED
            msg = "สลิปไม่ถูกต้อง กรุณาอัปโหลดใหม่"
        elif action == "delete":
            slip.delete()
            order.status = OrderStatus.PENDING
            order.save()
            Notification.objects.create(
                user=order.user,
                title="สลิปถูกลบ",
                message=f"คำสั่งซื้อ #{order.id}: สลิปถูกลบโดยแอดมิน กรุณาอัปโหลดใหม่"
            )
            return redirect("admin_orders")

        slip.note = note
        slip.checked_at = timezone.now()
        slip.save()
        order.save()

        Notification.objects.create(
            user=order.user,
            title="อัปเดตสถานะการชำระเงิน",
            message=f"คำสั่งซื้อ #{order.id}: {msg}"
        )

        return redirect("admin_orders")

    return render(request, "admin/check_slip.html", {"order": order, "slip": slip})

@staff_member_required
def admin_delete_order(request, order_id):
    order = get_object_or_404(Order, id=order_id)

    if request.method == "POST":
        # คืนสต็อกก่อนลบ
        for item in order.items.select_related("product"):
            item.product.stock += item.qty
            item.product.save()

        order_num = order.id
        user = order.user
        order.delete()

        Notification.objects.create(
            user=user,
            title="คำสั่งซื้อถูกลบ",
            message=f"คำสั่งซื้อ #{order_num} ถูกลบโดยแอดมิน"
        )

    return redirect("admin_orders")
