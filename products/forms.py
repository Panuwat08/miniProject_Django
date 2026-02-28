from django import forms
from .models import Product

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['name', 'description', 'price', 'image', 'stock_qty']
        # ไม่เอา is_active มาแสดง เพราะตอนเพิ่มสินค้าใหม่ควรให้ขายได้เลย
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'price': forms.NumberInput(attrs={'class': 'form-control'}),
            'stock_qty': forms.NumberInput(attrs={'class': 'form-control'}),
        }