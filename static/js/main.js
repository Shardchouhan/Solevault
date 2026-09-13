/**
 * SoleVault — Premium Sneaker E-Commerce JavaScript
 */

document.addEventListener('DOMContentLoaded', function () {
  // 1. Initialize Bootstrap Tooltips & Toasts
  const toastElList = [].slice.call(document.querySelectorAll('.toast'));
  toastElList.map(function (toastEl) {
    const toast = new bootstrap.Toast(toastEl, { delay: 4000 });
    toast.show();
    return toast;
  });

  // 2. Product Detail Image Gallery Switcher
  const mainImage = document.getElementById('mainProductImage');
  const thumbs = document.querySelectorAll('.gallery-thumb');

  if (mainImage && thumbs.length > 0) {
    thumbs.forEach(thumb => {
      thumb.addEventListener('click', function () {
        thumbs.forEach(t => t.classList.remove('active'));
        this.classList.add('active');
        const newSrc = this.getAttribute('data-img-src');
        if (newSrc) {
          mainImage.style.opacity = '0.4';
          mainImage.style.transform = 'scale(0.96)';
          setTimeout(() => {
            mainImage.src = newSrc;
            mainImage.style.opacity = '1';
            mainImage.style.transform = 'scale(1)';
          }, 150);
        }
      });
    });
  }

  // 3. Size Selection Handler
  const sizeInputs = document.querySelectorAll('input[name="size"]');
  const selectedSizeDisplay = document.getElementById('selectedSizeText');
  const sizeErrorMsg = document.getElementById('sizeErrorAlert');

  if (sizeInputs.length > 0) {
    sizeInputs.forEach(input => {
      input.addEventListener('change', function () {
        if (selectedSizeDisplay) {
          selectedSizeDisplay.textContent = this.value;
        }
        if (sizeErrorMsg) {
          sizeErrorMsg.classList.add('d-none');
        }
      });
    });
  }

  // Size validation on form submit
  const addToCartForm = document.getElementById('addToCartForm');
  if (addToCartForm) {
    addToCartForm.addEventListener('submit', function (e) {
      const checkedSize = document.querySelector('input[name="size"]:checked');
      if (!checkedSize) {
        e.preventDefault();
        if (sizeErrorMsg) {
          sizeErrorMsg.classList.remove('d-none');
          sizeErrorMsg.scrollIntoView({ behavior: 'smooth', block: 'center' });
        } else {
          alert('Please select your sneaker size before adding to bag.');
        }
      }
    });
  }

  // 4. Quantity Increment/Decrement Controls
  const qtyInput = document.getElementById('productQuantity');
  const qtyMinusBtn = document.getElementById('qtyMinus');
  const qtyPlusBtn = document.getElementById('qtyPlus');

  if (qtyInput && qtyMinusBtn && qtyPlusBtn) {
    qtyMinusBtn.addEventListener('click', function () {
      let val = parseInt(qtyInput.value) || 1;
      if (val > 1) {
        qtyInput.value = val - 1;
      }
    });

    qtyPlusBtn.addEventListener('click', function () {
      let val = parseInt(qtyInput.value) || 1;
      const maxVal = parseInt(qtyInput.getAttribute('max')) || 10;
      if (val < maxVal) {
        qtyInput.value = val + 1;
      }
    });
  }

  // 5. AJAX Wishlist Toggle
  const wishlistButtons = document.querySelectorAll('.wishlist-ajax-btn');
  wishlistButtons.forEach(btn => {
    btn.addEventListener('click', function (e) {
      e.preventDefault();
      const productId = this.getAttribute('data-product-id');
      const url = `/wishlist/toggle/${productId}/`;
      const heartIcon = this.querySelector('i');

      fetch(url, {
        method: 'GET',
        headers: {
          'X-Requested-With': 'XMLHttpRequest'
        }
      })
      .then(response => {
        if (response.redirected) {
          window.location.href = response.url;
          return;
        }
        return response.json();
      })
      .then(data => {
        if (data && data.status === 'ok') {
          if (data.added) {
            this.classList.add('active');
            if (heartIcon) {
              heartIcon.classList.remove('bi-heart');
              heartIcon.classList.add('bi-heart-fill');
            }
          } else {
            this.classList.remove('active');
            if (heartIcon) {
              heartIcon.classList.remove('bi-heart-fill');
              heartIcon.classList.add('bi-heart');
            }
          }

          // Update navbar badge if present
          const wishlistBadge = document.getElementById('navbarWishlistCount');
          if (wishlistBadge) {
            wishlistBadge.textContent = data.count;
            wishlistBadge.style.display = data.count > 0 ? 'flex' : 'none';
          }
        }
      })
      .catch(err => {
        console.error('Wishlist toggle error:', err);
      });
    });
  });

  // 6. Quick Search Form Auto-Focus
  const searchModal = document.getElementById('searchModal');
  if (searchModal) {
    searchModal.addEventListener('shown.bs.modal', function () {
      const searchInput = searchModal.querySelector('input[name="q"]');
      if (searchInput) searchInput.focus();
    });
  }
});
