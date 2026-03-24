"""??????????????????????????????????????????????????"""

from django.core.management.base import BaseCommand

from shop.models import Category


class Command(BaseCommand):
    help = "Seed default shop categories into shop_category"

    DEFAULT_CATEGORIES = [
        "เครื่องนอน",
        "อุปกรณ์ห้องน้ำ",
        "เครื่องใช้ไฟฟ้า",
        "มินิบาร์",
        "ของใช้ในโรงแรม",
        "อุปกรณ์ทำความสะอาด",
        "เฟอร์นิเจอร์",
        "อุปกรณ์จัดเลี้ยง",
    ]

    def handle(self, *args, **options):
        created_count = 0

        for name in self.DEFAULT_CATEGORIES:
            _, created = Category.objects.get_or_create(
                name=name,
                defaults={"is_active": True},
            )
            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f"Created category: {name}"))
            else:
                self.stdout.write(f"Already exists: {name}")

        self.stdout.write(
            self.style.SUCCESS(
                f"Done. Seeded categories successfully. New categories created: {created_count}"
            )
        )
