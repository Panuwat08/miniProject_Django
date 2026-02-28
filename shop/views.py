# ==========================================
# views.py — ฟังก์ชัน View ทั้งหมดของแอป shop
# จัดการ: หน้าแรก, รายละเอียดสินค้า, ตะกร้า, จัดการสินค้า (Admin)
# ==========================================

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Product, Cart, CartItem


# ==========================================
# ฟังก์ชันช่วยเหลือ (Helper Functions)
# ==========================================

def _get_cart(user):
    """ดึงตะกร้าสินค้าของผู้ใช้ ถ้ายังไม่มีจะสร้างให้อัตโนมัติ"""
    cart, _ = Cart.objects.get_or_create(user=user)
    return cart


# ==========================================
# ส่วนหน้าร้าน (Storefront Views)
# ==========================================

def home(request):
    """
    หน้าแรก — แสดงรายการสินค้าทั้งหมดที่ยัง active อยู่
    เรียงลำดับจากสินค้าล่าสุดไปเก่าสุด (id มากไปน้อย)
    """
    products = Product.objects.filter(is_active=True).order_by("-id")
    return render(request, "shop/product_list.html", {"products": products})


def product_detail(request, product_id):
    """
    หน้ารายละเอียดสินค้า — แสดงข้อมูลสินค้าตัวเดียว
    ถ้าหาไม่เจอจะแสดงหน้า 404
    """
    product = get_object_or_404(Product, id=product_id)
    return render(request, "shop/product_detail.html", {"product": product})


# ==========================================
# ส่วนตะกร้าสินค้า (Cart Views)
# ==========================================

@login_required
def cart_detail(request):
    """
    หน้าตะกร้าสินค้า — แสดงรายการสินค้าในตะกร้าของผู้ใช้
    ต้องล็อกอินก่อนถึงจะเข้าได้ (@login_required)
    """
    cart = _get_cart(request.user)
    return render(request, "shop/cart.html", {"cart": cart})


@login_required
def cart_add(request, product_id):
    """
    เพิ่มสินค้าลงตะกร้า
    - ถ้าสินค้ามีอยู่แล้วในตะกร้า จะเพิ่มจำนวน +1
    - ถ้าจำนวนเกินสต็อก จะปรับให้เท่ากับสต็อกและแจ้งเตือน
    """
    product = get_object_or_404(Product, id=product_id, is_active=True)
    cart = _get_cart(request.user)

    # สร้างรายการใหม่ หรือดึงรายการเดิมที่มีอยู่แล้ว
    item, created = CartItem.objects.get_or_create(cart=cart, product=product)
    if not created:
        item.qty += 1  # เพิ่มจำนวน +1 ถ้ามีอยู่แล้ว

    # ตรวจสอบว่าจำนวนไม่เกินสต็อก
    if item.qty > product.stock:
        item.qty = product.stock
        messages.error(request, "จำนวนเกินสต็อก")

    item.save()
    return redirect("cart_detail")


@login_required
def cart_update_qty(request, item_id):
    """
    อัปเดตจำนวนสินค้าในตะกร้า
    - รับค่า qty จาก POST request
    - ตรวจสอบขอบเขต: ต้อง >= 1 และ <= สต็อก
    """
    item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    qty_str = request.POST.get("qty", "1")

    # แปลงค่าจำนวนจาก string เป็น integer
    try:
        qty = int(qty_str)
    except ValueError:
        qty = 1  # ถ้าแปลงไม่ได้ ใช้ค่า 1

    # ตรวจสอบขอบเขตจำนวน
    if qty < 1:
        qty = 1  # จำนวนต่ำสุด = 1
    if qty > item.product.stock:
        qty = item.product.stock  # จำนวนสูงสุด = สต็อก
        messages.error(request, "จำนวนเกินสต็อก")

    item.qty = qty
    item.save()
    return redirect("cart_detail")


@login_required
def cart_remove(request, item_id):
    """
    ลบสินค้าออกจากตะกร้า
    - ตรวจสอบว่าเป็นสินค้าของผู้ใช้คนนี้จริง
    """
    item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    item.delete()
    return redirect("cart_detail")


# ==========================================
# ส่วนจัดการสินค้า — Admin Product Management
# เฉพาะ Superuser เท่านั้นที่เข้าถึงได้
# ==========================================
from .forms import ProductForm


@login_required
def admin_product_list(request):
    """
    หน้ารายการสินค้าทั้งหมด (Admin Panel)
    - ตรวจสอบสิทธิ์: ต้องเป็น superuser
    - แสดงสินค้าทั้งหมด (รวมที่ถูก soft-delete)
    """
    if not request.user.is_superuser:
        messages.error(request, 'ไม่มีสิทธิ์เข้าถึง')
        return redirect('home')
    products = Product.objects.all().order_by("-id")
    return render(request, "shop/admin_product_list.html", {"products": products})


@login_required
def product_create(request):
    """
    เพิ่มสินค้าใหม่
    - GET: แสดงฟอร์มเปล่า
    - POST: ตรวจสอบข้อมูลและบันทึกสินค้าใหม่ลงฐานข้อมูล
    """
    if not request.user.is_superuser:
        messages.error(request, 'ไม่มีสิทธิ์เข้าถึง')
        return redirect('home')

    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)  # รับข้อมูลพร้อมไฟล์รูปภาพ
        if form.is_valid():
            product = form.save()  # บันทึกสินค้าลงฐานข้อมูล
            messages.success(request, f'เพิ่มสินค้า "{product.name}" เรียบร้อยแล้ว')
            return redirect('admin_product_list')
    else:
        form = ProductForm()  # สร้างฟอร์มเปล่า
    return render(request, 'shop/product_form.html', {'form': form, 'title': 'เพิ่มสินค้าใหม่'})


@login_required
def product_update(request, pk):
    """
    แก้ไขข้อมูลสินค้า
    - GET: แสดงฟอร์มพร้อมข้อมูลเดิม
    - POST: ตรวจสอบและอัปเดตข้อมูลในฐานข้อมูล
    """
    if not request.user.is_superuser:
        messages.error(request, 'ไม่มีสิทธิ์เข้าถึง')
        return redirect('home')

    product = get_object_or_404(Product, pk=pk)  # ดึงสินค้าที่ต้องการแก้ไข
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product)  # ผูกกับสินค้าเดิม
        if form.is_valid():
            form.save()  # อัปเดตข้อมูลในฐานข้อมูล
            messages.success(request, f'อัปเดตข้อมูล "{product.name}" เรียบร้อยแล้ว')
            return redirect('admin_product_list')
    else:
        form = ProductForm(instance=product)  # โหลดข้อมูลเดิมลงฟอร์ม
    return render(request, 'shop/product_form.html', {'form': form, 'title': 'แก้ไขสินค้า'})


@login_required
def product_delete(request, pk):
    """
    ลบสินค้า (Soft Delete)
    - ไม่ได้ลบจริง แค่ตั้ง is_active = False
    - ข้อมูลยังอยู่ในฐานข้อมูลเพื่อเก็บประวัติการขาย
    - GET: แสดงหน้ายืนยันการลบ
    - POST: ทำการ soft-delete
    """
    if not request.user.is_superuser:
        messages.error(request, 'ไม่มีสิทธิ์เข้าถึง')
        return redirect('home')
        
    product = get_object_or_404(Product, pk=pk)  # ดึงสินค้าที่ต้องการลบ
    if request.method == 'POST':
        product.is_active = False  # Soft Delete: ซ่อนสินค้าแทนการลบจริง
        product.save()
        messages.warning(request, f'ลบสินค้า "{product.name}" ออกจากรายการขายแล้ว')
        return redirect('admin_product_list')
    return render(request, 'shop/product_confirm_delete.html', {'product': product})


# ==========================================
# ฟังก์ชันตัดสต็อก (Deduct Stock)
# เรียกใช้เมื่อมีการสั่งซื้อสำเร็จ
# ==========================================

def deduct_stock(product_id, quantity):
    """
    ตัดจำนวนสต็อกสินค้าเมื่อมีการสั่งซื้อ
    - ตรวจสอบว่าสต็อกเพียงพอก่อนตัด
    - คืน True ถ้าตัดสำเร็จ, False ถ้าสต็อกไม่พอหรือไม่พบสินค้า
    """
    try:
        product = Product.objects.get(id=product_id)
        if product.stock >= quantity:
            product.stock -= quantity  # ลดจำนวนสต็อก
            product.save()
            return True  # ตัดสต็อกสำเร็จ
        else:
            return False  # สต็อกไม่เพียงพอ
    except Product.DoesNotExist:
        return False  # ไม่พบสินค้า
