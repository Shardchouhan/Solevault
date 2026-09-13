from .models import Category, Brand, CartItem, Wishlist, Coupon

def global_context(request):
    """
    Context processor providing store-wide context variables such as
    categories, brands, cart item counts, and wishlist counts.
    """
    categories = Category.objects.all()
    brands = Brand.objects.all()

    # Calculate cart count
    cart_count = 0
    user = getattr(request, 'user', None)
    session = getattr(request, 'session', None)

    if user and user.is_authenticated:
        cart_count = sum(item.quantity for item in CartItem.objects.filter(user=user))
    elif session and session.session_key:
        cart_count = sum(item.quantity for item in CartItem.objects.filter(session_key=session.session_key))

    # Calculate wishlist count
    wishlist_count = 0
    if user and user.is_authenticated:
        wishlist_count = Wishlist.objects.filter(user=user).count()

    # Get featured promo coupon
    active_coupon = Coupon.objects.filter(active=True).first()

    return {
        'global_categories': categories,
        'global_brands': brands,
        'cart_count': cart_count,
        'wishlist_count': wishlist_count,
        'active_coupon': active_coupon,
    }
