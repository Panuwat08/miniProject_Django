"""????????? badge ???? ? ???? ???????????????????????? template ????"""

from django.db.models import Sum

from orders.models import Order, OrderStatus

from .models import CartItem


def cart_badge(request):
    cart_count = 0
    orders_count = 0
    admin_pending_orders_count = 0

    if request.user.is_authenticated:
        cart_count = (
            CartItem.objects.filter(cart__user=request.user)
            .aggregate(total_qty=Sum("qty"))
            .get("total_qty")
            or 0
        )
        orders_count = Order.objects.filter(
            user=request.user,
            status=OrderStatus.PENDING,
        ).count()
        if request.user.profile.is_staff_member() or request.user.profile.is_admin():
            admin_pending_orders_count = Order.objects.filter(status=OrderStatus.PENDING).count()

    return {
        "cart_item_count": cart_count,
        "customer_orders_count": orders_count,
        "admin_pending_orders_count": admin_pending_orders_count,
    }
