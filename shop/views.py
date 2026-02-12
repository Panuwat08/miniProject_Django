from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Product, Cart, CartItem

def _get_cart(user):
    cart, _ = Cart.objects.get_or_create(user=user)
    return cart

def home(request):
    # หน้าแรก = รายการสินค้า
    products = Product.objects.filter(is_active=True).order_by("-id")
    return render(request, "shop/product_list.html", {"products": products})

@login_required
def cart_detail(request):
    cart = _get_cart(request.user)
    return render(request, "shop/cart.html", {"cart": cart})

@login_required
def cart_add(request, product_id):
    product = get_object_or_404(Product, id=product_id, is_active=True)
    cart = _get_cart(request.user)

    item, created = CartItem.objects.get_or_create(cart=cart, product=product)
    if not created:
        item.qty += 1

    if item.qty > product.stock:
        item.qty = product.stock
        messages.error(request, "จำนวนเกินสต็อก")

    item.save()
    return redirect("cart_detail")

@login_required
def cart_update_qty(request, item_id):
    item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    qty_str = request.POST.get("qty", "1")

    try:
        qty = int(qty_str)
    except:
        qty = 1

    if qty < 1:
        qty = 1
    if qty > item.product.stock:
        qty = item.product.stock
        messages.error(request, "จำนวนเกินสต็อก")

    item.qty = qty
    item.save()
    return redirect("cart_detail")

@login_required
def cart_remove(request, item_id):
    item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    item.delete()
    return redirect("cart_detail")
