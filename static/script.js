document.addEventListener("DOMContentLoaded", function() {
    // Add to Cart function
    const addToCart = (productId) => {
        fetch("/add_to_cart", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({ product_id: productId }),
        })
        .then((response) => response.json())
        .then((data) => {
            if (data.success) {
                alert("Product added to cart successfully!");
                document.getElementById("cart-count").innerText = data.cart_count;
            } else {
                alert("Failed to add product to cart. Please try again.");
            }
        })
        .catch((error) => {
            console.error("Error adding to cart:", error);
        });
    };

    // Remove from Cart function
    const removeFromCart = (productId) => {
        fetch("/remove_from_cart", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({ product_id: productId }),
        })
        .then((response) => response.json())
        .then((data) => {
            if (data.success) {
                alert("Product removed from cart.");
                location.reload();  // Refresh the page after removing the item
            } else {
                alert("Failed to remove product from cart. Please try again.");
            }
        })
        .catch((error) => {
            console.error("Error removing from cart:", error);
        });
    };

    // Update Cart Item Quantity
    const updateCartQuantity = (productId, quantity) => {
        fetch(`/update_cart_quantity`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({ product_id: productId, quantity: quantity }),
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert("Cart updated successfully!");
                window.location.reload();
            } else {
                alert("Failed to update cart quantity.");
            }
        })
        .catch((error) => {
            console.error("Error updating cart quantity:", error);
        });
    };

    // Event Listeners for Add to Cart buttons
    document.querySelectorAll('.add-to-cart-btn').forEach(button => {
        button.addEventListener('click', function() {
            const productId = this.getAttribute('data-product-id');
            addToCart(productId);
        });
    });

    // Event Listeners for Remove from Cart buttons
    document.querySelectorAll('.remove-btn').forEach(button => {
        button.addEventListener('click', function() {
            const productId = this.getAttribute('data-product-id');
            removeFromCart(productId);
        });
    });

    // Event Listeners for updating cart item quantities
    document.querySelectorAll('.quantity-input').forEach(input => {
        input.addEventListener('change', function() {
            const productId = this.getAttribute('data-product-id');
            const quantity = this.value;
            updateCartQuantity(productId, quantity);
        });
    });

    // Password strength meter (optional enhancement)
    const passwordField = document.getElementById('password');
    if (passwordField) {
        passwordField.addEventListener('input', (e) => checkPasswordStrength(e.target.value));
    }
});

// Dynamic password strength meter
function checkPasswordStrength(password) {
    const strengthMeter = document.getElementById('password-strength-meter');
    const strengthText = document.getElementById('password-strength-text');
    
    let strength = 0;
    if (password.length >= 12) strength++;
    if (/[A-Z]/.test(password)) strength++;
    if (/[a-z]/.test(password)) strength++;
    if (/\d/.test(password)) strength++;
    if (/[!@#$%^&*(),.?":{}|<>]/.test(password)) strength++;

    switch (strength) {
        case 1:
        case 2:
            strengthMeter.value = 20;
            strengthText.innerText = 'Weak';
            break;
        case 3:
        case 4:
            strengthMeter.value = 50;
            strengthText.innerText = 'Moderate';
            break;
        case 5:
            strengthMeter.value = 100;
            strengthText.innerText = 'Strong';
            break;
        default:
            strengthMeter.value = 0;
            strengthText.innerText = '';
    }
}
