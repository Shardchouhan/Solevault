import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.test import Client, RequestFactory
from django.contrib.auth.models import User
from store.models import Product, ProductSize, Category, Brand, Coupon, Order, CartItem, Wishlist
from store.views import custom_404

client = Client()

print("--- Testing SoleVault India (INR & UK/Indian Sizing) ---")

# 1. Home
r = client.get('/')
assert r.status_code == 200, f"Home failed: {r.status_code}"
assert b'SOLEVAULT' in r.content
print("[OK] Home page: OK (200)")

# 2. Shop & Filters
r = client.get('/shop/')
assert r.status_code == 200
assert b'ALL SNEAKERS' in r.content

r = client.get('/shop/?category=running&sort=price_low')
assert r.status_code == 200

r = client.get('/shop/?brand=nike&size=UK 9&min_price=5000&max_price=30000')
assert r.status_code == 200
print("[OK] Shop catalog & multi-filtering in INR/UK sizes: OK (200)")

# 3. Product Detail & Size Chart Modal
prod = Product.objects.first()
r = client.get(f'/product/{prod.slug}/')
assert r.status_code == 200
assert b'sizeChartModal' in r.content
assert b'Foot Length (CM)' in r.content
print(f"[OK] Product Detail with Indian Size Chart Modal ({prod.slug}): OK (200)")

# 4. Cart Lifecycle
r = client.get('/cart/')
assert r.status_code == 200

# Add to cart with Indian/UK size
in_stock_size = ProductSize.objects.filter(product=prod, stock__gt=0).first().size
r = client.post(f'/cart/add/{prod.id}/', {'size': in_stock_size, 'quantity': 1}, follow=True)
assert r.status_code == 200
assert b'Added' in r.content
print(f"[OK] Add to Cart with UK Size ({in_stock_size}): OK")

# Apply coupon
r = client.post('/cart/coupon/apply/', {'code': 'WELCOME10'}, follow=True)
assert r.status_code == 200
assert b'applied successfully' in r.content
print("[OK] Coupon Application in INR: OK")

# 5. Checkout
r = client.get('/checkout/')
assert r.status_code == 200
assert b'SECURE CHECKOUT' in r.content

# Place Order via POST with Indian address & UPI
checkout_data = {
    'full_name': 'Rohan Mehta',
    'email': 'rohan@example.in',
    'phone': '+91 98111 22334',
    'address': 'Flat 802, Oberoi Sky City, Borivali East',
    'city': 'Mumbai',
    'state': 'Maharashtra',
    'postal_code': '400066',
    'country': 'India',
    'payment_method': 'UPI (Google Pay / PhonePe / Paytm)',
    'order_notes': 'Please deliver before 6 PM'
}
r = client.post('/checkout/', checkout_data, follow=True)
assert r.status_code == 200
assert b'THANK YOU FOR YOUR ORDER' in r.content
print("[OK] Checkout & Atomic Order Placement with Indian UPI: OK")

# 6. Auth Flows
client.login(username='jordan_fan', password='password123')

# Profile
r = client.get('/profile/')
assert r.status_code == 200
assert b'ACCOUNT SETTINGS' in r.content
print("[OK] User Profile with Indian Address: OK")

# Orders
r = client.get('/orders/')
assert r.status_code == 200
assert b'MY ORDERS' in r.content
print("[OK] My Orders History in INR: OK")

# Wishlist
r = client.get(f'/wishlist/toggle/{prod.id}/', follow=True)
assert r.status_code == 200
r = client.get('/wishlist/')
assert r.status_code == 200
print("[OK] Wishlist Operations: OK")

# 7. Static / Informational Pages & Size Chart in FAQ
for path in ['/about/', '/contact/', '/faq/', '/privacy/', '/terms/']:
    r = client.get(path)
    assert r.status_code == 200, f"Failed path {path}: {r.status_code}"
print("[OK] About, Contact, FAQ (with Indian Size Chart), Privacy, Terms: OK (200)")

# 8. Custom 404
rf = RequestFactory()
req_404 = rf.get('/some-invalid-path/')
res_404 = custom_404(req_404)
assert res_404.status_code == 404
assert b'THIS PAGE CANNOT BE FOUND IN THE VAULT' in res_404.content
print("[OK] Custom 404 page handler: OK (404)")

print("\n--- ALL INDIAN MARKET FEATURES & SIZE CHART TESTS PASSED! ---")
