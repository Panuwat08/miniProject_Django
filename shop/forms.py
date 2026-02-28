# ==========================================
# forms.py — ฟอร์มสำหรับจัดการสินค้า
# ใช้ ModelForm เพื่อสร้างฟอร์มจาก Product Model อัตโนมัติ
# ==========================================

from django import forms
from .models import Product


# ==========================================
# ฟอร์มสินค้า (ProductForm)
# ใช้สำหรับ: เพิ่มสินค้าใหม่ / แก้ไขสินค้าเดิม
# ==========================================
class ProductForm(forms.ModelForm):
    class Meta:
        model = Product  # ผูกกับโมเดล Product
        fields = ['name', 'description', 'price', 'image', 'stock']  # ฟิลด์ที่แสดงในฟอร์ม

        # กำหนด Widget พร้อม CSS class สำหรับแต่ละฟิลด์
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),           # ช่องชื่อสินค้า
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),  # ช่องรายละเอียด (3 บรรทัด)
            'price': forms.NumberInput(attrs={'class': 'form-control'}),         # ช่องราคา
            'stock': forms.NumberInput(attrs={'class': 'form-control'}),         # ช่องจำนวนสต็อก
            # หมายเหตุ: image ไม่ต้องกำหนด widget เพราะใช้ drag & drop ใน template
        }
