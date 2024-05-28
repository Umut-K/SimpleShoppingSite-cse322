from django.db import models
from django.contrib.auth.models import User
from PIL import Image



class Address(models.Model):
    ADDRESS_TYPE_CHOICES = (
        ('shipping', 'Shipping'),
        ('billing', 'Billing'),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='addresses', null= True)
    street = models.CharField(max_length=100, null=True)
    city = models.CharField(max_length=20, null=True)
    state = models.CharField(max_length=2, null=True)
    postcode = models.SmallIntegerField(null=True)
    address_type = models.CharField(max_length=10, choices=ADDRESS_TYPE_CHOICES, null= True)

    def __str__(self):
        return f"{self.address_type.capitalize()} Address: {self.street}, {self.city}, {self.state} {self.postcode}"


class Product(models.Model):
    name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.IntegerField()
    image = models.ImageField(upload_to='product_images/', blank=True, null=True)
    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.image:
            img = Image.open(self.image.path)
            if img.height > 300 or img.width > 300:
                output_size = (300, 300)
                img.thumbnail(output_size)
                img.save(self.image.path)

class Customer(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, null= True)
    name = models.CharField(max_length=100)
    email = models.EmailField(unique=False)
    def __str__(self):
        return self.name

class BillingAddress(Address):
    pass

class ShippingAddress(Address):
    pass

class Order(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null= True)
    shipping_address = models.OneToOneField(Address, on_delete=models.CASCADE, related_name='shipping_order', null= True)
    billing_address = models.OneToOneField(Address, on_delete=models.CASCADE, related_name='billing_order', null= True)
    status = models.CharField(max_length=20, default='Pending')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Order by {self.user} - Shipping: {self.shipping_address}, Billing: {self.billing_address} - {self.status}"

class OrderPayment(models.Model):
    cardNumber = models.BigIntegerField()
    txnId = models.IntegerField()
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    billing_address = models.ForeignKey(BillingAddress, on_delete=models.CASCADE)

class OrderItem(models.Model):
    price = models.FloatField()
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField()

    def __str__(self):
        return f"{self.quantity} x {self.product.name} at {self.price}"


class BasketItem(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='basket_items', null=True, blank=True)
    session_key = models.CharField(max_length=32, null=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1)


    def __str__(self):
        return f'{self.quantity} of {self.product.name}'