from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
import re


# ===============================
# REGISTER
# ===============================
def register(request):
    if request.method == "POST":
        username = request.POST.get("username", "")
        email = request.POST.get("email", "")
        password1 = request.POST.get("password1", "")
        password2 = request.POST.get("password2", "")

        # เช็คกรอกครบ
        if not username or not email or not password1 or not password2:
            messages.error(request, "กรอกข้อมูลให้ครบทุกช่อง")
            return redirect("/register/")

        # ห้ามมีช่องว่าง
        if " " in username:
            messages.error(request, "Username ห้ามมีช่องว่าง")
            return redirect("/register/")

        if " " in password1:
            messages.error(request, "Password ห้ามมีช่องว่าง")
            return redirect("/register/")

        # รับเฉพาะ อังกฤษ ตัวเลข _
        if not re.fullmatch(r'[A-Za-z0-9_]+', username):
            messages.error(request, "Username ใช้ได้เฉพาะภาษาอังกฤษ ตัวเลข และ _ เท่านั้น")
            return redirect("/register/")

        # เช็ครหัสผ่านตรงกัน
        if password1 != password2:
            messages.error(request, "รหัสผ่านไม่ตรงกัน")
            return redirect("/register/")

        # ความยาวขั้นต่ำ
        if len(password1) < 6:
            messages.error(request, "รหัสผ่านต้องอย่างน้อย 6 ตัวอักษร")
            return redirect("/register/")

        # เช็คซ้ำ
        if User.objects.filter(username=username).exists():
            messages.error(request, "Username นี้ถูกใช้แล้ว")
            return redirect("/register/")

        if User.objects.filter(email=email).exists():
            messages.error(request, "Email นี้ถูกใช้แล้ว")
            return redirect("/register/")

        # ✅ สร้าง user (ต้อง indent ให้ถูก)
        User.objects.create_user(
            username=username,
            email=email,
            password=password1
        )

        messages.success(request, "สมัครสมาชิกสำเร็จ 🎉 กรุณาเข้าสู่ระบบ")
        return redirect("/register/")

    # ✅ สำคัญมาก ห้ามลืมบรรทัดนี้
    return render(request, "register.html")

# ===============================
# LOGIN
# ===============================
def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username", "")
        password = request.POST.get("password", "")

        if not username or not password:
            messages.error(request, "กรอกข้อมูลให้ครบ")
            return redirect("/login/")

        # ห้ามภาษาไทย
        if not re.fullmatch(r'[A-Za-z0-9_]+', username):
            messages.error(request, "Username ไม่ถูกต้อง")
            return redirect("/login/")

        user = authenticate(request, username=username, password=password)

        if user is None:
            messages.error(request, "Username หรือ Password ไม่ถูกต้อง")
            return redirect("/login/")

        login(request, user)
        return redirect("/dashboard/")

    return render(request, "login.html")

