from django.shortcuts import render
from django.db.models import Sum, F
from django.db.models.functions import TruncMonth, TruncDate
from orders.models import Order, OrderItem
from products.models import Product
import openpyxl
from django.http import HttpResponse
from reportlab.pdfgen import canvas


# ==============================
# รายงานยอดขาย
# ==============================
def sales_report(request):

    start_date = request.GET.get("start_date")
    end_date = request.GET.get("end_date")
    report_type = request.GET.get("type", "monthly")

    orders = Order.objects.all()

    if start_date and end_date:
        orders = orders.filter(created_at__date__range=[start_date, end_date])

    if report_type == "daily":
        sales = (
            orders
            .annotate(period=TruncDate("created_at"))
            .values("period")
            .annotate(total_sales=Sum("total"))
            .order_by("period")
        )
    else:
        sales = (
            orders
            .annotate(period=TruncMonth("created_at"))
            .values("period")
            .annotate(total_sales=Sum("total"))
            .order_by("period")
        )

    labels = [str(s["period"]) for s in sales]
    data = [float(s["total_sales"]) for s in sales]


    # ==============================
    # สินค้าขายดี
    # ==============================
    order_items = OrderItem.objects.filter(order__in=orders)

    top_products = (
        order_items
        .values("product__name")
        .annotate(total_qty=Sum("qty"))
        .order_by("-total_qty")[:5]
    )

    return render(request, "reports/sales_report.html", {
        "sales": sales,
        "labels": labels,
        "data": data,
        "top_products": top_products,
    })


# ==============================
# รายงานยอดขายตามสินค้า
# ==============================
def product_report(request):

    products = (
        OrderItem.objects
        .values('product__name')
        .annotate(total_sales=Sum('price'))
        .order_by('-total_sales')
    )

    return render(request, 'reports/product_report.html', {
        'products': products
    })


# ==============================
# รายงานกำไร
# ==============================
def profit_report(request):

    products = Product.objects.annotate(
        profit=F('price') - F('cost')
    )

    return render(request, 'reports/profit_report.html', {
        'products': products
    })


# ==============================
# Export Excel
# ==============================
def export_excel(request):

    start_date = request.GET.get("start_date")
    end_date = request.GET.get("end_date")
    report_type = request.GET.get("type", "monthly")

    orders = Order.objects.all()

    if start_date and end_date:
        orders = orders.filter(created_at__date__range=[start_date, end_date])

    if report_type == "daily":
        sales = (
            orders
            .annotate(period=TruncDate("created_at"))
            .values("period")
            .annotate(total_sales=Sum("total"))
            .order_by("period")
        )
    else:
        sales = (
            orders
            .annotate(period=TruncMonth("created_at"))
            .values("period")
            .annotate(total_sales=Sum("total"))
            .order_by("period")
        )

    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = "Sales Report"

    sheet.append(["Period", "Total Sales"])

    for s in sales:
        sheet.append([
            str(s["period"]),
            s["total_sales"]
        ])

    response = HttpResponse(content_type='application/ms-excel')
    response['Content-Disposition'] = 'attachment; filename="sales_report.xlsx"'

    workbook.save(response)

    return response


# ==============================
# Export PDF
# ==============================
def export_pdf(request):

    start_date = request.GET.get("start_date")
    end_date = request.GET.get("end_date")
    report_type = request.GET.get("type", "monthly")

    orders = Order.objects.all()

    if start_date and end_date:
        orders = orders.filter(created_at__date__range=[start_date, end_date])

    if report_type == "daily":
        sales = (
            orders
            .annotate(period=TruncDate("created_at"))
            .values("period")
            .annotate(total_sales=Sum("total"))
            .order_by("period")
        )
    else:
        sales = (
            orders
            .annotate(period=TruncMonth("created_at"))
            .values("period")
            .annotate(total_sales=Sum("total"))
            .order_by("period")
        )

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="sales_report.pdf"'

    p = canvas.Canvas(response)

    y = 800
    p.drawString(100, y, "Sales Report")

    y -= 40

    for s in sales:
        text = f"{s['period']} : {s['total_sales']} บาท"
        p.drawString(100, y, text)
        y -= 25

    p.showPage()
    p.save()

    return response