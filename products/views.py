from django.shortcuts import render, get_object_or_404
from django.db.models import Q

from .models import Category, Product

# [กลุ่มที่ 2] ระบบควบคุมการแสดงผลสินค้าอุปกรณ์โรงแรม
# พัฒนาขึ้นโดยแยกส่วน Logic ออกจากทีมอื่นเพื่อความเสถียร (Domain Isolation)

def product_list(request):
    """
    [FR-05] แสดงรายการสินค้าทั้งหมด (Product Listing)
    ดึงข้อมูลสินค้าที่ 'เปิดใช้งาน' และรวมข้อมูลหมวดหมู่เพื่อลดการเรียก Database (Optimization)
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
    ช่วยให้ผู้ใช้หาอุปกรณ์ที่ต้องการได้รวดเร็วตามกลุ่มการใช้งาน
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
    [FR-07] ระบบแสดงรายละเอียดสินค้าเชิงลึก (Product Data Architecture)
    แสดงราคา, จำนวนสต็อกจริง, และรายละเอียดที่จำเป็นสำหรับการตัดสินใจซื้อ B2B
    """
    product = get_object_or_404(
        Product.objects.select_related("category"),
        slug=slug,
        is_active=True,
    )

    # Cross-selling System: แนะนำสินค้าที่ใกล้เคียงเพื่อเพิ่มโอกาสในการขาย
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
    รองรับการค้นหาจาก 'ชื่อสินค้า' และ 'คำอธิบาย' แบบไม่แยกพิมพ์เล็กพิมพ์ใหญ่ (Case-insensitive)
    """
    query = request.GET.get("q", "").strip()
    products = Product.objects.none()

    if query:
        # ใช้ Q Objects สำหรับการค้นหาข้าม Field (Complex Lookup)
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
