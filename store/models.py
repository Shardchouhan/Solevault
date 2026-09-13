import uuid
from decimal import Decimal
from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify
from django.db.models import Avg

class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    image = models.ImageField(upload_to='categories/', blank=True, null=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = 'Categories'
        ordering = ['name']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Brand(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    logo = models.ImageField(upload_to='brands/', blank=True, null=True)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ['name']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Product(models.Model):
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=280, unique=True, blank=True)
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE, related_name='products')
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')
    description = models.TextField()
    specifications = models.TextField(blank=True, help_text="Bullet points or details separated by newline")
    price = models.DecimalField(max_digits=10, decimal_places=2)
    discount_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    image = models.ImageField(upload_to='products/')
    stock = models.PositiveIntegerField(default=10)
    colors = models.CharField(max_length=200, default="Triple Black, Stealth Grey, Pure White")
    is_featured = models.BooleanField(default=False)
    is_new = models.BooleanField(default=True)
    is_best_seller = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            slug = base_slug
            counter = 1
            while Product.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.brand.name} {self.name}"

    @property
    def current_price(self):
        if self.discount_price and self.discount_price < self.price:
            return self.discount_price
        return self.price

    @property
    def has_discount(self):
        return bool(self.discount_price and self.discount_price < self.price)

    @property
    def discount_percent(self):
        if self.has_discount and self.price > 0:
            diff = self.price - self.discount_price
            return int(round((diff / self.price) * 100))
        return 0

    @property
    def in_stock(self):
        return self.stock > 0

    @property
    def average_rating(self):
        avg = self.reviews.aggregate(Avg('rating'))['rating__avg']
        return round(avg, 1) if avg else 5.0

    @property
    def rating_stars_count(self):
        return int(round(self.average_rating))

    @property
    def total_reviews(self):
        return self.reviews.count()

    @property
    def available_sizes(self):
        return self.sizes.filter(stock__gt=0)


class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='gallery_images')
    image = models.ImageField(upload_to='products/gallery/')
    caption = models.CharField(max_length=150, blank=True)

    def __str__(self):
        return f"Image for {self.product.name}"


class ProductSize(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='sizes')
    size = models.CharField(max_length=20, help_text="e.g. US 8, US 8.5, US 9")
    stock = models.PositiveIntegerField(default=5)

    class Meta:
        unique_together = ('product', 'size')
        ordering = ['size']

    def __str__(self):
        return f"{self.product.name} - {self.size} (Stock: {self.stock})"


class CartItem(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='cart_items')
    session_key = models.CharField(max_length=40, null=True, blank=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    size = models.CharField(max_length=20)
    quantity = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.product.name} ({self.size}) x {self.quantity}"

    @property
    def unit_price(self):
        return self.product.current_price

    @property
    def subtotal(self):
        return self.product.current_price * self.quantity


class Wishlist(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='wishlist_items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='wishlisted_by')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'product')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.product.name}"


class Coupon(models.Model):
    code = models.CharField(max_length=50, unique=True)
    discount_percent = models.PositiveIntegerField(default=0, help_text="Discount in percentage (0-100)")
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'), help_text="Flat discount amount")
    min_purchase = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    active = models.BooleanField(default=True)
    valid_to = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        if self.discount_percent > 0:
            return f"{self.code} ({self.discount_percent}% off)"
        return f"{self.code} (${self.discount_amount} off)"

    def calculate_discount(self, subtotal):
        if subtotal < self.min_purchase:
            return Decimal('0.00')
        if self.discount_percent > 0:
            return (subtotal * Decimal(self.discount_percent) / Decimal(100)).quantize(Decimal('0.01'))
        if self.discount_amount > 0:
            return min(self.discount_amount, subtotal)
        return Decimal('0.00')


class Order(models.Model):
    STATUS_CHOICES = (
        ('Pending', 'Pending'),
        ('Processing', 'Processing'),
        ('Shipped', 'Shipped'),
        ('Delivered', 'Delivered'),
        ('Cancelled', 'Cancelled'),
    )

    PAYMENT_METHOD_CHOICES = (
        ('Cash on Delivery (COD)', 'Cash on Delivery (COD)'),
        ('UPI (Google Pay / PhonePe / Paytm)', 'UPI (Google Pay / PhonePe / Paytm)'),
        ('Credit / Debit Card (Visa / Mastercard / RuPay)', 'Credit / Debit Card (Visa / Mastercard / RuPay)'),
        ('Net Banking', 'Net Banking (All Major Indian Banks)'),
    )

    order_number = models.CharField(max_length=36, unique=True, editable=False)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='orders')
    full_name = models.CharField(max_length=150)
    email = models.EmailField()
    phone = models.CharField(max_length=30)
    address = models.TextField()
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=30)
    country = models.CharField(max_length=100, default='India')
    
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    shipping_cost = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    
    coupon = models.ForeignKey(Coupon, on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='Processing')
    payment_method = models.CharField(max_length=80, choices=PAYMENT_METHOD_CHOICES, default='UPI (Google Pay / PhonePe / Paytm)')
    payment_status = models.CharField(max_length=30, default='Pending')
    tracking_number = models.CharField(max_length=50, blank=True)
    order_notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.order_number:
            self.order_number = f"SV-{uuid.uuid4().hex[:8].upper()}"
        if not self.tracking_number and self.order_number:
            self.tracking_number = f"TRK-{self.order_number[3:]}-US"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Order {self.order_number} by {self.full_name}"

    @property
    def total_items(self):
        return sum(item.quantity for item in self.items.all())


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    selected_size = models.CharField(max_length=20)
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.product.name} ({self.selected_size}) x {self.quantity}"

    @property
    def subtotal(self):
        return self.price * self.quantity


class Review(models.Model):
    RATING_CHOICES = (
        (5, '5 - Exceptional'),
        (4, '4 - Great Quality'),
        (3, '3 - Average'),
        (2, '2 - Below Expectations'),
        (1, '1 - Poor'),
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    rating = models.PositiveSmallIntegerField(choices=RATING_CHOICES, default=5)
    title = models.CharField(max_length=150, blank=True)
    comment = models.TextField()
    verified_buyer = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Review by {self.user.username} on {self.product.name} ({self.rating}/5)"


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    phone = models.CharField(max_length=30, blank=True)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=30, blank=True)
    country = models.CharField(max_length=100, default='India')
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)

    def __str__(self):
        return f"Profile for {self.user.username}"


class NewsletterSubscriber(models.Model):
    email = models.EmailField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.email


class ContactMessage(models.Model):
    name = models.CharField(max_length=150)
    email = models.EmailField()
    subject = models.CharField(max_length=200)
    message = models.TextField()
    is_resolved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Message from {self.name} - {self.subject}"
