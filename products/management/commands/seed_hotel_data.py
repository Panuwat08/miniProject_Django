import os
from django.core.management.base import BaseCommand
from products.models import Category, Product
from django.utils.text import slugify

class Command(BaseCommand):
    help = 'Seed comprehensive data for Hotel Equipment (Group 2)'

    def handle(self, *args, **kwargs):
        # ข้อมูลหมวดหมู่ 10 หมวดหมู่ (กลุ่มที่ 2)
        categories_data = [
            {"name": "ผ้าปูที่นอนและเครื่องนอน", "slug": "bedding-linen"},
            {"name": "เครื่องใช้ไฟฟ้าในห้องพัก", "slug": "room-appliances"},
            {"name": "ของใช้สิ้นเปลือง (Amenities)", "slug": "hotel-amenities"},
            {"name": "อุปกรณ์ในห้องน้ำ", "slug": "bathroom-accessories"},
            {"name": "มินิบาร์และเครื่องดื่ม", "slug": "minibar-beverages"},
            {"name": "อุปกรณ์ทำความสะอาด", "slug": "cleaning-housekeeping"},
            {"name": "ชุดพนักงานและยูนิฟอร์ม", "slug": "staff-uniforms"},
            {"name": "อุปกรณ์แผนกต้อนรับ (Front Office)", "slug": "front-office-supplies"},
            {"name": "ของตกแต่งและเฟอร์นิเจอร์", "slug": "decor-furniture"},
            {"name": "อุปกรณ์จัดเลี้ยงและห้องอาหาร", "slug": "banquet-fnb"},
        ]

        # สร้างหมวดหมู่
        cats = {}
        for cat_item in categories_data:
            obj, created = Category.objects.get_or_create(
                slug=cat_item["slug"],
                defaults={"name": cat_item["name"], "is_active": True}
            )
            cats[cat_item["slug"]] = obj
            if created:
                self.stdout.write(f'Created Category: {obj.name}')

        # ข้อมูลสินค้า (กลุ่มที่ 2)
        products_data = [
            {
                "category": cats["bedding-linen"],
                "name": "ชุดผ้าปูที่นอน Cotton 100% 500 เส้นด้าย",
                "price": 1250.00,
                "stock": 50,
                "description": "ผ้าปูที่นอนระดับพรีเมียม ให้สัมผัสนุ่มลื่น ระบายอากาศได้ดีเยี่ยม มาตรฐานโรงแรม 5 ดาว\nทนทานต่อการซักบ่อยครั้ง"
            },
            {
                "category": cats["bedding-linen"],
                "name": "หมอนขนห่านเทียม เกรดเอ",
                "price": 450.00,
                "stock": 100,
                "description": "นุ่มแน่น คืนตัวได้ดี ไม่สะสมไรฝุ่น เหมาะสำหรับการพักผ่อนอย่างเต็มที่"
            },
            {
                "category": cats["bathroom-accessories"],
                "name": "ชุดผ้าเช็ดตัว Cotton เกรดพรีเมียม",
                "price": 320.00,
                "stock": 80,
                "description": "ซึมซับน้ำได้ดี ขนไม่หลุดง่าย สีขาวสะอาดยอดนิยมสำหรับโรงแรม"
            },
            {
                "category": cats["room-appliances"],
                "name": "ไดร์เป่าผมแบบติดผนัง 1200W",
                "price": 890.00,
                "stock": 30,
                "description": "ดีไซน์ทันสมัย แข็งแรงทนทาน มีระบบตัดไฟอัตโนมัติเพื่อความปลอดภัย"
            },
            {
                "category": cats["room-appliances"],
                "name": "กาต้มน้ำไฟฟ้าความจุ 0.8 ลิตร (แสตนเลส)",
                "price": 750.00,
                "stock": 40,
                "description": "ขนาดกะทัดรัด ประหยัดพื้นที่ เหมาะสำหรับตั้งในห้องพัก"
            },
            {
                "category": cats["minibar-beverages"],
                "name": "ตู้เย็นขนาดเล็ก 40 ลิตร (เงียบพิเศษ)",
                "price": 4200.00,
                "stock": 15,
                "description": "ระบบระบายความร้อนที่ทำงานเงียบกริบ ไม่รบกวนการนอนของผู้เข้าพัก"
            },
            {
                "category": cats["hotel-amenities"],
                "name": "เซตแชมพูและสบู่เหลว กลิ่นเลมอนกราส",
                "price": 15.00,
                "stock": 500,
                "description": "ชุด Amenities ขนาดพกพา 30ml หอมสดชื่น ผ่อนคลายแบบไทย"
            },
            {
                "category": cats["hotel-amenities"],
                "name": "ชุดแปรงสีฟันและยาสีฟันพกพา",
                "price": 12.00,
                "stock": 1000,
                "description": "บรรจุในกล่องสวยงาม พร้อมใช้งานทันทีสำหรับแขก"
            },
            {
                "category": cats["cleaning-housekeeping"],
                "name": "รถเข็นแม่บ้านโรงแรม (Housekeeping Cart)",
                "price": 3500.00,
                "stock": 10,
                "description": "รถเข็นทรงตัวดี มีถุงใส่ผ้าขนาดใหญ่ และช่องแบ่งเก็บของหลากหลาย"
            },
            {
                "category": cats["staff-uniforms"],
                "name": "เสื้อเชิ้ตพนักงานต้อนรับ (Front Desk Uniform)",
                "price": 550.00,
                "stock": 60,
                "description": "เนื้อผ้าเบาสบาย รีดง่าย ดูเนี๊ยบตลอดวัน"
            },
            {
                "category": cats["front-office-supplies"],
                "name": "ป้ายตั้งโต๊ะ Reserved (สแตนเลส)",
                "price": 250.00,
                "stock": 45,
                "description": "ป้ายจองโต๊ะเรียบหรู สำหรับห้องอาหารหรือโซนต้อนรับพิเศษ"
            },
            {
                "category": cats["decor-furniture"],
                "name": "โคมไฟตั้งโต๊ะสไตล์ Minimal Luxury",
                "price": 1290.00,
                "stock": 25,
                "description": "ให้แสงไฟสีวอร์มไวทล์ ช่วยสร้างบรรยากาศอบอุ่นในห้องพัก"
            },
            {
                "category": cats["banquet-fnb"],
                "name": "ชุดถาดใส่อาหารสแตนเลสแบบมีฝาปิด (Chafing Dish)",
                "price": 2800.00,
                "stock": 20,
                "description": "สำหรับจัดไลน์บุฟเฟต์อาหารเช้า เก็บความร้อนได้ดีเยี่ยม"
            },
        ]

        # สร้างสินค้า
        for p_item in products_data:
            obj, created = Product.objects.get_or_create(
                slug=slugify(p_item["name"], allow_unicode=True),
                defaults={
                    "name": p_item["name"],
                    "category": p_item["category"],
                    "price": p_item["price"],
                    "stock": p_item["stock"],
                    "description": p_item["description"],
                    "is_active": True
                }
            )
            if created:
                self.stdout.write(f'Created Product: {obj.name}')

        self.stdout.write(self.style.SUCCESS('Successfully seeded Hotel Equipment data (Group 2)'))
