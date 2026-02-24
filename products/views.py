from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import Product
from .forms import ProductForm

# ==============================
# ส่วนจัดการหน้าจอ Admin (FR-20)
# ==============================

# 1. หน้าแสดงรายการสินค้าทั้งหมด (Read)
def product_list(request):
    # ดึงเฉพาะสินค้าที่ยังขายอยู่ (is_active=True)
    products = Product.objects.filter(is_active=True)
    return render(request, 'products/product_list.html', {'products': products})

# 2. ฟังก์ชันเพิ่มสินค้า (Create)
def product_create(request):
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            product = form.save()
            messages.success(request, f'เพิ่มสินค้า "{product.name}" เรียบร้อยแล้ว')
            return redirect('product_list')
    else:
        form = ProductForm()
    return render(request, 'products/product_form.html', {'form': form, 'title': 'เพิ่มสินค้าใหม่'})

# 3. ฟังก์ชันแก้ไขสินค้า (Update)
def product_update(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            form.save()
            messages.success(request, f'อัปเดตข้อมูล "{product.name}" เรียบร้อยแล้ว')
            return redirect('product_list')
    else:
        form = ProductForm(instance=product)
    return render(request, 'products/product_form.html', {'form': form, 'title': 'แก้ไขสินค้า'})

# 4. ฟังก์ชันลบสินค้าแบบ Soft Delete (Delete - FR-20)
def product_delete(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == 'POST':
        product.is_active = False  # ไม่ลบจริง แค่ซ่อน
        product.save()
        messages.warning(request, f'ลบสินค้า "{product.name}" ออกจากรายการขายแล้ว')
        return redirect('product_list')
    return render(request, 'products/product_confirm_delete.html', {'product': product})

# ==============================
# ส่วน Logic ตัดสต็อก (FR-21, FR-22)
# ==============================
# ฟังก์ชันนี้ไม่ได้ต่อกับหน้าเว็บโดยตรง แต่มีไว้ให้กลุ่ม 3 (สั่งซื้อ) เรียกใช้
def deduct_stock(product_id, quantity):
    try:
        product = Product.objects.get(id=product_id)
        # FR-22: ป้องกันสต็อกติดลบ
        if product.stock_qty >= quantity:
            product.stock_qty -= quantity
            product.save()
            return True # ตัดสต็อกสำเร็จ
        else:
            return False # ของไม่พอ
    except Product.DoesNotExist:
        return False