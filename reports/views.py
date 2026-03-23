import openpyxl
import os
from django.contrib.auth.decorators import login_required
from django.db.models import DecimalField, ExpressionWrapper, F, Sum
from django.db.models.functions import TruncDate, TruncMonth
from django.http import HttpResponse
from django.shortcuts import render
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from orders.models import Order, OrderItem, OrderStatus
from shop.models import Product


PAID_STATUSES = [OrderStatus.PAID, OrderStatus.SHIPPED, OrderStatus.COMPLETED]


def _register_thai_pdf_fonts():
    regular_name = "TahomaThai"
    bold_name = "TahomaThai-Bold"

    if regular_name not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont(regular_name, os.path.join(os.environ["WINDIR"], "Fonts", "tahoma.ttf")))

    if bold_name not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont(bold_name, os.path.join(os.environ["WINDIR"], "Fonts", "tahomabd.ttf")))

    return regular_name, bold_name


def _filtered_orders(request):
    start_date = request.GET.get("start_date")
    end_date = request.GET.get("end_date")
    report_type = request.GET.get("type", "monthly")

    invalid_date_values = {"", "None", "null", None}
    if start_date in invalid_date_values:
        start_date = None
    if end_date in invalid_date_values:
        end_date = None

    orders = Order.objects.filter(status__in=PAID_STATUSES)
    if start_date and end_date:
        orders = orders.filter(created_at__date__range=[start_date, end_date])

    return orders, start_date, end_date, report_type


def _sales_summary(orders, report_type):
    trunc = TruncDate("created_at") if report_type == "daily" else TruncMonth("created_at")
    sales = (
        orders.annotate(period=trunc)
        .values("period")
        .annotate(total_sales=Sum("total"))
        .order_by("period")
    )
    labels = [str(row["period"]) for row in sales]
    data = [float(row["total_sales"] or 0) for row in sales]
    return sales, labels, data


def _sales_export_rows(orders):
    return (
        OrderItem.objects.filter(order__in=orders)
        .values("order__created_at__date", "product__name", "price")
        .annotate(
            total_qty=Sum("qty"),
            total_amount=Sum(
                ExpressionWrapper(F("price") * F("qty"), output_field=DecimalField(max_digits=12, decimal_places=2))
            ),
        )
        .order_by("order__created_at__date", "product__name", "price")
    )


@login_required
def sales_report(request):
    orders, start_date, end_date, report_type = _filtered_orders(request)
    sales, labels, data = _sales_summary(orders, report_type)

    top_products = (
        OrderItem.objects.filter(order__in=orders)
        .values("product__name")
        .annotate(total_qty=Sum("qty"))
        .order_by("-total_qty", "product__name")[:10]
    )

    return render(
        request,
        "reports/sales_report.html",
        {
            "sales": sales,
            "labels": labels,
            "data": data,
            "top_products": top_products,
            "selected_type": report_type,
            "start_date": start_date,
            "end_date": end_date,
        },
    )


@login_required
def product_report(request):
    orders, start_date, end_date, report_type = _filtered_orders(request)
    items = OrderItem.objects.filter(order__in=orders)

    products = (
        items.values("product__name", "product__category__name", "product__stock")
        .annotate(
            total_qty=Sum("qty"),
            total_sales=Sum(ExpressionWrapper(F("price") * F("qty"), output_field=DecimalField())),
        )
        .order_by("-total_qty", "product__name")
    )

    return render(
        request,
        "reports/product_report.html",
        {
            "products": products,
            "selected_type": report_type,
            "start_date": start_date,
            "end_date": end_date,
        },
    )


@login_required
def profit_report(request):
    orders, start_date, end_date, report_type = _filtered_orders(request)
    items = OrderItem.objects.filter(order__in=orders)

    profits = (
        items.values("product__name", "product__category__name")
        .annotate(
            total_qty=Sum("qty"),
            revenue=Sum(ExpressionWrapper(F("price") * F("qty"), output_field=DecimalField())),
            cost_total=Sum(ExpressionWrapper(F("cost") * F("qty"), output_field=DecimalField())),
        )
        .annotate(profit=ExpressionWrapper(F("revenue") - F("cost_total"), output_field=DecimalField()))
        .order_by("-profit", "product__name")
    )

    inventory = Product.objects.filter(is_active=True).order_by("name")

    return render(
        request,
        "reports/profit_report.html",
        {
            "profits": profits,
            "inventory": inventory,
            "selected_type": report_type,
            "start_date": start_date,
            "end_date": end_date,
        },
    )


@login_required
def export_excel(request):
    orders, _, _, report_type = _filtered_orders(request)
    sales, _, _ = _sales_summary(orders, report_type)
    export_rows = _sales_export_rows(orders)

    workbook = openpyxl.Workbook()
    detail_sheet = workbook.active
    detail_sheet.title = "รายละเอียดสินค้า"
    detail_sheet.append(["ลำดับที่", "ช่วงเวลา", "ชื่อสินค้า", "จำนวนสินค้า", "ราคา", "รวมทั้งหมด"])
    for index, row in enumerate(export_rows, start=1):
        detail_sheet.append(
            [
                index,
                str(row["order__created_at__date"]),
                row["product__name"],
                int(row["total_qty"] or 0),
                float(row["price"] or 0),
                float(row["total_amount"] or 0),
            ]
        )

    summary_sheet = workbook.create_sheet("สรุปยอดขาย")
    summary_sheet.append(["ช่วงเวลา", "ยอดขายรวม"])

    for row in sales:
        summary_sheet.append([str(row["period"]), float(row["total_sales"] or 0)])

    response = HttpResponse(content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    response["Content-Disposition"] = 'attachment; filename="sales_report.xlsx"'
    workbook.save(response)
    return response


@login_required
def export_pdf(request):
    orders, _, _, report_type = _filtered_orders(request)
    export_rows = _sales_export_rows(orders)
    regular_font, bold_font = _register_thai_pdf_fonts()

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = 'attachment; filename="sales_report.pdf"'

    document = SimpleDocTemplate(
        response,
        pagesize=A4,
        leftMargin=30,
        rightMargin=30,
        topMargin=30,
        bottomMargin=30,
    )
    styles = getSampleStyleSheet()
    styles["Title"].fontName = bold_font
    styles["Title"].fontSize = 18
    styles["Normal"].fontName = regular_font
    styles["Normal"].fontSize = 10
    elements = [
        Paragraph("รายงานยอดขาย", styles["Title"]),
        Spacer(1, 12),
        Paragraph(f"ประเภทรายงาน: {'รายวัน' if report_type == 'daily' else 'รายเดือน'}", styles["Normal"]),
        Spacer(1, 16),
    ]

    table_data = [["ลำดับที่", "ชื่อสินค้า", "ราคา", "รวม"]]
    for index, row in enumerate(export_rows, start=1):
        table_data.append(
            [
                str(index),
                str(row["product__name"]),
                f"{float(row['price'] or 0):,.2f}",
                f"{float(row['total_amount'] or 0):,.2f}",
            ]
        )

    if len(table_data) == 1:
        table_data.append(["-", "ไม่มีข้อมูล", "-", "-"])

    report_table = Table(table_data, colWidths=[45, 255, 90, 100])
    report_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#243b6b")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), bold_font),
                ("FONTNAME", (0, 1), (-1, -1), regular_font),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("ALIGN", (1, 1), (1, -1), "LEFT"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("GRID", (0, 0), (-1, -1), 0.8, colors.HexColor("#94a3b8")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.HexColor("#eef4ff")]),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 10),
                ("TOPPADDING", (0, 0), (-1, 0), 10),
            ]
        )
    )

    elements.append(report_table)
    document.build(elements)
    return response
