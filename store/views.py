import json
from decimal import Decimal
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth import login, logout, authenticate, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db import transaction, models
from django.db.models import Q, Count, Avg, F
from django.db.models.functions import Coalesce
from django.http import JsonResponse, HttpResponseRedirect
from django.urls import reverse
from django.views.decorators.http import require_POST

from .models import (
    Category, Brand, Product, ProductImage, ProductSize,
    CartItem, Wishlist, Coupon, Order, OrderItem,
    Review, UserProfile, NewsletterSubscriber, ContactMessage
)
from .forms import (
    UserRegistrationForm, UserLoginForm, UserProfileForm,
    CheckoutForm, ReviewForm, CouponApplyForm, ContactForm, NewsletterForm
)


# ==========================================
# HELPER FUNCTIONS
# ==========================================

def get_session_key(request):
    """Ensure session exists and return the key."""
    if not request.session.session_key:
        request.session.create()
    return request.session.session_key


def get_cart_queryset(request):
    """Return cart items for either authenticated user or anonymous session."""
    if request.user.is_authenticated:
        return CartItem.objects.filter(user=request.user).select_related('product', 'product__brand')
    else:
        key = get_session_key(request)
        return CartItem.objects.filter(session_key=key).select_related('product', 'product__brand')


def merge_session_cart_to_user(request, user):
    """When a user logs in, merge their guest session cart items into their account."""
    if not request.session.session_key:
        return
    session_items = CartItem.objects.filter(session_key=request.session.session_key)
    for s_item in session_items:
        existing = CartItem.objects.filter(user=user, product=s_item.product, size=s_item.size).first()
        if existing:
            existing.quantity += s_item.quantity
            existing.save()
            s_item.delete()
        else:
            s_item.user = user
            s_item.session_key = None
            s_item.save()


def get_cart_summary(request):
    """Calculate cart subtotal, coupon discounts, shipping and grand total."""
    cart_items = get_cart_queryset(request)
    subtotal = sum(item.subtotal for item in cart_items)
    
    # Coupon calculation
    coupon_id = request.session.get('coupon_id')
    coupon = None
    discount = Decimal('0.00')
    if coupon_id:
        try:
            coupon = Coupon.objects.get(id=coupon_id, active=True)
            discount = coupon.calculate_discount(subtotal)
        except Coupon.DoesNotExist:
            if 'coupon_id' in request.session:
                del request.session['coupon_id']

    # Free shipping on orders over ₹4,999, else flat ₹299.00 (or ₹0 if cart is empty)
    if subtotal == 0:
        shipping = Decimal('0.00')
    elif subtotal >= Decimal('4999.00'):
        shipping = Decimal('0.00')
    else:
        shipping = Decimal('299.00')

    grand_total = max(Decimal('0.00'), subtotal - discount + shipping)

    return {
        'cart_items': cart_items,
        'subtotal': subtotal,
        'discount': discount,
        'coupon': coupon,
        'shipping': shipping,
        'grand_total': grand_total,
        'free_shipping_threshold': Decimal('4999.00'),
        'free_shipping_remaining': max(Decimal('0.00'), Decimal('4999.00') - subtotal)
    }


# ==========================================
# CORE STORE VIEWS
# ==========================================

def home(request):
    """Homepage with hero banner, categories, new arrivals, best sellers, etc."""
    featured_categories = Category.objects.all()[:5]
    new_arrivals = Product.objects.filter(is_new=True)[:8]
    best_sellers = Product.objects.filter(is_best_seller=True)[:6]
    featured_products = Product.objects.filter(is_featured=True)[:4]

    # If not enough new/best sellers are flagged, fallback to recent products
    if not new_arrivals:
        new_arrivals = Product.objects.all()[:8]
    if not best_sellers:
        best_sellers = Product.objects.all().order_by('-price')[:6]

    context = {
        'featured_categories': featured_categories,
        'new_arrivals': new_arrivals,
        'best_sellers': best_sellers,
        'featured_products': featured_products,
    }
    return render(request, 'home.html', context)


def shop(request):
    """Product catalog with robust multi-filtering, search, sorting and pagination."""
    products = Product.objects.all().select_related('brand', 'category').prefetch_related('sizes', 'reviews')

    # 1. Search Query
    q = request.GET.get('q', '').strip()
    if q:
        products = products.filter(
            Q(name__icontains=q) |
            Q(description__icontains=q) |
            Q(brand__name__icontains=q) |
            Q(category__name__icontains=q)
        )

    # 2. Filter by Category
    category_slug = request.GET.get('category', '').strip()
    selected_category = None
    if category_slug:
        selected_category = get_object_or_404(Category, slug=category_slug)
        products = products.filter(category=selected_category)

    # 3. Filter by Brand
    brand_slug = request.GET.get('brand', '').strip()
    selected_brand = None
    if brand_slug:
        selected_brand = get_object_or_404(Brand, slug=brand_slug)
        products = products.filter(brand=selected_brand)

    # 4. Filter by Price Range (supporting effective selling price)
    products = products.annotate(effective_price=Coalesce('discount_price', 'price'))
    
    min_price = request.GET.get('min_price', '').strip()
    max_price = request.GET.get('max_price', '').strip()
    if min_price:
        try:
            products = products.filter(effective_price__gte=Decimal(min_price))
        except (ValueError, TypeError):
            pass
    if max_price:
        try:
            products = products.filter(effective_price__lte=Decimal(max_price))
        except (ValueError, TypeError):
            pass

    # 5. Filter by Size
    size = request.GET.get('size', '').strip()
    if size:
        products = products.filter(sizes__size=size, sizes__stock__gt=0).distinct()

    # 6. Sorting
    sort = request.GET.get('sort', 'newest').strip()
    if sort == 'price_low':
        products = products.order_by('effective_price')
    elif sort == 'price_high':
        products = products.order_by('-effective_price')
    elif sort == 'popular':
        products = products.annotate(num_reviews=Count('reviews')).order_by('-num_reviews', '-is_best_seller')
    elif sort == 'discount':
        products = products.filter(discount_price__isnull=False).order_by('-effective_price')
    else:  # 'newest' default
        products = products.order_by('-created_at')

    # Available filter options for sidebar
    all_categories = Category.objects.annotate(prod_count=Count('products'))
    all_brands = Brand.objects.annotate(prod_count=Count('products'))
    all_sizes = ProductSize.objects.values_list('size', flat=True).distinct().order_by('size')

    # Price bracket presets requested by user
    price_brackets = [
        {'label': 'Under ₹1,000', 'min': '500', 'max': '1000', 'slug': '500-1000'},
        {'label': '₹1,000 – ₹1,500', 'min': '1000', 'max': '1500', 'slug': '1000-1500'},
        {'label': '₹1,500 – ₹2,000', 'min': '1500', 'max': '2000', 'slug': '1500-2000'},
        {'label': '₹2,000 – ₹3,000', 'min': '2000', 'max': '3000', 'slug': '2000-3000'},
        {'label': '₹3,000 – ₹5,000', 'min': '3000', 'max': '5000', 'slug': '3000-5000'},
        {'label': '₹5,000 – ₹8,000', 'min': '5000', 'max': '8000', 'slug': '5000-8000'},
        {'label': '₹8,000 – ₹10,000', 'min': '8000', 'max': '10000', 'slug': '8000-10000'},
        {'label': '₹10,000 – ₹15,000', 'min': '10000', 'max': '15000', 'slug': '10000-15000'},
        {'label': 'Above ₹15,000', 'min': '15000', 'max': '', 'slug': '15000-plus'},
    ]

    # Pagination
    paginator = Paginator(products, 9)
    page = request.GET.get('page', 1)
    try:
        products_page = paginator.page(page)
    except PageNotAnInteger:
        products_page = paginator.page(1)
    except EmptyPage:
        products_page = paginator.page(paginator.num_pages)

    # Preserve GET params across pagination
    get_params = request.GET.copy()
    if 'page' in get_params:
        del get_params['page']
    query_string = get_params.urlencode()

    context = {
        'products': products_page,
        'total_count': products.count(),
        'all_categories': all_categories,
        'all_brands': all_brands,
        'all_sizes': all_sizes,
        'price_brackets': price_brackets,
        'selected_category': selected_category,
        'selected_brand': selected_brand,
        'selected_size': size,
        'min_price': min_price,
        'max_price': max_price,
        'current_sort': sort,
        'search_query': q,
        'query_string': query_string,
    }
    return render(request, 'shop.html', context)


def product_detail(request, slug):
    """Detailed product view with gallery, size chooser, reviews, and related items."""
    product = get_object_or_404(
        Product.objects.select_related('brand', 'category').prefetch_related('gallery_images', 'sizes', 'reviews__user'),
        slug=slug
    )
    
    # Related products from same category or brand
    related_products = Product.objects.filter(category=product.category).exclude(id=product.id)[:4]
    if related_products.count() < 4:
        extra = Product.objects.exclude(id=product.id).exclude(id__in=[p.id for p in related_products])[:4 - related_products.count()]
        related_products = list(related_products) + list(extra)

    # Review form handling
    review_form = ReviewForm()
    if request.method == 'POST' and request.user.is_authenticated:
        review_form = ReviewForm(request.POST)
        if review_form.is_valid():
            review = review_form.save(commit=False)
            review.user = request.user
            review.product = product
            review.save()
            messages.success(request, "Your verified review has been published. Thank you for your feedback!")
            return redirect('product_detail', slug=product.slug)

    # Check if wishlisted by current user
    is_in_wishlist = False
    if request.user.is_authenticated:
        is_in_wishlist = Wishlist.objects.filter(user=request.user, product=product).exists()

    context = {
        'product': product,
        'related_products': related_products,
        'review_form': review_form,
        'is_in_wishlist': is_in_wishlist,
    }
    return render(request, 'product_detail.html', context)


# ==========================================
# CART & CHECKOUT
# ==========================================

def cart_view(request):
    """Display shopping cart and summary."""
    summary = get_cart_summary(request)
    coupon_form = CouponApplyForm()
    recommended_products = Product.objects.filter(is_best_seller=True)[:3]

    context = {
        **summary,
        'coupon_form': coupon_form,
        'recommended_products': recommended_products,
    }
    return render(request, 'cart.html', context)


@require_POST
def add_to_cart(request, product_id):
    """Add item with selected size to user or session cart."""
    product = get_object_or_404(Product, id=product_id)
    size = request.POST.get('size', '').strip()
    quantity = int(request.POST.get('quantity', 1))

    if not size:
        messages.error(request, "Please select an available sneaker size before adding to your bag.")
        return redirect(request.META.get('HTTP_REFERER', 'shop'))

    # Verify size exists in stock
    product_size = ProductSize.objects.filter(product=product, size=size).first()
    if not product_size or product_size.stock < quantity:
        messages.error(request, f"Sorry, size {size} is out of stock or does not have enough inventory.")
        return redirect(request.META.get('HTTP_REFERER', 'shop'))

    if request.user.is_authenticated:
        cart_item, created = CartItem.objects.get_or_create(
            user=request.user,
            product=product,
            size=size,
            defaults={'quantity': quantity}
        )
        if not created:
            cart_item.quantity += quantity
            cart_item.save()
    else:
        key = get_session_key(request)
        cart_item, created = CartItem.objects.get_or_create(
            session_key=key,
            product=product,
            size=size,
            defaults={'quantity': quantity}
        )
        if not created:
            cart_item.quantity += quantity
            cart_item.save()

    messages.success(request, f"Added {product.name} (Size {size}) to your bag!")

    # Check if "buy_now" was clicked
    if request.POST.get('action') == 'buy_now':
        return redirect('checkout')

    return redirect(request.META.get('HTTP_REFERER', 'cart'))


def update_cart_item(request, item_id):
    """Adjust quantity of item in cart (increase/decrease/set)."""
    cart_items = get_cart_queryset(request)
    item = get_object_or_404(cart_items, id=item_id)
    action = request.GET.get('action') or request.POST.get('action')

    if action == 'increase':
        # Check stock
        product_size = ProductSize.objects.filter(product=item.product, size=item.size).first()
        if product_size and item.quantity + 1 > product_size.stock:
            messages.warning(request, f"Maximum available stock for size {item.size} is {product_size.stock}.")
        else:
            item.quantity += 1
            item.save()
            messages.success(request, f"Updated quantity for {item.product.name}.")
    elif action == 'decrease':
        if item.quantity > 1:
            item.quantity -= 1
            item.save()
            messages.success(request, f"Updated quantity for {item.product.name}.")
        else:
            item.delete()
            messages.info(request, f"Removed {item.product.name} from your bag.")

    return redirect('cart')


def remove_from_cart(request, item_id):
    """Delete a specific cart item."""
    cart_items = get_cart_queryset(request)
    item = get_object_or_404(cart_items, id=item_id)
    name = item.product.name
    item.delete()
    messages.info(request, f"Removed {name} from your bag.")
    return redirect('cart')


@require_POST
def apply_coupon(request):
    """Apply discount voucher code to current cart."""
    form = CouponApplyForm(request.POST)
    if form.is_valid():
        code = form.cleaned_data['code'].strip().upper()
        try:
            coupon = Coupon.objects.get(code__iexact=code, active=True)
            cart_items = get_cart_queryset(request)
            subtotal = sum(i.subtotal for i in cart_items)

            if subtotal < coupon.min_purchase:
                messages.error(request, f"Coupon '{coupon.code}' requires a minimum cart value of ${coupon.min_purchase}.")
            else:
                request.session['coupon_id'] = coupon.id
                messages.success(request, f"Promo code '{coupon.code}' applied successfully!")
        except Coupon.DoesNotExist:
            messages.error(request, f"Invalid or expired promo code '{code}'.")
    return redirect('cart')


def remove_coupon(request):
    """Remove active coupon from session."""
    if 'coupon_id' in request.session:
        del request.session['coupon_id']
        messages.info(request, "Promo code removed.")
    return redirect('cart')


def checkout_view(request):
    """Checkout page with validation, inventory verification, and order processing."""
    cart_summary = get_cart_summary(request)
    cart_items = cart_summary['cart_items']

    if not cart_items.exists():
        messages.warning(request, "Your bag is empty. Please add sneakers before proceeding to checkout.")
        return redirect('shop')

    # Prepopulate initial data if user is logged in
    initial_data = {}
    if request.user.is_authenticated:
        initial_data = {
            'full_name': f"{request.user.first_name} {request.user.last_name}".strip() or request.user.username,
            'email': request.user.email,
        }
        profile = getattr(request.user, 'profile', None)
        if profile:
            initial_data.update({
                'phone': profile.phone,
                'address': profile.address,
                'city': profile.city,
                'state': profile.state,
                'postal_code': profile.postal_code,
                'country': profile.country,
            })

    if request.method == 'POST':
        form = CheckoutForm(request.POST)
        if form.is_valid():
            # Validate inventory before placing order
            for item in cart_items:
                product_size = ProductSize.objects.filter(product=item.product, size=item.size).first()
                if product_size and product_size.stock < item.quantity:
                    messages.error(request, f"Insufficient stock for {item.product.name} (Size: {item.size}). Available: {product_size.stock}")
                    return redirect('cart')

            # Create Order atomically
            with transaction.atomic():
                order = form.save(commit=False)
                if request.user.is_authenticated:
                    order.user = request.user
                
                order.subtotal = cart_summary['subtotal']
                order.discount_amount = cart_summary['discount']
                order.shipping_cost = cart_summary['shipping']
                order.total_amount = cart_summary['grand_total']
                order.coupon = cart_summary['coupon']
                order.status = 'Processing'
                order.payment_status = 'Pending' if order.payment_method == 'Cash on Delivery' else 'Paid'
                order.save()

                # Create OrderItems and reduce inventory
                for item in cart_items:
                    OrderItem.objects.create(
                        order=order,
                        product=item.product,
                        selected_size=item.size,
                        quantity=item.quantity,
                        price=item.product.current_price
                    )
                    # Reduce product size stock and total stock
                    ProductSize.objects.filter(product=item.product, size=item.size).update(
                        stock=models.F('stock') - item.quantity
                    )
                    Product.objects.filter(id=item.product.id).update(
                        stock=models.F('stock') - item.quantity
                    )

                # Clear cart & coupon
                cart_items.delete()
                if 'coupon_id' in request.session:
                    del request.session['coupon_id']

                # Also save shipping info back to user profile if authenticated
                if request.user.is_authenticated:
                    profile, _ = UserProfile.objects.get_or_create(user=request.user)
                    if not profile.phone:
                        profile.phone = order.phone
                    if not profile.address:
                        profile.address = order.address
                        profile.city = order.city
                        profile.state = order.state
                        profile.postal_code = order.postal_code
                        profile.country = order.country
                    profile.save()

            messages.success(request, f"Thank you! Your order {order.order_number} has been placed successfully.")
            return redirect('order_success', order_number=order.order_number)
    else:
        form = CheckoutForm(initial=initial_data)

    context = {
        'form': form,
        **cart_summary,
    }
    return render(request, 'checkout.html', context)


def order_success(request, order_number):
    """Confirmation page with order receipt and tracking info."""
    order = get_object_or_404(Order.objects.prefetch_related('items__product'), order_number=order_number)
    
    # Permission check: if order belongs to a user, only allow that user (or staff) to view it
    if order.user and request.user.is_authenticated and order.user != request.user and not request.user.is_staff:
        messages.error(request, "You are not authorized to view this order.")
        return redirect('home')

    context = {
        'order': order,
    }
    return render(request, 'order_success.html', context)


# ==========================================
# WISHLIST
# ==========================================

@login_required
def wishlist_view(request):
    """Display user's saved wishlist items."""
    wishlist_items = Wishlist.objects.filter(user=request.user).select_related('product', 'product__brand')
    context = {
        'wishlist_items': wishlist_items,
    }
    return render(request, 'wishlist.html', context)


@login_required
def toggle_wishlist(request, product_id):
    """Add or remove product from wishlist."""
    product = get_object_or_404(Product, id=product_id)
    item = Wishlist.objects.filter(user=request.user, product=product).first()

    if item:
        item.delete()
        messages.info(request, f"Removed {product.name} from your wishlist.")
        added = False
    else:
        Wishlist.objects.create(user=request.user, product=product)
        messages.success(request, f"Saved {product.name} to your wishlist!")
        added = True

    # Support AJAX or standard redirect
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        count = Wishlist.objects.filter(user=request.user).count()
        return JsonResponse({'status': 'ok', 'added': added, 'count': count})

    return redirect(request.META.get('HTTP_REFERER', 'wishlist'))


@login_required
def move_wishlist_to_cart(request, product_id):
    """Move product from wishlist to cart using first available size."""
    product = get_object_or_404(Product, id=product_id)
    available_size = product.sizes.filter(stock__gt=0).first()

    if not available_size:
        messages.error(request, f"Sorry, {product.name} is currently sold out in all sizes.")
        return redirect('wishlist')

    cart_item, created = CartItem.objects.get_or_create(
        user=request.user,
        product=product,
        size=available_size.size,
        defaults={'quantity': 1}
    )
    if not created:
        cart_item.quantity += 1
        cart_item.save()

    # Remove from wishlist
    Wishlist.objects.filter(user=request.user, product=product).delete()
    messages.success(request, f"Moved {product.name} (Size {available_size.size}) to your shopping bag!")
    return redirect('cart')


# ==========================================
# AUTHENTICATION & USER PROFILE
# ==========================================

def register_view(request):
    """Handle new user registration."""
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])
            user.save()
            UserProfile.objects.create(user=user)
            
            # Auto login
            login(request, user)
            merge_session_cart_to_user(request, user)
            messages.success(request, f"Welcome to SoleVault, {user.first_name or user.username}! Your account has been created.")
            return redirect('home')
    else:
        form = UserRegistrationForm()

    return render(request, 'register.html', {'form': form})


def login_view(request):
    """Handle user login and cart merge."""
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        form = UserLoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            merge_session_cart_to_user(request, user)
            messages.success(request, f"Welcome back, {user.first_name or user.username}!")
            next_url = request.GET.get('next') or request.POST.get('next') or 'home'
            return redirect(next_url)
        else:
            messages.error(request, "Invalid username or password. Please try again.")
    else:
        form = UserLoginForm()

    return render(request, 'login.html', {'form': form})


def logout_view(request):
    """Log out user and redirect to home."""
    logout(request)
    messages.info(request, "You have been logged out securely. See you again soon!")
    return redirect('home')


@login_required
def profile_view(request):
    """Manage user contact and shipping profile."""
    profile, _ = UserProfile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        form = UserProfileForm(request.POST, instance=profile)
        if form.is_valid():
            # Update User attributes
            request.user.first_name = form.cleaned_data.get('first_name', '')
            request.user.last_name = form.cleaned_data.get('last_name', '')
            request.user.email = form.cleaned_data.get('email', '')
            request.user.save()
            form.save()
            messages.success(request, "Your profile details have been successfully updated.")
            return redirect('profile')
    else:
        initial = {
            'first_name': request.user.first_name,
            'last_name': request.user.last_name,
            'email': request.user.email,
        }
        form = UserProfileForm(instance=profile, initial=initial)

    recent_orders = Order.objects.filter(user=request.user)[:3]

    context = {
        'form': form,
        'profile': profile,
        'recent_orders': recent_orders,
    }
    return render(request, 'profile.html', context)


@login_required
def change_password_view(request):
    """Change user password securely."""
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, "Your password has been changed successfully.")
            return redirect('profile')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = PasswordChangeForm(request.user)

    return render(request, 'change_password.html', {'form': form})


@login_required
def orders_view(request):
    """List all orders for logged-in user."""
    orders = Order.objects.filter(user=request.user).prefetch_related('items__product')
    context = {
        'orders': orders,
    }
    return render(request, 'orders.html', context)


@login_required
def order_detail_view(request, order_number):
    """View details of a specific past order for the logged-in user."""
    order = get_object_or_404(
        Order.objects.prefetch_related('items__product'),
        order_number=order_number,
        user=request.user
    )
    context = {
        'order': order,
    }
    return render(request, 'order_detail.html', context)


# ==========================================
# INFORMATIONAL PAGES
# ==========================================

def about_view(request):
    """About SoleVault brand, heritage, craftsmanship, and ethos."""
    return render(request, 'about.html')


def contact_view(request):
    """Contact page with contact form handling and customer support details."""
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Thank you for reaching out! Our concierge team will respond within 24 hours.")
            return redirect('contact')
    else:
        form = ContactForm()

    return render(request, 'contact.html', {'form': form})


def faq_view(request):
    """Frequently asked questions with interactive categories."""
    return render(request, 'faq.html')


def privacy_view(request):
    """Privacy policy page."""
    return render(request, 'privacy.html')


def terms_view(request):
    """Terms and conditions page."""
    return render(request, 'terms.html')


@require_POST
def newsletter_subscribe(request):
    """Handle newsletter signup via form or AJAX."""
    form = NewsletterForm(request.POST)
    if form.is_valid():
        email = form.cleaned_data['email']
        NewsletterSubscriber.objects.get_or_create(email=email)
        messages.success(request, "Thank you for subscribing! You are now on the VIP priority drop list.")
    else:
        messages.info(request, "You are already subscribed to our private drop list.")

    return redirect(request.META.get('HTTP_REFERER', 'home'))


def custom_404(request, exception=None):
    """Custom luxury 404 page."""
    return render(request, '404.html', status=404)
