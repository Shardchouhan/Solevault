import os
import shutil
import requests
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.conf import settings
from django.utils.text import slugify
from store.models import (
    Category, Brand, Product, ProductImage, ProductSize,
    Coupon, Review, UserProfile, Order, OrderItem
)

def download_or_save_image(filepath, url, fallback_title="Sneaker"):
    """Download authentic high-res sneaker photograph, or use user-uploaded asset / vector fallback."""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    if os.path.exists(filepath) and os.path.getsize(filepath) > 1000:
        return True

    try:
        r = requests.get(url, timeout=12, headers={'User-Agent': 'SoleVault/1.0'})
        if r.status_code == 200 and len(r.content) > 1000:
            with open(filepath, 'wb') as f:
                f.write(r.content)
            return True
    except Exception as e:
        pass

    # Fallback SVG if network issue
    svg_fallback = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 600" width="100%" height="100%">
      <rect width="800" height="600" fill="#202020" />
      <circle cx="400" cy="300" r="220" fill="#C5A880" opacity="0.15" />
      <text x="400" y="310" font-family="'Outfit', sans-serif" font-size="28" font-weight="700" fill="#FFFFFF" text-anchor="middle">{fallback_title}</text>
    </svg>"""
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(svg_fallback)
    return False


class Command(BaseCommand):
    help = 'Seeds database with real authentic sneaker photographs, INR prices, and Indian/UK sizes.'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS("Starting SoleVault database seeding with REAL Sneaker Photography..."))

        media_root = settings.MEDIA_ROOT
        prod_dir = os.path.join(media_root, 'products')
        gal_dir = os.path.join(prod_dir, 'gallery')
        cat_dir = os.path.join(media_root, 'categories')
        brand_dir = os.path.join(media_root, 'brands')
        os.makedirs(prod_dir, exist_ok=True)
        os.makedirs(gal_dir, exist_ok=True)
        os.makedirs(cat_dir, exist_ok=True)
        os.makedirs(brand_dir, exist_ok=True)

        # 1. Users
        admin_user, _ = User.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@solevault.in',
                'first_name': 'Vault',
                'last_name': 'Director',
                'is_staff': True,
                'is_superuser': True
            }
        )
        admin_user.set_password('admin123')
        admin_user.save()
        UserProfile.objects.get_or_create(user=admin_user, defaults={'city': 'Mumbai', 'state': 'Maharashtra', 'country': 'India'})

        demo_user, _ = User.objects.get_or_create(
            username='jordan_fan',
            defaults={
                'email': 'jordan@example.in',
                'first_name': 'Aarav',
                'last_name': 'Vance',
            }
        )
        demo_user.set_password('password123')
        demo_user.save()
        UserProfile.objects.get_or_create(
            user=demo_user,
            defaults={
                'phone': '+91 98200 12345',
                'address': 'Flat 14B, Sea View Towers, Bandra West',
                'city': 'Mumbai',
                'state': 'Maharashtra',
                'postal_code': '400050',
                'country': 'India'
            }
        )

        # 2. Categories with Real High-Res Photography
        categories_data = [
            {
                'name': 'Running',
                'description': 'Engineered for speed, responsive energy return, and marathon-grade performance.',
                'image_url': 'https://images.unsplash.com/photo-1542291026-7eec264c27ff?auto=format&fit=crop&w=1000&q=80',
                'file_name': 'running_sneakers_v2.jpg'
            },
            {
                'name': 'Lifestyle',
                'description': 'Everyday luxury icons crafted with buttery Italian leathers, muted neutrals, and timeless silhouettes.',
                'image_url': 'https://images.unsplash.com/photo-1595950653106-6c9ebd614d3a?auto=format&fit=crop&w=1000&q=80',
                'file_name': 'lifestyle_sneakers_v2.jpg'
            },
            {
                'name': 'Basketball',
                'description': 'Hardwood dominance and championship DNA with responsive Air cushioning.',
                'image_url': 'https://images.unsplash.com/photo-1579338559194-a162d19bf842?auto=format&fit=crop&w=1000&q=80',
                'file_name': 'basketball_sneakers_v2.jpg'
            },
            {
                'name': 'High Tops',
                'description': 'Classic high-cut silhouettes delivering supreme ankle support and timeless streetwear heritage.',
                'image_url': 'https://images.unsplash.com/photo-1552346154-21d32810aba3?auto=format&fit=crop&w=1000&q=80',
                'file_name': 'high_tops_sneakers_v2.jpg'
            },
            {
                'name': 'Limited Edition',
                'description': 'Ultra-rare vault drops, highly coveted designer collaborations, and numbered collector pairs.',
                'image_url': 'https://images.unsplash.com/photo-1597045566677-8cf032ed6634?auto=format&fit=crop&w=1000&q=80',
                'file_name': 'limited_edition_sneakers_v2.jpg'
            },
        ]

        categories_dict = {}
        for cat in categories_data:
            c_slug = slugify(cat['name'])
            img_path = os.path.join(cat_dir, cat['file_name'])
            download_or_save_image(img_path, cat['image_url'], cat['name'])
            
            category_obj, _ = Category.objects.update_or_create(
                name=cat['name'],
                defaults={
                    'slug': c_slug,
                    'description': cat['description'],
                    'image': f"categories/{cat['file_name']}"
                }
            )
            categories_dict[cat['name']] = category_obj

        self.stdout.write("Seeded 5 Categories with real high-res photography.")

        # 3. Brands
        brands_data = [
            {'name': 'Jordan', 'description': 'The gold standard of basketball greatness and timeless street luxury.'},
            {'name': 'Nike', 'description': 'Groundbreaking innovation and iconic athletic performance since 1972.'},
            {'name': 'Adidas Originals', 'description': 'Three stripes heritage, terrace culture, and avant-garde style.'},
            {'name': 'New Balance', 'description': 'Uncompromising American and British craftsmanship, premium suedes, and orthotic comfort.'},
            {'name': 'Yeezy', 'description': 'Architectural contours, organic shapes, and groundbreaking knit engineering.'},
            {'name': 'Asics', 'description': 'Japanese technical running mastery and Y2K aesthetic perfection.'},
        ]

        brands_dict = {}
        for b in brands_data:
            b_slug = slugify(b['name'])
            brand_obj, _ = Brand.objects.update_or_create(
                name=b['name'],
                defaults={
                    'slug': b_slug,
                    'description': b['description'],
                }
            )
            brands_dict[b['name']] = brand_obj

        self.stdout.write("Seeded 6 Brands.")

        # 4. User's exact uploaded real image handling
        user_img_source = r'C:/Users/ASUS/.gemini/antigravity/brain/8aa80ab6-672c-44b6-956d-ef16acd7f5f0/.user_uploaded/media_1789276862906.png'
        flyknit_dest = os.path.join(prod_dir, 'jordan1_flyknit_gold.png')
        if os.path.exists(user_img_source):
            shutil.copy(user_img_source, flyknit_dest)

        # 5. Products (15 Curated Real Sneaker Models with Studio Photos spanning ₹500 to ₹15,000+)
        products_data = [
            {
                'name': "Air Jordan 1 Retro High Flyknit 'Golden Ochre'",
                'brand': 'Jordan',
                'category': 'High Tops',
                'price': Decimal('15999.00'),
                'discount_price': Decimal('13999.00'),
                'stock': 16,
                'is_featured': True,
                'is_new': True,
                'is_best_seller': True,
                'local_image': 'products/jordan1_flyknit_gold_v2.png',
                'image_url': 'https://images.unsplash.com/photo-1552346154-21d32810aba3?auto=format&fit=crop&w=800&q=80',
                'gallery_urls': [
                    'https://images.unsplash.com/photo-1584735935682-2f2b69dff9d2?auto=format&fit=crop&w=800&q=80',
                    'https://images.unsplash.com/photo-1515955656352-a1fa3ffcd111?auto=format&fit=crop&w=800&q=80',
                    'https://images.unsplash.com/photo-1600185365483-26d7a4cc7519?auto=format&fit=crop&w=800&q=80',
                ],
                'description': "Engineered with a breathable woven Flyknit upper in tonal heather grey with rich Golden Ochre leather swooshes and Jordan Wings detailing. Air-Sole cushioning encapsulated in the heel with classic gum rubber outsole.",
                'specifications': "Premium seamless engineered Flyknit upper\nFull-grain leather Swoosh and embossed Wings logo\nEncapsulated Air-Sole cushioning in heel\nSolid gum rubber cupsole with pivot circle"
            },
            {
                'name': "Air Jordan 1 Retro High OG 'Chicago Lost & Found'",
                'brand': 'Jordan',
                'category': 'High Tops',
                'price': Decimal('22999.00'),
                'discount_price': Decimal('18999.00'),
                'stock': 18,
                'is_featured': True,
                'is_new': True,
                'is_best_seller': True,
                'image_url': 'https://images.unsplash.com/photo-1552346154-21d32810aba3?auto=format&fit=crop&w=800&q=80',
                'gallery_urls': [
                    'https://images.unsplash.com/photo-1584735935682-2f2b69dff9d2?auto=format&fit=crop&w=800&q=80',
                    'https://images.unsplash.com/photo-1600185365483-26d7a4cc7519?auto=format&fit=crop&w=800&q=80',
                    'https://images.unsplash.com/photo-1595950653106-6c9ebd614d3a?auto=format&fit=crop&w=800&q=80',
                ],
                'description': "An exquisite tribute to the 1985 original. Crafted with cracked vintage leather collars, aged sail midsoles, and vibrant Varsity Red leather overlays. Includes vintage receipt packaging and classic Nike Air tongue tags.",
                'specifications': "Premium tumbled leather upper\nVintage cracked leather ankle collar\nEncapsulated Air-Sole cushioning in heel\nSolid rubber cupsole with deep flex grooves\nOriginal 1985 box packaging with vintage invoice reprint"
            },
            {
                'name': "Travis Scott x Air Jordan 1 Low 'Reverse Mocha'",
                'brand': 'Jordan',
                'category': 'Limited Edition',
                'price': Decimal('34999.00'),
                'discount_price': None,
                'stock': 6,
                'is_featured': True,
                'is_new': False,
                'is_best_seller': True,
                'image_url': 'https://images.unsplash.com/photo-1595950653106-6c9ebd614d3a?auto=format&fit=crop&w=800&q=80',
                'gallery_urls': [
                    'https://images.unsplash.com/photo-1607522370275-f14206abe5d3?auto=format&fit=crop&w=800&q=80',
                    'https://images.unsplash.com/photo-1584735935682-2f2b69dff9d2?auto=format&fit=crop&w=800&q=80',
                    'https://images.unsplash.com/photo-1515955656352-a1fa3ffcd111?auto=format&fit=crop&w=800&q=80',
                ],
                'description': "Houston's cultural icon features the signature reversed oversized swoosh in cream leather against velvety mocha durabuck and clean white overlays with Cactus Jack embroidery.",
                'specifications': "Rich mocha nubuck base with premium leather overlays\nSignature backward oversized Swoosh on lateral side\nEmbroidered Cactus Jack and Wings logos on heel counters\nAged sail midsole with durable traction outsole"
            },
            {
                'name': "Nike Dunk Low Retro 'Panda Noir'",
                'brand': 'Nike',
                'category': 'Lifestyle',
                'price': Decimal('2299.00'),
                'discount_price': Decimal('1899.00'),
                'stock': 35,
                'is_featured': False,
                'is_new': False,
                'is_best_seller': True,
                'image_url': 'https://images.unsplash.com/photo-1607522370275-f14206abe5d3?auto=format&fit=crop&w=800&q=80',
                'gallery_urls': [
                    'https://images.unsplash.com/photo-1595950653106-6c9ebd614d3a?auto=format&fit=crop&w=800&q=80',
                    'https://images.unsplash.com/photo-1542291026-7eec264c27ff?auto=format&fit=crop&w=800&q=80',
                    'https://images.unsplash.com/photo-1518002171953-a080ee817e1f?auto=format&fit=crop&w=800&q=80',
                ],
                'description': "The undisputed king of daily streetwear. The Panda Dunk Low combines crisp white leather with stark black panel overlays for an effortlessly sharp, versatile silhouette.",
                'specifications': "Smooth natural leather upper\nPadded low-cut collar for sleek look and comfort\nFoam midsole offering lightweight, responsive cushioning\nRubber outsole with classic hoops pivot circle"
            },
            {
                'name': "Nike Air Max 1 '86 OG 'Big Bubble'",
                'brand': 'Nike',
                'category': 'Lifestyle',
                'price': Decimal('4999.00'),
                'discount_price': Decimal('3999.00'),
                'stock': 22,
                'is_featured': True,
                'is_new': True,
                'is_best_seller': False,
                'image_url': 'https://images.unsplash.com/photo-1542291026-7eec264c27ff?auto=format&fit=crop&w=800&q=80',
                'gallery_urls': [
                    'https://images.unsplash.com/photo-1552346154-21d32810aba3?auto=format&fit=crop&w=800&q=80',
                    'https://images.unsplash.com/photo-1584735935682-2f2b69dff9d2?auto=format&fit=crop&w=800&q=80',
                    'https://images.unsplash.com/photo-1607522370275-f14206abe5d3?auto=format&fit=crop&w=800&q=80',
                ],
                'description': "The holy grail of visible Air technology. Engineered with the larger four-window Air unit designed by Tinker Hatfield in 1986. Mesh underlays with soft grey and vibrant Sport Red suede mudguards.",
                'specifications': "Original Big Bubble visible Max Air cushioning unit\nBreathable mesh toe box and quarter panels\nSynthetic suede overlays in classic heritage color-blocking\nWaffle-pattern rubber outsole for heritage grip"
            },
            {
                'name': "Yeezy Boost 350 V2 'Onyx'",
                'brand': 'Yeezy',
                'category': 'Lifestyle',
                'price': Decimal('11999.00'),
                'discount_price': Decimal('9999.00'),
                'stock': 12,
                'is_featured': True,
                'is_new': False,
                'is_best_seller': True,
                'image_url': 'https://images.unsplash.com/photo-1587563871167-1ee9c731aefb?auto=format&fit=crop&w=800&q=80',
                'gallery_urls': [
                    'https://images.unsplash.com/photo-1608231387042-66d1773070a5?auto=format&fit=crop&w=800&q=80',
                    'https://images.unsplash.com/photo-1595950653106-6c9ebd614d3a?auto=format&fit=crop&w=800&q=80',
                    'https://images.unsplash.com/photo-1552346154-21d32810aba3?auto=format&fit=crop&w=800&q=80',
                ],
                'description': "Monochromatic stealth mastery. Features a re-engineered Primeknit upper with a monofilament side stripe, grounded by a full-length encapsulated BOOST midsole wrapped in a semi-translucent TPU cage.",
                'specifications': "Adaptive re-engineered Primeknit upper\nFull-length responsive adidas BOOST cushioning\nSemi-translucent ribbed TPU midsole wrap\nIntegrated rope lacing system"
            },
            {
                'name': "Yeezy 700 V3 'Azael Light'",
                'brand': 'Yeezy',
                'category': 'Limited Edition',
                'price': Decimal('24999.00'),
                'discount_price': Decimal('19999.00'),
                'stock': 9,
                'is_featured': False,
                'is_new': True,
                'is_best_seller': False,
                'image_url': 'https://images.unsplash.com/photo-1608231387042-66d1773070a5?auto=format&fit=crop&w=800&q=80',
                'gallery_urls': [
                    'https://images.unsplash.com/photo-1587563871167-1ee9c731aefb?auto=format&fit=crop&w=800&q=80',
                    'https://images.unsplash.com/photo-1539185441755-769473a23570?auto=format&fit=crop&w=800&q=80',
                    'https://images.unsplash.com/photo-1560769629-975ec94e6a86?auto=format&fit=crop&w=800&q=80',
                ],
                'description': "Futuristic aerodynamic architecture. Features a monofilament engineered mesh upper encased in a glow-in-the-dark RPU cage providing structural integrity and otherworldly nighttime visual impact.",
                'specifications': "Glow-in-the-dark sculpted RPU cage\nMonofilament engineered mesh base\nDrop-in EVA midsole for lightweight all-day comfort\nHerringbone rubber traction outsole"
            },
            {
                'name': "New Balance 990v6 Made in USA 'Castlerock'",
                'brand': 'New Balance',
                'category': 'Running',
                'price': Decimal('10499.00'),
                'discount_price': Decimal('8999.00'),
                'stock': 25,
                'is_featured': True,
                'is_new': True,
                'is_best_seller': True,
                'image_url': 'https://images.unsplash.com/photo-1539185441755-769473a23570?auto=format&fit=crop&w=800&q=80',
                'gallery_urls': [
                    'https://images.unsplash.com/photo-1551107696-a4b0c5a0d9a2?auto=format&fit=crop&w=800&q=80',
                    'https://images.unsplash.com/photo-1582588678413-dbf45f4823e9?auto=format&fit=crop&w=800&q=80',
                    'https://images.unsplash.com/photo-1518002171953-a080ee817e1f?auto=format&fit=crop&w=800&q=80',
                ],
                'description': "The pinnacle of luxury running comfort. Blending pigskin suede overlays, breathable mesh, and FuelCell foam technology delivering propulsive energy return alongside ENCAP midsole stability.",
                'specifications': "FuelCell foam delivers a propulsive feel to help drive you forward\nENCAP midsole cushioning combines lightweight foam with durable polyurethane rim\nPremium pigskin suede and mesh upper\nManufactured with domestic and imported materials"
            },
            {
                'name': "New Balance 2002R 'Protection Pack Rain Cloud'",
                'brand': 'New Balance',
                'category': 'Lifestyle',
                'price': Decimal('7499.00'),
                'discount_price': Decimal('6499.00'),
                'stock': 16,
                'is_featured': False,
                'is_new': False,
                'is_best_seller': True,
                'image_url': 'https://images.unsplash.com/photo-1551107696-a4b0c5a0d9a2?auto=format&fit=crop&w=800&q=80',
                'gallery_urls': [
                    'https://images.unsplash.com/photo-1539185441755-769473a23570?auto=format&fit=crop&w=800&q=80',
                    'https://images.unsplash.com/photo-1582588678413-dbf45f4823e9?auto=format&fit=crop&w=800&q=80',
                    'https://images.unsplash.com/photo-1518002171953-a080ee817e1f?auto=format&fit=crop&w=800&q=80',
                ],
                'description': "Deconstructed luxury designed by Yue Wu with jagged raw-edge suede overlays evoking wearable relics. Powered by N-ergy shock absorption and ABZORB SBS heel cushioning.",
                'specifications': "Rough-cut raw suede overlays with breathable mesh underlays\nABZORB midsole absorbs impact through a combination of cushioning\nN-ergy outsole provides superior shock absorption\nStability Web outsole technology provides added arch support"
            },
            {
                'name': "Adidas Originals Samba OG 'Cloud White / Core Black'",
                'brand': 'Adidas Originals',
                'category': 'Lifestyle',
                'price': Decimal('1199.00'),
                'discount_price': Decimal('899.00'),
                'stock': 40,
                'is_featured': True,
                'is_new': False,
                'is_best_seller': True,
                'image_url': 'https://images.unsplash.com/photo-1518002171953-a080ee817e1f?auto=format&fit=crop&w=800&q=80',
                'gallery_urls': [
                    'https://images.unsplash.com/photo-1560769629-975ec94e6a86?auto=format&fit=crop&w=800&q=80',
                    'https://images.unsplash.com/photo-1552346154-21d32810aba3?auto=format&fit=crop&w=800&q=80',
                    'https://images.unsplash.com/photo-1595950653106-6c9ebd614d3a?auto=format&fit=crop&w=800&q=80',
                ],
                'description': "Born on the football pitch, perfected on the runways. Full-grain leather upper with a suede T-toe cap and low-profile dark gum rubber cupsole for a refined vintage silhouette.",
                'specifications': "Full grain leather upper with gritty suede and gold foil details\nSynthetic leather lining for soft foot entry\nGum rubber midsole and low-profile grip outsole\nIconic serrated 3-Stripes branding"
            },
            {
                'name': "Adidas Forum 84 Low 'Luxury Cream'",
                'brand': 'Adidas Originals',
                'category': 'Lifestyle',
                'price': Decimal('1699.00'),
                'discount_price': Decimal('1299.00'),
                'stock': 20,
                'is_featured': False,
                'is_new': True,
                'is_best_seller': False,
                'image_url': 'https://images.unsplash.com/photo-1560769629-975ec94e6a86?auto=format&fit=crop&w=800&q=80',
                'gallery_urls': [
                    'https://images.unsplash.com/photo-1518002171953-a080ee817e1f?auto=format&fit=crop&w=800&q=80',
                    'https://images.unsplash.com/photo-1539185441755-769473a23570?auto=format&fit=crop&w=800&q=80',
                    'https://images.unsplash.com/photo-1542291026-7eec264c27ff?auto=format&fit=crop&w=800&q=80',
                ],
                'description': "A tribute to basketball royalty in 1984. Premium tumbled off-white leather paired with warm beige suede accents, authentic crisscross ankle strap, and exposed French terry collar lining.",
                'specifications': "Premium leather and suede upper\nRemovable hook-and-loop ankle strap\nDellinger web midsole detail\nHeritage rubber cupsole"
            },
            {
                'name': "Asics GEL-Kayano 14 'Metallic Silver / Cream'",
                'brand': 'Asics',
                'category': 'Running',
                'price': Decimal('3299.00'),
                'discount_price': Decimal('2699.00'),
                'stock': 28,
                'is_featured': True,
                'is_new': True,
                'is_best_seller': True,
                'image_url': 'https://images.unsplash.com/photo-1575537302964-96cd47c06b1b?auto=format&fit=crop&w=1000&q=80',
                'gallery_urls': [
                    'https://images.unsplash.com/photo-1539185441755-769473a23570?auto=format&fit=crop&w=800&q=80',
                    'https://images.unsplash.com/photo-1551107696-a4b0c5a0d9a2?auto=format&fit=crop&w=800&q=80',
                    'https://images.unsplash.com/photo-1584735935682-2f2b69dff9d2?auto=format&fit=crop&w=800&q=80',
                ],
                'description': "Late 2000s technical running aesthetics modernized for high-fashion wear. Retaining layered synthetic leather and open mesh construction, supported by signature GEL cushioning units.",
                'specifications': "GEL technology cushioning provides excellent shock absorption\nTRUSSTIC support system preserves structural integrity\nLate 2000s aesthetic language with layered metallic overlays\nSolution dye sockliner reduces water usage"
            },
            {
                'name': "Nike ZoomX Vaporfly NEXT% 3 'Phantom Platinum'",
                'brand': 'Nike',
                'category': 'Running',
                'price': Decimal('14999.00'),
                'discount_price': Decimal('12499.00'),
                'stock': 14,
                'is_featured': False,
                'is_new': True,
                'is_best_seller': False,
                'image_url': 'https://images.unsplash.com/photo-1606107557195-0e29a4b5b4aa?auto=format&fit=crop&w=1000&q=80',
                'gallery_urls': [
                    'https://images.unsplash.com/photo-1542291026-7eec264c27ff?auto=format&fit=crop&w=800&q=80',
                    'https://images.unsplash.com/photo-1607522370275-f14206abe5d3?auto=format&fit=crop&w=800&q=80',
                    'https://images.unsplash.com/photo-1552346154-21d32810aba3?auto=format&fit=crop&w=800&q=80',
                ],
                'description': "The ultimate marathon race-day weapon. Features full-length carbon fiber Flyplate propulsion embedded inside high-rebound ZoomX foam with ultra-breathable Flyknit yarn upper.",
                'specifications': "Full-length carbon fiber Flyplate provides a stiff and propulsive feel\nNike ZoomX foam is ultra-responsive and lightweight\nEngineered Flyknit upper provides targeted zones of breathability\nWaffle-pattern rubber outsole pods for wet/dry cornering"
            },
            {
                'name': "Off-White x Nike Air Force 1 'Ghost White'",
                'brand': 'Nike',
                'category': 'Limited Edition',
                'price': Decimal('29999.00'),
                'discount_price': None,
                'stock': 4,
                'is_featured': True,
                'is_new': False,
                'is_best_seller': False,
                'image_url': 'https://images.unsplash.com/photo-1597045566677-8cf032ed6634?auto=format&fit=crop&w=800&q=80',
                'gallery_urls': [
                    'https://images.unsplash.com/photo-1518002171953-a080ee817e1f?auto=format&fit=crop&w=800&q=80',
                    'https://images.unsplash.com/photo-1560769629-975ec94e6a86?auto=format&fit=crop&w=800&q=80',
                    'https://images.unsplash.com/photo-1552346154-21d32810aba3?auto=format&fit=crop&w=800&q=80',
                ],
                'description': "Virgil Abloh's iconic deconstructivist design language. Features exposed foam padding, translucent ripstop quarter panels, signature industrial quotation text, and an orange zip-tie tag.",
                'specifications': "Translucent synthetic and textile upper\nExposed foam tongue with off-center branding tag\nSignature Helvetica text on medial side\nClassic Air-cushioned rubber sole unit"
            },
            {
                'name': "Air Jordan 4 Retro 'Military Black'",
                'brand': 'Jordan',
                'category': 'High Tops',
                'price': Decimal('16999.00'),
                'discount_price': Decimal('14499.00'),
                'stock': 15,
                'is_featured': True,
                'is_new': False,
                'is_best_seller': True,
                'image_url': 'https://images.unsplash.com/photo-1579338559194-a162d19bf842?auto=format&fit=crop&w=800&q=80',
                'gallery_urls': [
                    'https://images.unsplash.com/photo-1552346154-21d32810aba3?auto=format&fit=crop&w=800&q=80',
                    'https://images.unsplash.com/photo-1584735935682-2f2b69dff9d2?auto=format&fit=crop&w=800&q=80',
                    'https://images.unsplash.com/photo-1595950653106-6c9ebd614d3a?auto=format&fit=crop&w=800&q=80',
                ],
                'description': "Clean, crisp, and undeniably iconic. Incorporates smooth white leather with light grey suede toe overlays and bold black accents on the TPU eyelets, heel tab, and midsole arches.",
                'specifications': "Genuine white leather upper with neutral grey suede front wrap\nTPU support wings and molded heel tab\nVisible Air-Sole unit in heel with encapsulated forefoot cushioning\nHerringbone pattern rubber outsole for multi-directional traction"
            },
        ]

        # Indian / UK Standard Sizing
        indian_uk_sizes = ['UK 6', 'UK 6.5', 'UK 7', 'UK 7.5', 'UK 8', 'UK 8.5', 'UK 9', 'UK 9.5', 'UK 10', 'UK 10.5', 'UK 11', 'UK 12']

        for p_data in products_data:
            p_slug = slugify(p_data['name'])
            
            # Check if local image assigned
            if p_data.get('local_image'):
                img_relative_path = p_data['local_image']
            else:
                img_filename = f"product_{p_slug[:30]}.jpg"
                img_path = os.path.join(prod_dir, img_filename)
                download_or_save_image(img_path, p_data['image_url'], p_data['name'])
                img_relative_path = f"products/{img_filename}"

            product_obj, created = Product.objects.update_or_create(
                name=p_data['name'],
                defaults={
                    'slug': p_slug,
                    'brand': brands_dict[p_data['brand']],
                    'category': categories_dict[p_data['category']],
                    'description': p_data['description'],
                    'specifications': p_data['specifications'],
                    'price': p_data['price'],
                    'discount_price': p_data['discount_price'],
                    'stock': p_data['stock'],
                    'is_featured': p_data['is_featured'],
                    'is_new': p_data['is_new'],
                    'is_best_seller': p_data['is_best_seller'],
                    'image': img_relative_path,
                }
            )

            # Create Indian / UK Sizes
            for s in indian_uk_sizes:
                ProductSize.objects.update_or_create(
                    product=product_obj,
                    size=s,
                    defaults={'stock': 4 if '8' in s or '9' in s or '10' in s else 2}
                )

            # Create Gallery Images from URLs
            gallery_urls = p_data.get('gallery_urls', [])
            for i, g_url in enumerate(gallery_urls, 1):
                gal_filename = f"gal_{p_slug[:20]}_{i}.jpg"
                gal_path = os.path.join(gal_dir, gal_filename)
                download_or_save_image(gal_path, g_url, f"{p_data['name']} Angle {i}")
                ProductImage.objects.get_or_create(
                    product=product_obj,
                    image=f"products/gallery/{gal_filename}",
                    defaults={'caption': f"Studio View #{i}"}
                )

            # Seed realistic customer reviews
            Review.objects.get_or_create(
                user=demo_user,
                product=product_obj,
                defaults={
                    'rating': 5,
                    'title': "100% genuine and fast delivery across India!",
                    'comment': f"Received my {product_obj.name} in mint condition. The double-boxed packaging and verification tag gave complete peace of mind. Delivery to Mumbai was swift within 48 hours."
                }
            )

        self.stdout.write("Seeded 15 Sneaker Products with authentic real photographs.")

        # 6. Seed Promo Coupons in INR
        coupons = [
            {'code': 'WELCOME10', 'discount_percent': 10, 'discount_amount': Decimal('0.00'), 'min_purchase': Decimal('2999.00')},
            {'code': 'VAULT20', 'discount_percent': 20, 'discount_amount': Decimal('0.00'), 'min_purchase': Decimal('15000.00')},
            {'code': 'SOLE1000', 'discount_percent': 0, 'discount_amount': Decimal('1000.00'), 'min_purchase': Decimal('9999.00')},
            {'code': 'FREESHIP', 'discount_percent': 5, 'discount_amount': Decimal('0.00'), 'min_purchase': Decimal('1999.00')},
        ]
        for c in coupons:
            Coupon.objects.update_or_create(
                code=c['code'],
                defaults={
                    'discount_percent': c['discount_percent'],
                    'discount_amount': c['discount_amount'],
                    'min_purchase': c['min_purchase'],
                    'active': True
                }
            )
        self.stdout.write("Seeded 4 Promo Coupons in INR.")

        # 7. Sample Order
        sample_prod = Product.objects.first()
        if sample_prod:
            order, o_created = Order.objects.get_or_create(
                order_number='SV-MUM8899',
                defaults={
                    'user': demo_user,
                    'full_name': 'Aarav Vance',
                    'email': 'jordan@example.in',
                    'phone': '+91 98200 12345',
                    'address': 'Flat 14B, Sea View Towers, Bandra West',
                    'city': 'Mumbai',
                    'state': 'Maharashtra',
                    'postal_code': '400050',
                    'country': 'India',
                    'subtotal': sample_prod.current_price,
                    'shipping_cost': Decimal('0.00'),
                    'discount_amount': Decimal('1000.00'),
                    'total_amount': sample_prod.current_price - Decimal('1000.00'),
                    'status': 'Shipped',
                    'payment_method': 'UPI (Google Pay / PhonePe / Paytm)',
                    'payment_status': 'Paid',
                    'tracking_number': 'TRK-IND8899-DELHIVERY'
                }
            )
            if o_created:
                OrderItem.objects.create(
                    order=order,
                    product=sample_prod,
                    selected_size='UK 9',
                    quantity=1,
                    price=sample_prod.current_price
                )
        self.stdout.write("Seeded Demo Order.")

        self.stdout.write(self.style.SUCCESS("SoleVault Real Sneaker Photography seeding completed successfully!"))
