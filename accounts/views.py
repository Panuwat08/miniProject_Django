"""มุมมองหลักของระบบบัญชีผู้ใช้ เช่น สมัครสมาชิก เข้าสู่ระบบ และหน้าจัดการผู้ใช้"""

import re
import time

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404, redirect, render

from orders.models import Order, OrderStatus
from shop.models import Product

from .forms import ProfileUpdateForm
from .models import UserProfile


def _require_staff_access(request):
    """กันสิทธิ์ไม่ให้ผู้ใช้ทั่วไปเข้าถึงหน้าฝั่งผู้ดูแลระบบ"""
    profile = request.user.profile
    if not (profile.is_staff_member() or profile.is_admin()):
        messages.error(request, "หน้านี้สำหรับผู้ดูแลระบบ")
        return redirect("dashboard")
    return None

import re
from django.contrib import messages
from django.contrib.auth.models import User
from django.shortcuts import redirect, render

def register(request):
    """สมัครสมาชิกใหม่ โดยกำหนดบทบาทเริ่มต้นเป็นลูกค้า"""
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        email = request.POST.get("email", "").strip()
        password1 = request.POST.get("password1", "")
        password2 = request.POST.get("password2", "")

        # ✅ 1. เช็คค่าว่าง
        if not username or not email or not password1 or not password2:
            messages.error(request, "กรอกข้อมูลให้ครบทุกช่อง")
            return redirect("/register/")

        # ✅ 2. จำกัดความยาว
        if len(username) > 20:
            messages.error(request, "Username ห้ามเกิน 20 ตัวอักษร")
            return redirect("/register/")

        if len(password1) > 20:
            messages.error(request, "Password ห้ามเกิน 20 ตัวอักษร")
            return redirect("/register/")

        # ✅ 3. ห้ามมีช่องว่าง
        if " " in username:
            messages.error(request, "Username ห้ามมีช่องว่าง")
            return redirect("/register/")

        if " " in password1:
            messages.error(request, "Password ห้ามมีช่องว่าง")
            return redirect("/register/")

        # ✅ 4. รูปแบบ username
        if not re.fullmatch(r"[A-Za-z0-9_]+", username):
            messages.error(request, "Username ใช้ได้เฉพาะภาษาอังกฤษ ตัวเลข และ _ เท่านั้น")
            return redirect("/register/")

        # ✅ 5. กัน email ภาษาไทย + format email
        if not re.fullmatch(r"[A-Za-z0-9@._\-]+", email):
            messages.error(request, "Email ต้องเป็นภาษาอังกฤษเท่านั้น")
            return redirect("/register/")

        if not re.fullmatch(r"[^@]+@[^@]+\.[^@]+", email):
            messages.error(request, "รูปแบบ Email ไม่ถูกต้อง")
            return redirect("/register/")

        # ✅ 6. เช็ครหัสผ่าน
        if password1 != password2:
            messages.error(request, "รหัสผ่านไม่ตรงกัน")
            return redirect("/register/")

        if len(password1) < 6:
            messages.error(request, "รหัสผ่านต้องมีอย่างน้อย 6 ตัวอักษร")
            return redirect("/register/")

        # ✅ 7. เช็คซ้ำ
        if User.objects.filter(username=username).exists():
            messages.error(request, "Username นี้ถูกใช้แล้ว")
            return redirect("/register/")

        if User.objects.filter(email=email).exists():
            messages.error(request, "Email นี้ถูกใช้แล้ว")
            return redirect("/register/")

        # ✅ 8. สร้าง user
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password1,
        )

        # ✅ 9. ตั้งค่า profile
        profile = user.profile
        profile.role = "CUSTOMER"
        profile.save()

        messages.success(request, "สมัครสมาชิกสำเร็จ กรุณาเข้าสู่ระบบ")
        return redirect("/login/")  # 🔥 เปลี่ยนให้ไป login

    return render(request, "register.html")


def login_view(request):
    """เข้าสู่ระบบพร้อมจำกัดการลองผิดเกิน 3 ครั้งและล็อกชั่วคราว 60 วินาที"""
    lock_until = request.session.get("login_locked_until", 0)
    remaining_seconds = max(0, int(lock_until - time.time()))

    if request.method == "POST":
        if remaining_seconds > 0:
            messages.error(request, f"กรุณารอ {remaining_seconds} วินาทีก่อนลองเข้าสู่ระบบใหม่")
            return redirect("/login/")

        username = request.POST.get("username", "")
        password = request.POST.get("password", "")

        if not username or not password:
            messages.error(request, "กรอกข้อมูลให้ครบ")
            return redirect("/login/")

        if not re.fullmatch(r"[A-Za-z0-9_]+", username):
            messages.error(request, "Username ไม่ถูกต้อง")
            return redirect("/login/")

        # ตรวจสอบข้อมูลเข้าสู่ระบบด้วยระบบ auth ของ Django
        user = authenticate(request, username=username, password=password)

        if user is None:
            # เก็บจำนวนครั้งที่กรอกผิดไว้ใน session ของเบราว์เซอร์ปัจจุบัน
            failed_attempts = int(request.session.get("login_failed_attempts", 0) or 0) + 1
            if failed_attempts >= 3:
                request.session["login_locked_until"] = time.time() + 60
                request.session["login_failed_attempts"] = 0
                messages.error(request, "กรอก Username หรือ Password ผิดครบ 3 ครั้ง ระบบจะล็อก 60 วินาที")
            else:
                request.session["login_failed_attempts"] = failed_attempts
                remaining_attempts = 3 - failed_attempts
                messages.error(
                    request,
                    f"Username หรือ Password ไม่ถูกต้อง เหลืออีก {remaining_attempts} ครั้งก่อนระบบจะล็อก",
                )
            return redirect("/login/")

        # หากเข้าสู่ระบบสำเร็จให้ล้างตัวนับและเวลาล็อกอินที่เคยค้างไว้
        request.session.pop("login_locked_until", None)
        request.session.pop("login_failed_attempts", None)
        login(request, user)
        return redirect("/")

    lock_until = request.session.get("login_locked_until", 0)
    remaining_seconds = max(0, int(lock_until - time.time()))
    return render(request, "login.html", {"lock_remaining": remaining_seconds})


def logout_view(request):
    """ออกจากระบบและพาผู้ใช้กลับไปหน้าเข้าสู่ระบบ"""
    logout(request)
    messages.success(request, "ออกจากระบบสำเร็จ")
    return redirect("/login/")


@login_required
def dashboard(request):
    """แสดงข้อมูล dashboard ที่แตกต่างกันตามบทบาทของผู้ใช้"""
    profile = request.user.profile
    context = {
        "user": request.user,
        "profile": profile,
    }

    if profile.is_staff_member() or profile.is_admin():
        # สรุปตัวเลขหลักสำหรับการ์ดและรายการออเดอร์ล่าสุดบนหน้า dashboard
        orders = Order.objects.all()
        context.update(
            {
                "product_count": Product.objects.filter(is_active=True).count(),
                "order_count": orders.count(),
                "pending_count": orders.filter(status__in=[OrderStatus.PENDING, OrderStatus.REJECTED]).count(),
                "customer_count": User.objects.filter(profile__role="CUSTOMER").count(),
                "low_stock_count": Product.objects.filter(is_active=True, stock__lte=5).count(),
                "sales_total": orders.filter(
                    status__in=[OrderStatus.PAID, OrderStatus.SHIPPED, OrderStatus.COMPLETED]
                ).aggregate(total=Sum("total"))["total"]
                or 0,
                "recent_orders": orders.select_related("user").order_by("-created_at")[:5],
            }
        )

    return render(request, "dashboard.html", context)


@login_required
def profile_view(request):
    """แสดงและบันทึกการแก้ไขข้อมูลส่วนตัวของผู้ใช้"""
    profile = request.user.profile
    if request.method == "POST":
        form = ProfileUpdateForm(request.POST, user=request.user)
        if form.is_valid():
            # บันทึกเฉพาะฟิลด์ที่เปิดให้ผู้ใช้แก้ไขจากหน้าโปรไฟล์
            form.save()
            messages.success(request, "บันทึกข้อมูลส่วนตัวเรียบร้อยแล้ว")
            return redirect("profile")
        messages.error(request, "กรุณาตรวจสอบข้อมูลที่กรอกอีกครั้ง")
    else:
        form = ProfileUpdateForm(user=request.user)

    return render(
        request,
        "profile.html",
        {
            "user": request.user,
            "profile": profile,
            "form": form,
        },
    )


@login_required
def user_management(request):
    """หน้าจัดการผู้ใช้สำหรับ staff/admin พร้อมค้นหา กรอง และสรุปจำนวนผู้ใช้"""
    blocked = _require_staff_access(request)
    if blocked:
        return blocked

    query = request.GET.get("q", "").strip()
    role = request.GET.get("role", "").strip()

    # ดึง profile มาพร้อมกันเพื่อลดจำนวน query ตอนแสดงผลในตาราง
    users = User.objects.select_related("profile").order_by("-date_joined")

    if query:
        users = users.filter(
            Q(username__icontains=query)
            | Q(email__icontains=query)
            | Q(profile__company_name__icontains=query)
            | Q(profile__phone__icontains=query)
        )

    if role:
        users = users.filter(profile__role=role)

    summary = {
        "total_users": User.objects.count(),
        "customers": User.objects.filter(profile__role="CUSTOMER").count(),
        "staffs": User.objects.filter(profile__role="STAFF").count(),
        "admins": User.objects.filter(profile__role="ADMIN").count(),
        "active_users": User.objects.filter(is_active=True).count(),
    }

    return render(
        request,
        "admin/user_management.html",
        {
            "users": users,
            "query": query,
            "role_filter": role,
            "role_choices": UserProfile.ROLE_CHOICES,
            "summary": summary,
        },
    )


@login_required
def create_user_account(request):
    """สร้างผู้ใช้ใหม่จากฝั่งผู้ดูแลระบบ โดย staff จะถูกจำกัดบทบาทที่สร้างได้"""
    blocked = _require_staff_access(request)
    if blocked:
        return blocked

    if request.method != "POST":
        return redirect("user_management")

    username = request.POST.get("username", "").strip()
    email = request.POST.get("email", "").strip()
    password = request.POST.get("password", "")
    role = request.POST.get("role", "CUSTOMER").strip()
    phone = request.POST.get("phone", "").strip()
    company_name = request.POST.get("company_name", "").strip()

    allowed_roles = {choice[0] for choice in UserProfile.ROLE_CHOICES}

    if request.user.profile.is_staff_member():
        allowed_roles.discard("ADMIN")

    if not username or not email or not password:
        messages.error(request, "กรุณากรอกข้อมูลผู้ใช้ใหม่ให้ครบ")
        return redirect("user_management")

    if role not in allowed_roles:
        messages.error(request, "ไม่มีสิทธิ์สร้างผู้ใช้ในบทบาทนี้")
        return redirect("user_management")

    if " " in username or not re.fullmatch(r"[A-Za-z0-9_]+", username):
        messages.error(request, "Username ใช้ได้เฉพาะภาษาอังกฤษ ตัวเลข และ _")
        return redirect("user_management")

    if len(password) < 6 or " " in password:
        messages.error(request, "รหัสผ่านต้องมีอย่างน้อย 6 ตัวอักษรและห้ามมีช่องว่าง")
        return redirect("user_management")

    if User.objects.filter(username=username).exists():
        messages.error(request, "Username นี้ถูกใช้แล้ว")
        return redirect("user_management")

    if User.objects.filter(email=email).exists():
        messages.error(request, "Email นี้ถูกใช้แล้ว")
        return redirect("user_management")

    user = User.objects.create_user(username=username, email=email, password=password)
    user.profile.role = role
    user.profile.phone = phone
    user.profile.company_name = company_name
    user.profile.save(update_fields=["role", "phone", "company_name", "updated_at"])

    messages.success(request, f"สร้างผู้ใช้ {username} เรียบร้อยแล้ว")
    return redirect("user_management")


@login_required
def update_user_role(request, user_id):
    """เปลี่ยนบทบาทผู้ใช้ โดยตรวจสิทธิ์ของผู้ที่กำลังแก้ไขก่อนเสมอ"""
    blocked = _require_staff_access(request)
    if blocked:
        return blocked

    if request.method != "POST":
        return redirect("user_management")

    target = get_object_or_404(User.objects.select_related("profile"), id=user_id)
    new_role = request.POST.get("role", "").strip()
    allowed_roles = {choice[0] for choice in UserProfile.ROLE_CHOICES}

    if new_role not in allowed_roles:
        messages.error(request, "บทบาทที่เลือกไม่ถูกต้อง")
        return redirect("user_management")

    if request.user.profile.is_staff_member():
        if new_role == "ADMIN" or target.profile.role == "ADMIN":
            messages.error(request, "พนักงานไม่สามารถแก้ไขสิทธิ์ผู้ดูแลระบบได้")
            return redirect("user_management")

    if target == request.user and new_role == "CUSTOMER":
        messages.error(request, "ไม่สามารถลดสิทธิ์บัญชีของตัวเองเป็นลูกค้าได้")
        return redirect("user_management")

    target.profile.role = new_role
    target.profile.save(update_fields=["role", "updated_at"])
    messages.success(request, f"อัปเดตบทบาทของ {target.username} เรียบร้อยแล้ว")
    return redirect("user_management")


@login_required
def toggle_user_active(request, user_id):
    """เปิดหรือปิดการใช้งานบัญชีจากหน้าจัดการผู้ใช้"""
    blocked = _require_staff_access(request)
    if blocked:
        return blocked

    if request.method != "POST":
        return redirect("user_management")

    target = get_object_or_404(User, id=user_id)

    if target == request.user:
        messages.error(request, "ไม่สามารถปิดการใช้งานบัญชีของตัวเองได้")
        return redirect("user_management")

    if request.user.profile.is_staff_member() and target.profile.role == "ADMIN":
        messages.error(request, "พนักงานไม่สามารถปิดการใช้งานบัญชีผู้ดูแลระบบได้")
        return redirect("user_management")

    target.is_active = not target.is_active
    target.save(update_fields=["is_active"])
    messages.success(
        request,
        f"{'เปิด' if target.is_active else 'ปิด'}การใช้งานบัญชี {target.username} เรียบร้อยแล้ว",
    )
    return redirect("user_management")
