from django.db import models
from django.contrib.auth.models import User

class UserProfile(models.Model):
    """
    โปรไฟล์ผู้ใช้ - กำหนดบทบาทและข้อมูลเพิ่มเติม
    """
    ROLE_CHOICES = [
        ('CUSTOMER', 'ลูกค้า'),
        ('STAFF', 'พนักงานขาย'),
        ('ADMIN', 'ผู้ดูแลระบบ'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField('บทบาท', max_length=20, choices=ROLE_CHOICES, default='CUSTOMER')
    phone = models.CharField('เบอร์โทร', max_length=20, blank=True)
    company_name = models.CharField('ชื่อโรงแรม/บริษัท', max_length=255, blank=True)
    address = models.TextField('ที่อยู่', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'โปรไฟล์ผู้ใช้'
        verbose_name_plural = 'โปรไฟล์ผู้ใช้'

    def __str__(self):
        return f"{self.user.username} - {self.get_role_display()}"

    def is_customer(self):
        return self.role == 'CUSTOMER'

    def is_staff_member(self):
        return self.role == 'STAFF'

    def is_admin(self):
        return self.role == 'ADMIN'

    @property
    def full_name(self):
        """ชื่อเต็มสำหรับแสดงผล"""
        if self.company_name:
            return self.company_name
        return self.user.get_full_name() or self.user.username
