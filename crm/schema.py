import graphene
from graphene import relay
from graphene_django import DjangoObjectType
from graphene_django.filter import DjangoFilterConnectionField
from django.db import transaction
from django.core.exceptions import ValidationError
import re
from datetime import datetime
from .models import Customer, Product, Order
from .filters import CustomerFilter, ProductFilter, OrderFilter

# ============ TYPE DEFINITIONS ============

# Node types for Relay connections with filtering
class CustomerNode(DjangoObjectType):
    class Meta:
        model = Customer
        interfaces = (relay.Node,)
        filterset_class = CustomerFilter

class ProductNode(DjangoObjectType):
    class Meta:
        model = Product
        interfaces = (relay.Node,)
        filterset_class = ProductFilter

class OrderNode(DjangoObjectType):
    class Meta:
        model = Order
        interfaces = (relay.Node,)
        filterset_class = OrderFilter
    
    products = graphene.List(ProductNode)
    
    def resolve_products(self, info):
        return self.products.all()

# Regular Types for backward compatibility (from Task 1)
class CustomerType(DjangoObjectType):
    class Meta:
        model = Customer
        fields = "__all__"

class ProductType(DjangoObjectType):
    class Meta:
        model = Product
        fields = "__all__"

class OrderType(DjangoObjectType):
    class Meta:
        model = Order
        fields = "__all__"
    
    products = graphene.List(ProductType)
    
    def resolve_products(self, info):
        return self.products.all()

# ============ NEW TYPES FOR LOW-STOCK MUTATION ============

class ProductUpdateType(graphene.ObjectType):
    """Type representing an updated product for low-stock mutation"""
    id = graphene.String()
    name = graphene.String()
    old_stock = graphene.Int()
    new_stock = graphene.Int()
    updated_at = graphene.String()

class UpdateLowStockProductsResponse(graphene.ObjectType):
    """Response type for the low-stock update mutation"""
    success = graphene.Boolean()
    message = graphene.String()
    updated_products = graphene.List(ProductUpdateType)
    total_updated = graphene.Int()

# ============ INPUT TYPES (From Task 1) ============

class CustomerInput(graphene.InputObjectType):
    name = graphene.String(required=True)
    email = graphene.String(required=True)
    phone = graphene.String()

class BulkCustomerInput(graphene.InputObjectType):
    customers = graphene.List(CustomerInput, required=True)

class ProductInput(graphene.InputObjectType):
    name = graphene.String(required=True)
    price = graphene.Decimal(required=True)
    stock = graphene.Int()

class OrderInput(graphene.InputObjectType):
    customer_id = graphene.String(required=True)
    product_ids = graphene.List(graphene.String, required=True)
    order_date = graphene.DateTime()

# ============ RESPONSE TYPES (From Task 1) ============

class CreateCustomerResponse(graphene.ObjectType):
    customer = graphene.Field(CustomerType)
    message = graphene.String()

class BulkCreateCustomersResponse(graphene.ObjectType):
    customers = graphene.List(CustomerType)
    errors = graphene.List(graphene.String)

class CreateProductResponse(graphene.ObjectType):
    product = graphene.Field(ProductType)

class CreateOrderResponse(graphene.ObjectType):
    order = graphene.Field(OrderType)

# ============ MUTATIONS (From Task 1 - Keep as is) ============

class CreateCustomer(graphene.Mutation):
    class Arguments:
        input = CustomerInput(required=True)
    
    Output = CreateCustomerResponse
    
    @staticmethod
    def validate_phone(phone):
        if phone:
            # Validate phone format: +1234567890 or 123-456-7890
            pattern = r'^(\+\d{10,15}|\d{3}-\d{3}-\d{4})$'
            if not re.match(pattern, phone):
                raise ValidationError("Phone must be in format +1234567890 or 123-456-7890")
        return phone
    
    @staticmethod
    def mutate(root, info, input):
        try:
            # Validate phone
            if input.phone:
                CreateCustomer.validate_phone(input.phone)
            
            # Check if email already exists
            if Customer.objects.filter(email=input.email).exists():
                raise ValidationError(f"Email '{input.email}' already exists")
            
            customer = Customer(
                name=input.name,
                email=input.email,
                phone=input.phone
            )
            customer.full_clean()
            customer.save()
            
            return CreateCustomerResponse(
                customer=customer,
                message="Customer created successfully"
            )
        
        except ValidationError as e:
            raise ValidationError(str(e))
        except Exception as e:
            raise ValidationError(f"Error creating customer: {str(e)}")

class BulkCreateCustomers(graphene.Mutation):
    class Arguments:
        input = BulkCustomerInput(required=True)
    
    Output = BulkCreateCustomersResponse
    
    @staticmethod
    def mutate(root, info, input):
        customers = []
        errors = []
        
        with transaction.atomic():
            for idx, customer_data in enumerate(input.customers):
                try:
                    # Validate phone
                    if customer_data.phone:
                        CreateCustomer.validate_phone(customer_data.phone)
                    
                    # Check if email already exists
                    if Customer.objects.filter(email=customer_data.email).exists():
                        errors.append(f"Row {idx + 1}: Email '{customer_data.email}' already exists")
                        continue
                    
                    customer = Customer(
                        name=customer_data.name,
                        email=customer_data.email,
                        phone=customer_data.phone
                    )
                    customer.full_clean()
                    customer.save()
                    customers.append(customer)
                    
                except ValidationError as e:
                    errors.append(f"Row {idx + 1}: {str(e)}")
                except Exception as e:
                    errors.append(f"Row {idx + 1}: {str(e)}")
        
        return BulkCreateCustomersResponse(
            customers=customers,
            errors=errors
        )

class CreateProduct(graphene.Mutation):
    class Arguments:
        input = ProductInput(required=True)
    
    Output = CreateProductResponse
    
    @staticmethod
    def mutate(root, info, input):
        try:
            # Validate price is positive
            if input.price <= 0:
                raise ValidationError("Price must be positive")
            
            # Validate stock is not negative
            stock = input.stock if input.stock is not None else 0
            if stock < 0:
                raise ValidationError("Stock cannot be negative")
            
            product = Product(
                name=input.name,
                price=input.price,
                stock=stock
            )
            product.full_clean()
            product.save()
            
            return CreateProductResponse(product=product)
        
        except ValidationError as e:
            raise ValidationError(str(e))
        except Exception as e:
            raise ValidationError(f"Error creating product: {str(e)}")

class CreateOrder(graphene.Mutation):
    class Arguments:
        input = OrderInput(required=True)
    
    Output = CreateOrderResponse
    
    @staticmethod
    def mutate(root, info, input):
        try:
            # Validate customer exists
            try:
                customer = Customer.objects.get(id=input.customer_id)
            except Customer.DoesNotExist:
                raise ValidationError(f"Customer with ID '{input.customer_id}' does not exist")
            
            # Validate products exist
            products = []
            for product_id in input.product_ids:
                try:
                    product = Product.objects.get(id=product_id)
                    products.append(product)
                except Product.DoesNotExist:
                    raise ValidationError(f"Product with ID '{product_id}' does not exist")
            
            # Ensure at least one product
            if not products:
                raise ValidationError("At least one product is required")
            
            # Calculate total amount
            total_amount = sum(product.price for product in products)
            
            # Create order
            order = Order(
                customer=customer,
                total_amount=total_amount
            )
            order.save()
            order.products.set(products)
            
            return CreateOrderResponse(order=order)
        
        except ValidationError as e:
            raise ValidationError(str(e))
        except Exception as e:
            raise ValidationError(f"Error creating order: {str(e)}")

# ============ NEW MUTATION FOR LOW-STOCK PRODUCTS ============

class UpdateLowStockProducts(graphene.Mutation):
    """
    Mutation to update low-stock products (stock < 10)
    Increments stock by 10 (simulating restocking)
    Returns a list of updated products and a success message
    """
    
    class Arguments:
        """Optional arguments for the mutation"""
        increment_by = graphene.Int(
            description="Amount to increment stock by (default: 10)",
            default_value=10
        )
        threshold = graphene.Int(
            description="Stock threshold (default: 10)",
            default_value=10
        )
    
    Output = UpdateLowStockProductsResponse
    
    @staticmethod
    @transaction.atomic
    def mutate(root, info, increment_by=10, threshold=10):
        """
        Execute the mutation to update low-stock products
        
        Queries products with stock < threshold
        Increments their stock by increment_by
        Returns updated products and success message
        """
        try:
            # Query products with stock less than threshold
            low_stock_products = Product.objects.filter(stock__lt=threshold)
            
            if not low_stock_products.exists():
                return UpdateLowStockProductsResponse(
                    success=True,
                    message=f"No products found with stock less than {threshold}",
                    updated_products=[],
                    total_updated=0
                )
            
            updated_products_data = []
            
            # Update each product and collect data
            for product in low_stock_products:
                old_stock = product.stock
                new_stock = old_stock + increment_by
                
                # Update the product stock
                product.stock = new_stock
                product.save()
                
                # Add to response data
                updated_products_data.append(ProductUpdateType(
                    id=str(product.id),
                    name=product.name,
                    old_stock=old_stock,
                    new_stock=new_stock,
                    updated_at=datetime.now().isoformat()
                ))
            
            # Return success response
            return UpdateLowStockProductsResponse(
                success=True,
                message=f"Successfully updated {len(updated_products_data)} products with stock less than {threshold}",
                updated_products=updated_products_data,
                total_updated=len(updated_products_data)
            )
            
        except Exception as e:
            # Rollback transaction on error
            transaction.set_rollback(True)
            return UpdateLowStockProductsResponse(
                success=False,
                message=f"Error updating low-stock products: {str(e)}",
                updated_products=[],
                total_updated=0
            )

# ============ QUERY CLASS WITH FILTERING (Task 3) ============

class Query(graphene.ObjectType):
    # Relay-style connections with filtering (Task 3)
    all_customers = DjangoFilterConnectionField(CustomerNode)
    all_products = DjangoFilterConnectionField(ProductNode)
    all_orders = DjangoFilterConnectionField(OrderNode)
    
    # Regular queries (from Task 1 - keep for backward compatibility)
    customers = graphene.List(CustomerType)
    products = graphene.List(ProductType)
    orders = graphene.List(OrderType)
    
    # New query for low-stock products
    low_stock_products = graphene.List(
        ProductType,
        threshold=graphene.Int(default_value=10)
    )
    
    def resolve_customers(self, info):
        return Customer.objects.all()
    
    def resolve_products(self, info):
        return Product.objects.all()
    
    def resolve_orders(self, info):
        return Order.objects.all()
    
    def resolve_low_stock_products(self, info, threshold=10):
        """Query to get low-stock products"""
        return Product.objects.filter(stock__lt=threshold)

# ============ MUTATION CLASS (Updated with low-stock mutation) ============

class Mutation(graphene.ObjectType):
    # Existing mutations
    create_customer = CreateCustomer.Field()
    bulk_create_customers = BulkCreateCustomers.Field()
    create_product = CreateProduct.Field()
    create_order = CreateOrder.Field()
    
    # New mutation for low-stock products
    update_low_stock_products = UpdateLowStockProducts.Field()

# ============ SCHEMA DEFINITION ============

schema = graphene.Schema(query=Query, mutation=Mutation)
