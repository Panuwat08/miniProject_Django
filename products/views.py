from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Q
from django.contrib import messages

from .models import Category, Product
from .forms import ProductForm

# [กลุ่มที่ 2] ระบบควบคุมการแสดงผลและจัดการสินค้า (หมวดอุปกรณ์โรงแรม)
# รายละเอียดความต้องการ (Requirements):
# FR-05: ระบบต้องแสดงรายการสินค้า (Product List)
# FR-06: ระบบต้องแสดงสินค้าแยกตามหมวด (Category Filter)
# FR-07: ระบบต้องแสดงรายละเอียดสินค้า (Product Detail)
# FR-08: ระบบต้องรองรับการค้นหาสินค้า (Search System)

# --- ส่วนแสดงผลสำหรับลูกค้า (User Facing) ---

def product_list(request):
    """
    [FR-05] แสดงรายการสินค้าทั้งหมด (Product Listing)
    """
    categories = Category.objects.filter(is_active=True)
    products = Product.objects.filter(is_active=True).select_related("category")

    # [FR-06] รองรับการกรองตามหมวดหมู่ผ่าน Query String (?category=slug)
    category_slug = request.GET.get("category")

    current_category = None
    if category_slug:
        current_category = get_object_or_404(Category, slug=category_slug, is_active=True)
        products = products.filter(category=current_category)

    context = {
        "products": products,
        "categories": categories,
        "current_category": current_category,
    }
    return render(request, "products/product_list.html", context)


def product_by_category(request, slug):
    """
    [FR-06] ระบบแยกแยะสินค้าตามหมวดหมู่ (Filtering Strategy)
    """
    category = get_object_or_404(Category, slug=slug, is_active=True)
    categories = Category.objects.filter(is_active=True)
    products = Product.objects.filter(is_active=True, category=category).select_related("category")

    context = {
        "products": products,
        "categories": categories,
        "current_category": category,
    }
    return render(request, "products/product_list.html", context)


def product_detail(request, slug):
    """
    [FR-07] ระบบแสดงรายละเอียดสินค้าเชิงลึก
    """
    product = get_object_or_404(
        Product.objects.select_related("category"),
        slug=slug,
        is_active=True,
    )

    # Cross-selling System: แนะนำสินค้าที่ใกล้เคียง
    related_products = (
        Product.objects.filter(is_active=True, category=product.category)
        .exclude(id=product.id)
        .select_related("category")[:4]
        if product.category
        else Product.objects.none()
    )

    context = {
        "product": product,
        "related_products": related_products,
    }
    return render(request, "products/product_detail.html", context)


def product_search(request):
    """
    [FR-08] ระบบค้นหาอัจฉริยะ (Search Algorithm)
    """
    query = request.GET.get("q", "").strip()
    products = Product.objects.none()

    if query:
        products = (
            Product.objects.filter(is_active=True)
            .filter(Q(name__icontains=query) | Q(description__icontains=query))
            .select_related("category")
        )

    context = {
        "products": products,
        "query": query,
    }
    return render(request, "products/search_results.html", context)


# --- ส่วนจัดการหลังบ้าน (Admin Management - FR-20, 21, 22) ---

def product_create(request):
    """[Create] ฟังก์ชันเพิ่มสินค้าใหม่"""
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            product = form.save()
            messages.success(request, f'เพิ่มสินค้า "{product.name}" เรียบร้อยแล้ว')
            return redirect('products:product_list')
    else:
        form = ProductForm()
    return render(request, 'products/product_form.html', {'form': form, 'title': 'เพิ่มสินค้าใหม่'})


def product_update(request, pk):
    """[Update] ฟังก์ชันแก้ไขข้อมูลสินค้าตาม Primary Key"""
    product = get_object_or_404(Product, pk=pk)
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            form.save()
            messages.success(request, f'อัปเดตข้อมูล "{product.name}" เรียบร้อยแล้ว')
            return redirect('products:product_list')
    else:
        form = ProductForm(instance=product)
    return render(request, 'products/product_form.html', {'form': form, 'title': 'แก้ไขสินค้า'})


def product_delete(request, pk):
    """[Delete - FR-20] ฟังก์ชันลบสินค้าแบบ Soft Delete (ไม่ลบจริงแต่ซ่อนไว้)"""
    product = get_object_or_404(Product, pk=pk)
    if request.method == 'POST':
        product.is_active = False  # Soft Delete: ปิดการใช้งานแทนการลบแถวใน DB
        product.save()
        messages.warning(request, f'ลบสินค้า "{product.name}" ออกจากรายการขายแล้ว')
        return redirect('products:product_list')
    return render(request, 'products/product_confirm_delete.html', {'product': product})


def deduct_stock(product_id, quantity):
    """
    [FR-21, FR-22] ส่วน Logic ตัดสต็อกเชิงเทคนิค 
    (สำหรับให้กลุ่มอื่นเรียกใช้งานข้าม Module)
    """
    try:
        product = Product.objects.get(id=product_id)
        if product.can_sell(quantity): # ใช้ Method จาก Model
            product.stock_qty -= quantity
            product.save()
            return True # ตัดสต็อกสำเร็จ
        else:
            return False # สินค้าไม่พอ
    except Product.DoesNotExist:
        return False
