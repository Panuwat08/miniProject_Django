#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecommerce.settings')
django.setup()

from django.contrib.auth.models import User  # noqa: E402

try:
    user = User.objects.get(username='panuw')
    user.set_password('admin123')
    user.save()
    print(f"✅ Password for '{user.username}' has been reset to: admin123")
except User.DoesNotExist:
    print("❌ User 'panuw' not found")
except Exception as e:
    print(f"❌ Error: {e}")
