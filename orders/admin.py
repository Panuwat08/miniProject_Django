from django.contrib import admin
from .models import ShippingAddress, Order, OrderItem, PaymentSlip, Notification

admin.site.register(ShippingAddress)
admin.site.register(Order)
admin.site.register(OrderItem)
admin.site.register(PaymentSlip)
admin.site.register(Notification)
