from django.urls import path
from . import views

urlpatterns = [

    path('sales/', views.sales_report, name='sales_report'),
    path('product/', views.product_report, name='product_report'),
    path('profit/', views.profit_report, name='profit_report'),
    path('export/excel/', views.export_excel, name='export_excel'),
    path('export/pdf/', views.export_pdf, name='export_pdf'),

]