from django import forms

from .models import Category, Product


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ["name"]
        labels = {
            "name": "ชื่อหมวดหมู่",
        }
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "เช่น เครื่องนอน"}),
        }


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ["category", "name", "description", "price", "cost", "stock", "image"]
        labels = {
            "category": "หมวดหมู่สินค้า",
            "name": "ชื่อสินค้า",
            "description": "รายละเอียดสินค้า",
            "price": "ราคาขาย",
            "cost": "ต้นทุนสินค้า",
            "stock": "จำนวนคงเหลือ",
            "image": "รูปสินค้า",
        }
        help_texts = {
            "image": "รองรับไฟล์รูปภาพสำหรับแสดงหน้าสินค้า",
        }
        widgets = {
            "category": forms.Select(attrs={"class": "form-select"}),
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "price": forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "min": "0"}),
            "cost": forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "min": "0"}),
            "stock": forms.NumberInput(attrs={"class": "form-control", "min": "0"}),
            "image": forms.ClearableFileInput(attrs={"class": "form-control"}),
        }
