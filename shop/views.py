from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render

from .forms import CategoryForm, ProductForm
from .models import Cart, CartItem, Category, Product


def _require_customer(request):
    if not request.user.is_authenticated:
        messages.error(request, "กรุณาเข้าสู่ระบบก่อนใช้งาน")
        return redirect("login")
    if not request.user.profile.is_customer():
        return redirect("dashboard")
    return None


def _get_cart(user):
    cart, _ = Cart.objects.get_or_create(user=user)
    return cart


def home(request):
    blocked = _require_customer(request)
    if blocked:
        return blocked

    products = Product.objects.filter(is_active=True).select_related("category").order_by("-id")
    categories = Category.objects.filter(is_active=True)

    category_slug = request.GET.get("category", "").strip()
    query = request.GET.get("q", "").strip()

    if category_slug:
        products = products.filter(category__slug=category_slug)

    if query:
        products = products.filter(name__icontains=query)

    paginator = Paginator(products, 8)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(
        request,
        "shop/product_list.html",
        {
            "products": page_obj,
            "page_obj": page_obj,
            "categories": categories,
            "selected_category": category_slug,
            "query": query,
        },
    )


def product_detail(request, product_id):
    blocked = _require_customer(request)
    if blocked:
        return blocked

    product = get_object_or_404(Product.objects.select_related("category"), id=product_id, is_active=True)
    return render(request, "shop/product_detail.html", {"product": product})


@login_required
def cart_detail(request):
    blocked = _require_customer(request)
    if blocked:
        return blocked

    cart = _get_cart(request.user)
    return render(request, "shop/cart.html", {"cart": cart})


@login_required
def cart_add(request, product_id):
    blocked = _require_customer(request)
    if blocked:
        return blocked

    product = get_object_or_404(Product, id=product_id, is_active=True)
    cart = _get_cart(request.user)
    item, created = CartItem.objects.get_or_create(cart=cart, product=product)

    if not created:
        item.qty += 1

    if item.qty > product.stock:
        item.qty = product.stock
        messages.error(request, "จำนวนสินค้าเกินสต๊อก")

    item.save()
    return redirect("cart_detail")


@login_required
def cart_update_qty(request, item_id):
    blocked = _require_customer(request)
    if blocked:
        return blocked

    item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    try:
        qty = int(request.POST.get("qty", "1"))
    except ValueError:
        qty = 1

    if qty < 1:
        qty = 1
    if qty > item.product.stock:
        qty = item.product.stock
        messages.error(request, "จำนวนสินค้าเกินสต๊อก")

    item.qty = qty
    item.save()
    return redirect("cart_detail")


@login_required
def cart_remove(request, item_id):
    blocked = _require_customer(request)
    if blocked:
        return blocked

    item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    item.delete()
    return redirect("cart_detail")


@login_required
def admin_product_list(request):
    if not (request.user.profile.is_staff_member() or request.user.profile.is_admin()):
        messages.error(request, "ไม่มีสิทธิ์เข้าถึง")
        return redirect("home")

    products = Product.objects.select_related("category").all().order_by("-id")
    categories = Category.objects.filter(is_active=True).order_by("name")
    query = request.GET.get("q", "").strip()
    category_slug = request.GET.get("category", "").strip()

    if query:
        products = products.filter(name__icontains=query)

    if category_slug:
        products = products.filter(category__slug=category_slug)

    paginator = Paginator(products, 8)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(
        request,
        "shop/admin_product_list.html",
        {
            "products": page_obj,
            "page_obj": page_obj,
            "categories": categories,
            "query": query,
            "selected_category": category_slug,
            "low_stock_count": products.filter(stock__lt=5).count(),
        },
    )


@login_required
def product_create(request):
    if not (request.user.profile.is_staff_member() or request.user.profile.is_admin()):
        messages.error(request, "ไม่มีสิทธิ์เข้าถึง")
        return redirect("home")

    if request.method == "POST":
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            product = form.save()
            messages.success(request, f'เพิ่มสินค้า "{product.name}" เรียบร้อยแล้ว')
            return redirect("admin_product_list")
    else:
        form = ProductForm()

    return render(request, "shop/product_form.html", {"form": form, "title": "เพิ่มสินค้าใหม่"})


@login_required
def product_update(request, pk):
    if not (request.user.profile.is_staff_member() or request.user.profile.is_admin()):
        messages.error(request, "ไม่มีสิทธิ์เข้าถึง")
        return redirect("home")

    product = get_object_or_404(Product, pk=pk)
    if request.method == "POST":
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            form.save()
            messages.success(request, f'อัปเดตข้อมูล "{product.name}" เรียบร้อยแล้ว')
            return redirect("admin_product_list")
    else:
        form = ProductForm(instance=product)

    return render(request, "shop/product_form.html", {"form": form, "title": "แก้ไขสินค้า"})


@login_required
def product_delete(request, pk):
    if not (request.user.profile.is_staff_member() or request.user.profile.is_admin()):
        messages.error(request, "ไม่มีสิทธิ์เข้าถึง")
        return redirect("home")

    product = get_object_or_404(Product, pk=pk)
    if request.method == "POST":
        product.is_active = False
        product.save()
        messages.warning(request, f'ลบสินค้า "{product.name}" ออกจากรายการขายแล้ว')
        return redirect("admin_product_list")

    return render(request, "shop/product_confirm_delete.html", {"product": product})


@login_required
def admin_category_list(request):
    if not (request.user.profile.is_staff_member() or request.user.profile.is_admin()):
        messages.error(request, "ไม่มีสิทธิ์เข้าถึง")
        return redirect("home")

    categories = Category.objects.all().order_by("name")
    query = request.GET.get("q", "").strip()

    if query:
        categories = categories.filter(name__icontains=query)

    paginator = Paginator(categories, 6)
    page_obj = paginator.get_page(request.GET.get("page"))

    form = CategoryForm()
    return render(
        request,
        "shop/admin_category_list.html",
        {
            "categories": page_obj,
            "page_obj": page_obj,
            "query": query,
            "form": form,
        },
    )


@login_required
def category_create(request):
    if not (request.user.profile.is_staff_member() or request.user.profile.is_admin()):
        messages.error(request, "ไม่มีสิทธิ์เข้าถึง")
        return redirect("home")

    if request.method == "POST":
        form = CategoryForm(request.POST)
        if form.is_valid():
            category = form.save()
            messages.success(request, f'เพิ่มหมวดหมู่ "{category.name}" เรียบร้อยแล้ว')
        else:
            messages.error(request, "ไม่สามารถเพิ่มหมวดหมู่ได้ กรุณาตรวจสอบข้อมูลอีกครั้ง")

    return redirect("admin_category_list")


@login_required
def category_remove(request, pk):
    if not (request.user.profile.is_staff_member() or request.user.profile.is_admin()):
        messages.error(request, "ไม่มีสิทธิ์เข้าถึง")
        return redirect("home")

    category = get_object_or_404(Category, pk=pk)
    if request.method == "POST":
        if category.products.exists():
            messages.error(request, f'ไม่สามารถลบหมวดหมู่ "{category.name}" ได้ เพราะยังมีสินค้าอยู่ในหมวดนี้')
        else:
            category_name = category.name
            category.delete()
            messages.success(request, f'ลบหมวดหมู่ "{category_name}" เรียบร้อยแล้ว')

    return redirect("admin_category_list")


@login_required
def category_update(request, pk):
    if not (request.user.profile.is_staff_member() or request.user.profile.is_admin()):
        messages.error(request, "ไม่มีสิทธิ์เข้าถึง")
        return redirect("home")

    category = get_object_or_404(Category, pk=pk)
    if request.method == "POST":
        form = CategoryForm(request.POST, instance=category)
        if form.is_valid():
            category = form.save()
            messages.success(request, f'อัปเดตหมวดหมู่ "{category.name}" เรียบร้อยแล้ว')
        else:
            messages.error(request, "ไม่สามารถบันทึกหมวดหมู่ได้")

    return redirect("admin_category_list")


@login_required
def category_delete(request, pk):
    if not (request.user.profile.is_staff_member() or request.user.profile.is_admin()):
        messages.error(request, "ไม่มีสิทธิ์เข้าถึง")
        return redirect("home")

    category = get_object_or_404(Category, pk=pk)
    if request.method == "POST":
        category.is_active = False
        category.save(update_fields=["is_active"])
        messages.warning(request, f'ปิดใช้งานหมวดหมู่ "{category.name}" แล้ว')

    return redirect("admin_category_list")


@login_required
def category_enable(request, pk):
    if not (request.user.profile.is_staff_member() or request.user.profile.is_admin()):
        messages.error(request, "ไม่มีสิทธิ์เข้าถึง")
        return redirect("home")

    category = get_object_or_404(Category, pk=pk)
    if request.method == "POST":
        category.is_active = True
        category.save(update_fields=["is_active"])
        messages.success(request, f'เปิดใช้งานหมวดหมู่ "{category.name}" แล้ว')

    return redirect("admin_category_list")
