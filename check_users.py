#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecommerce.settings')
django.setup()

from django.contrib.auth.models import User  # noqa: E402

print("=== All Users ===")
users = User.objects.all()
if not users:
    print("No users found!")
else:
    for user in users:
        print(f"Username: {user.username}")
        print(f"Email: {user.email}")
        print(f"Staff: {user.is_staff}")
        print(f"Superuser: {user.is_superuser}")
        print(f"Active: {user.is_active}")
        print("-" * 30)

print("\n=== Creating superuser if needed ===")
if not users:
    User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
    print("Created superuser: admin / admin123")
else:
    print("Users already exist")
