"""???????????????????????????????????"""

import re

from django import forms
from django.contrib.auth.models import User


class ProfileUpdateForm(forms.Form):
    first_name = forms.CharField(
        label="ชื่อ",
        max_length=150,
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "ชื่อ",
            }
        ),
    )
    last_name = forms.CharField(
        label="นามสกุล",
        max_length=150,
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "นามสกุล",
            }
        ),
    )
    email = forms.EmailField(
        label="อีเมล",
        widget=forms.EmailInput(
            attrs={
                "class": "form-control",
                "placeholder": "email@example.com",
            }
        ),
    )
    phone = forms.CharField(
        label="เบอร์โทร",
        max_length=12,
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "id": "phoneInput",
                "placeholder": "081-234-5678",
                "inputmode": "numeric",
                "maxlength": "12",
                "pattern": "[0-9]{3}-[0-9]{3}-[0-9]{4}",
            }
        ),
    )

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        initial = kwargs.setdefault("initial", {})
        if user is not None:
            initial.setdefault("first_name", user.first_name)
            initial.setdefault("last_name", user.last_name)
            initial.setdefault("email", user.email)
            initial.setdefault("phone", user.profile.phone)
        super().__init__(*args, **kwargs)

    def clean_email(self):
        email = self.cleaned_data["email"].strip()
        if User.objects.filter(email__iexact=email).exclude(pk=self.user.pk).exists():
            raise forms.ValidationError("อีเมลนี้ถูกใช้งานแล้ว")
        return email

    def clean_phone(self):
        phone = self.cleaned_data["phone"].strip()
        if not phone:
            return ""

        digits = re.sub(r"\D", "", phone)[:10]
        if len(digits) != 10:
            raise forms.ValidationError("กรุณากรอกเบอร์โทร 10 หลัก")
        return f"{digits[:3]}-{digits[3:6]}-{digits[6:]}"

    def save(self):
        user = self.user
        profile = user.profile

        user.first_name = self.cleaned_data["first_name"].strip()
        user.last_name = self.cleaned_data["last_name"].strip()
        user.email = self.cleaned_data["email"].strip()
        user.save(update_fields=["first_name", "last_name", "email"])

        profile.phone = self.cleaned_data["phone"].strip()
        profile.save(update_fields=["phone", "updated_at"])

        return user
