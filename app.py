from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_pymongo import PyMongo
from bson.objectid import ObjectId
import bcrypt
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import TfidfVectorizer

app = Flask(__name__)
app.secret_key = 'ee31ea110a42a8be96e6004c861a1ada31a7930c1aa'  # Change this to a secure random secret key
app.config['MONGO_URI'] = 'mongodb+srv://mmmnnn21212:aHRn3QVtZ2fX3jQj@cluster0.tbo9w.mongodb.net/mydatabase'  # Replace with your MongoDB URI
mongo = PyMongo(app)

# Password verification logic
def verify_password(password):
    if len(password) < 12:
        return False
    if not any(char.islower() for char in password):
        return False
    if not any(char.isupper() for char in password):
        return False
    if not any(char.isdigit() for char in password):
        return False
    if not any(char in "!@#$%^&*()-_+=<>?/" for char in password):
        return False
    return True

# Fetch recommendations (Hybrid Filtering)
def fetch_recommendations(user_id):
    user_data = mongo.db.users.find_one({"_id": ObjectId(user_id)})
    if not user_data:
        return []

    user_purchases = user_data.get('purchased_products', [])
    product_list = list(mongo.db.products.find())
    product_df = pd.DataFrame(product_list)

    recommendations = []

    # If the user hasn't bought anything, don't recommend
    if not user_purchases:
        return recommendations

    # Prepare content features for similarity computation
    if not product_df.empty:
        # Ensure that tags are in a list format
        product_df['tags'] = product_df['tags'].apply(lambda x: x if isinstance(x, list) else [])
        product_df['tags'] = product_df['tags'].apply(lambda x: ','.join(x) if x else '')  # Join tags safely
        product_df['content_features'] = product_df['tags'] + ' ' + product_df['description'].fillna('')

        # Create TF-IDF matrix for content features
        tfidf_vectorizer = TfidfVectorizer()
        tfidf_matrix = tfidf_vectorizer.fit_transform(product_df['content_features'])
        cosine_sim = cosine_similarity(tfidf_matrix)

        # Collaborative Filtering Component
        similar_users = mongo.db.users.find({"purchased_products": {"$in": user_purchases}})
        for user in similar_users:
            for product in user.get('purchased_products', []):
                if product not in user_purchases and product not in recommendations:
                    product_details = mongo.db.products.find_one({"_id": ObjectId(product)})
                    if product_details:
                        recommendations.append(product_details)

        # Content-Based Filtering Component
        user_product_indices = product_df[product_df['_id'].isin(user_purchases)].index.tolist()
        if user_product_indices:
            similar_indices = cosine_sim[user_product_indices].argsort(axis=1)[:, -6:].flatten()
            for idx in similar_indices:
                recommended_product = product_df.iloc[idx]
                if recommended_product['_id'] not in user_purchases and recommended_product['_id'] not in recommendations:
                    recommendations.append(mongo.db.products.find_one({"_id": recommended_product['_id']}))

    return recommendations[:6]


@app.route('/')
def index():
    recommendations = []
    if 'user_id' in session:
        recommendations = fetch_recommendations(session['user_id'])
    return render_template('index.html', recommendations=recommendations)

@app.route('/product_list')
def product_list():
    products = list(mongo.db.products.find())
    recommendations = fetch_recommendations(session['user_id']) if 'user_id' in session else []
    return render_template('product_list.html', products=products, recommendations=recommendations)

@app.route('/product/<product_id>')
def product_detail(product_id):
    product = mongo.db.products.find_one({"_id": ObjectId(product_id)})
    if product is None:
        return "Product not found", 404
    recommendations = fetch_recommendations(session['user_id']) if 'user_id' in session else []
    return render_template('product_detail.html', product=product, recommendations=recommendations)

@app.route('/cart')
def cart():
    cart_items = []
    total_price = 0
    if 'user_id' in session:
        user_cart = mongo.db.users.find_one({"_id": ObjectId(session['user_id'])}).get('cart', [])
        cart_items = list(mongo.db.products.find({"_id": {"$in": [ObjectId(item) for item in user_cart]}}))
        total_price = sum(item['price'] for item in cart_items)
        
    recommendations = fetch_recommendations(session['user_id']) if 'user_id' in session else []
    return render_template('cart.html', cart_items=cart_items, total_price=total_price, recommendations=recommendations)

@app.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    product_id = request.json['product_id']
    if 'user_id' in session:
        mongo.db.users.update_one({"_id": ObjectId(session['user_id'])}, {"$push": {"cart": product_id}})
        cart_count = len(mongo.db.users.find_one({"_id": ObjectId(session['user_id'])})['cart'])
        return jsonify(success=True, cart_count=cart_count)
    return jsonify(success=False)

@app.route('/remove_from_cart', methods=['POST'])
def remove_from_cart():
    product_id = request.json['product_id']
    if 'user_id' in session:
        mongo.db.users.update_one({"_id": ObjectId(session['user_id'])}, {"$pull": {"cart": product_id}})
        return jsonify(success=True)
    return jsonify(success=False)

@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    if request.method == 'POST':
        shipping_address = request.form['shipping_address']
        user_cart = mongo.db.users.find_one({"_id": ObjectId(session['user_id'])}).get('cart', [])

        if user_cart:  # Ensure there are items in the cart
            # Get details of the products in the cart
            cart_items = list(mongo.db.products.find({"_id": {"$in": [ObjectId(item) for item in user_cart]}}))

            # Create an order document
            order = {
                "user_id": session['user_id'],
                "products": cart_items,
                "shipping_address": shipping_address,
                "total_price": sum(item['price'] for item in cart_items),
                "status": "Pending",  # You can change this based on your order status handling
                "order_date": pd.Timestamp.now()  # Record the order date
            }

            # Insert the order into the orders collection
            mongo.db.orders.insert_one(order)

            # Convert cart items to a list of product IDs as strings
            purchased_product_ids = [str(item['_id']) for item in cart_items]

            # Update the user's purchased products
            mongo.db.users.update_one(
                {"_id": ObjectId(session['user_id'])},
                {"$addToSet": {"purchased_products": {"$each": purchased_product_ids}}, "$set": {"cart": []}}
            )

            flash('Order placed successfully!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Your cart is empty!', 'warning')
            return redirect(url_for('cart'))  # Redirect back to the cart if empty

    cart_items = []
    total_price = 0
    if 'user_id' in session:
        user_cart = mongo.db.users.find_one({"_id": ObjectId(session['user_id'])}).get('cart', [])
        cart_items = list(mongo.db.products.find({"_id": {"$in": [ObjectId(item) for item in user_cart]}}))
        total_price = sum(item['price'] for item in cart_items)

    recommendations = fetch_recommendations(session['user_id']) if 'user_id' in session else []
    return render_template('checkout.html', cart_items=cart_items, total_price=total_price, recommendations=recommendations)



@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        message = request.form['message']
        flash('Message sent successfully!', 'success')
        return redirect(url_for('index'))
    return render_template('contact.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']

        if not verify_password(password):
            return 'Password does not meet the complexity requirements'

        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

        mongo.db.users.insert_one({
            "name": name,
            "email": email,
            "password": hashed_password,
            "cart": [],
            "purchased_products": []
        })

        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        user = mongo.db.users.find_one({"email": email})
        if user and bcrypt.checkpw(password.encode('utf-8'), user['password'].encode('utf-8')):
            session['user_id'] = str(user['_id'])
            return redirect(url_for('index'))
        else:
            return 'Login failed. Check your credentials.'

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('You have been logged out', 'success')
    return redirect(url_for('index'))

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = mongo.db.users.find_one({'_id': ObjectId(session['user_id'])})
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form.get('password')

        update_data = {'name': name, 'email': email}
        if password:
            hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
            update_data['password'] = hashed_password.decode('utf-8')

        mongo.db.users.update_one({'_id': ObjectId(session['user_id'])}, {'$set': update_data})
        return redirect(url_for('profile'))

    return render_template('profile.html', user=user)

@app.route('/add_product', methods=['GET', 'POST'])
def add_product():
    if request.method == 'POST':
        product_name = request.form['product_name']
        price = request.form['price']
        image_url = request.form['image_url']
        tags = request.form['tags'].split(',')

        mongo.db.products.insert_one({
            "product_name": product_name,
            "price": float(price),
            "image_url": image_url,
            "tags": tags,
            "description": request.form['description']  # Add a description field
        })
        flash('Product added successfully!', 'success')
        return redirect(url_for('product_list'))

    return render_template('add_product.html')

if __name__ == '__main__':
    app.run(debug=True)
