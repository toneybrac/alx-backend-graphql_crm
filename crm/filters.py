import django_filters as filters
from .models import Customer, Product, Order
import re

class CustomerFilter(filters.FilterSet):
    # Filter by name (case-insensitive partial match)
    name_Icontains = filters.CharFilter(field_name='name', lookup_expr='icontains')

    # Filter by email (case-insensitive partial match)
    email_Icontains = filters.CharFilter(field_name='email', lookup_expr='icontains')

    # Filter by creation date range
    createdAt_Gte = filters.DateFilter(field_name='created_at', lookup_expr='gte')
    createdAt_Lte = filters.DateFilter(field_name='created_at', lookup_expr='lte')

    # Custom filter: phone number pattern (e.g., starts with +1)
    phone_Startswith = filters.CharFilter(field_name='phone', lookup_expr='startswith')

    class Meta:
        model = Customer
        fields = []
        order_by = ['name', 'email', 'created_at', '-name', '-email', '-created_at']

class ProductFilter(filters.FilterSet):
    # Filter by name (case-insensitive partial match)
    name_Icontains = filters.CharFilter(field_name='name', lookup_expr='icontains')

    # Filter by price range
    price_Gte = filters.NumberFilter(field_name='price', lookup_expr='gte')
    price_Lte = filters.NumberFilter(field_name='price', lookup_expr='lte')

    # Filter by stock (exact match or range)
    stock_Gte = filters.NumberFilter(field_name='stock', lookup_expr='gte')
    stock_Lte = filters.NumberFilter(field_name='stock', lookup_expr='lte')

    class Meta:
        model = Product
        fields = []
        order_by = ['name', 'price', 'stock', '-name', '-price', '-stock']

class OrderFilter(filters.FilterSet):
    # Filter by total amount range
    totalAmount_Gte = filters.NumberFilter(field_name='total_amount', lookup_expr='gte')
    totalAmount_Lte = filters.NumberFilter(field_name='total_amount', lookup_expr='lte')

    # Filter by order date range
    orderDate_Gte = filters.DateFilter(field_name='order_date', lookup_expr='gte')
    orderDate_Lte = filters.DateFilter(field_name='order_date', lookup_expr='lte')

    # Filter by customer name (related field, case-insensitive partial match)
    customerName_Icontains = filters.CharFilter(field_name='customer__name', lookup_expr='icontains')

    # Filter by product name (related field, case-insensitive partial match)
    productName_Icontains = filters.CharFilter(field_name='products__name', lookup_expr='icontains')

    # Challenge: Filter by specific product ID
    productId = filters.UUIDFilter(field_name='products__id', lookup_expr='exact')

    class Meta:
        model = Order
        fields = []
        order_by = ['order_date', 'total_amount', '-order_date', '-total_amount']

    @property
    def qs(self):
        """
        Override to handle ManyToMany filtering properly
        Ensures distinct results when filtering by related products
        """
        parent = super().qs
        return parent.distinct()
