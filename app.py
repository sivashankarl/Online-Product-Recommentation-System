from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, abort
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import pandas as pd
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import TfidfVectorizer
import os
from PIL import Image, ImageDraw, ImageFont
import io
import base64
import random
from datetime import datetime
import uuid
from functools import lru_cache
from concurrent.futures import ThreadPoolExecutor
import plotly.graph_objs as go
import plotly.io as pio
from flask import render_template

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-this-for-production'
app.config['UPLOAD_FOLDER'] = 'static/images'

# Product class
class Product:
    def __init__(self, id, name, price, rating, description, image, category, stock=50):
        self.id = id
        self.name = name
        self.price = price  # Prices will be stored in INR
        self.rating = rating
        self.description = description
        self.image = image
        self.category = category
        self.stock = stock

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'price': self.price,
            'rating': self.rating,
            'description': self.description,
            'image': self.image,
            'category': self.category,
            'stock': self.stock
        }

# Order class
class Order:
    def __init__(self, order_id, user_id, items, total, status, payment_method, timestamp):
        self.order_id = order_id
        self.user_id = user_id
        self.items = items  # List of dicts: {product: Product, quantity: int}
        self.total = total  # Total in INR
        self.status = status  # 'pending', 'paid', 'shipped', 'delivered', 'cancelled'
        self.payment_method = payment_method
        self.timestamp = timestamp

# Create product images directory if it doesn't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Sample product data with image paths (prices in INR)
PRODUCTS = {
    # Original Electronics Products (1-8)
    1: Product(1, "Wireless Bluetooth Headphones", 5999, 4.5,
              "High-quality wireless headphones with noise cancellation", "headphones.jpg", "Electronics"),
    2: Product(2, "Smart Fitness Watch", 14999, 4.2,
              "Track your fitness goals with this advanced smartwatch", "fitness_watch.jpg", "Electronics"),
    6: Product(6, "Wireless Phone Charger", 1999, 4.1,
              "Fast wireless charging pad compatible with all devices", "phone_charger.jpg", "Electronics"),
    8: Product(8, "Bluetooth Speaker", 6699, 4.4,
              "Portable speaker with rich sound and long battery life", "speaker.jpg", "Electronics"),
    
    # Original Food Product (3)
    3: Product(3, "Organic Coffee Beans", 1799, 4.8,
              "Premium organic coffee beans from sustainable farms", "coffee_beans.jpg", "Food"),
    
    # Original Fitness Product (4)
    4: Product(4, "Yoga Mat Pro", 3299, 4.6,
              "Non-slip premium yoga mat for all your fitness needs", "yoga_mat.jpg", "Fitness"),
    
    # Original Home Product (5)
    5: Product(5, "LED Desk Lamp", 2699, 4.3,
              "Adjustable LED desk lamp with multiple brightness levels", "desk_lamp.jpg", "Home"),
    
    # Original Lifestyle Product (7)
    7: Product(7, "Stainless Steel Water Bottle", 1499, 4.7,
              "Insulated water bottle keeps drinks cold for 24 hours", "water_bottle.jpg", "Lifestyle"),
    # Additional Electronics (9-12)
    9: Product(9, "4K Action Camera", 25999, 4.6,
              "Waterproof camera with image stabilization", "action_cam.jpg", "Electronics"),
    10: Product(10, "E-Reader", 9699, 4.5,
               "Glare-free display with weeks of battery life", "ereader.jpg", "Electronics"),
    11: Product(11, "Mechanical Keyboard", 6699, 4.7,
               "RGB backlit keyboard with customizable keys", "keyboard.jpg", "Electronics"),
    12: Product(12, "Smart Home Hub", 7499, 4.3,
               "Control all your smart devices from one place", "smart_hub.jpg", "Electronics"),
    
    # Additional Food (13-16)
    13: Product(13, "Organic Matcha Powder", 1399, 4.7,
               "Ceremonial grade Japanese matcha", "matcha.jpg", "Food"),
    14: Product(14, "Artisan Pasta Set", 1699, 4.5,
               "Handcrafted pasta in 4 varieties", "pasta_set.jpg", "Food"),
    15: Product(15, "Gourmet Popcorn Sampler", 1249, 4.4,
               "6 unique flavors in giftable tin", "popcorn.jpg", "Food"),
    16: Product(16, "Cold Brew Coffee Kit", 2599, 4.6,
               "Everything needed to make perfect cold brew", "cold_brew.jpg", "Food"),
    
    # Additional Fitness (17-20)
    17: Product(17, "Resistance Band Set", 2199, 4.4,
               "5 bands with door anchor and handles", "resistance_bands.jpg", "Fitness"),
    18: Product(18, "Foam Roller", 1849, 4.3,
               "High-density foam for muscle recovery", "foam_roller.jpg", "Fitness"),
    19: Product(19, "Smart Jump Rope", 3699, 4.5,
               "Tracks jumps and calories burned", "jump_rope.jpg", "Fitness"),
    20: Product(20, "Yoga Block Set", 1499, 4.6,
               "2 cork blocks for alignment support", "yoga_blocks.jpg", "Fitness"),
    
    # Additional Home (21-24)
    21: Product(21, "Smart Plug", 1849, 4.4,
               "Control devices remotely with your phone", "smart_plug.jpg", "Home"),
    22: Product(22, "Essential Oil Diffuser", 2999, 4.5,
               "Ultrasonic diffuser with color-changing lights", "diffuser.jpg", "Home"),
    23: Product(23, "French Press", 2199, 4.8,
               "Stainless steel coffee maker (34 oz)", "french_press.jpg", "Home"),
    24: Product(24, "Throw Blanket", 3399, 4.7,
               "Super soft chunky knit blanket", "blanket.jpg", "Home"),
    
    # Additional Lifestyle (25-28)
    25: Product(25, "Leather Journal", 2449, 4.6,
               "Hand-stitched genuine leather notebook", "journal.jpg", "Lifestyle"),
    26: Product(26, "Minimalist Watch", 10999, 4.5,
               "Sleek analog watch with sapphire glass", "watch.jpg", "Lifestyle"),
    27: Product(27, "Aviator Sunglasses", 6699, 4.4,
               "Polarized lenses with UV protection", "sunglasses.jpg", "Lifestyle"),
    28: Product(28, "Weekender Bag", 5999, 4.7,
               "Durable canvas bag with leather accents", "weekender.jpg", "Lifestyle"),
    
    # New Category: Outdoor (29-32)
    29: Product(29, "Camping Hammock", 4499, 4.6,
               "Lightweight hammock with tree straps", "hammock.jpg", "Outdoor"),
    30: Product(30, "Portable Grill", 9699, 4.5,
               "Compact propane grill for tailgating", "portable_grill.jpg", "Outdoor"),
    31: Product(31, "Hydration Backpack", 3699, 4.4,
               "2L water bladder with breathable straps", "hydration_pack.jpg", "Outdoor"),
    32: Product(32, "Telescoping Trekking Poles", 5199, 4.7,
               "Adjustable aluminum poles with cork grips", "trekking_poles.jpg", "Outdoor"),
    
    # New Category: Office (33-36)
    33: Product(33, "Ergonomic Mouse", 2999, 4.5,
               "Vertical design reduces wrist strain", "ergo_mouse.jpg", "Office"),
    34: Product(34, "Desk Organizer", 2199, 4.3,
               "Bamboo organizer with multiple compartments", "desk_organizer.jpg", "Office"),
    35: Product(35, "Noise Cancelling Headphones", 22499, 4.8,
               "Premium over-ear headphones for focus", "noise_cancelling.jpg", "Office"),
    36: Product(36, "Standing Desk Converter", 14999, 4.6,
               "Adjustable riser for sit-stand work", "desk_converter.jpg", "Office")
}

# Generate placeholder images if they don't exist
def generate_placeholder_image(product_name, filename):
    try:
        # Create a blank image with light gray background
        width, height = 800, 600
        image = Image.new('RGB', (width, height), color=(240, 240, 240))
        draw = ImageDraw.Draw(image)
        
        # Use a default font
        try:
            font = ImageFont.truetype("arial.ttf", 40)
        except:
            font = ImageFont.load_default()
        
        text = product_name
        
        # Get text bounding box (new method for Pillow 10+)
        left, top, right, bottom = draw.textbbox((0, 0), text, font=font)
        text_width = right - left
        text_height = bottom - top
        
        # Calculate text position (centered)
        x = (width - text_width) / 2
        y = (height - text_height) / 2
        
        # Draw text
        draw.text((x, y), text, font=font, fill='black')
        
        # Save the image
        img_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        image.save(img_path)
        return True
    except Exception as e:
        print(f"Error generating placeholder image: {e}")
        return False

# Check and generate images
for product in PRODUCTS.values():
    img_path = os.path.join(app.config['UPLOAD_FOLDER'], product.image)
    if not os.path.exists(img_path):
        generate_placeholder_image(product.name, product.image)

# Sample user data with hashed passwords (expanded to 55 users)
USERS = {
    'admin': {
        'password': generate_password_hash('admin123'),
        'email': 'admin@example.com',
        'user_id': 1
    },
    'user1': {
        'password': generate_password_hash('pass123'),
        'email': 'user1@example.com',
        'user_id': 2
    },
    'user2': {
        'password': generate_password_hash('pass123'),
        'email': 'user2@example.com',
        'user_id': 3
    },
}

# Add users up to 55
for i in range(4, 56):
    username = f'user{i}'
    USERS[username] = {
        'password': generate_password_hash(f'pass{i}'),
        'email': f'user{i}@example.com',
        'user_id': i
    }

# Sample user ratings (expanded to 55 users)
USER_RATINGS = {
    1: {1: 5, 2: 4, 3: 3, 4: 5},
    2: {1: 4, 3: 5, 5: 4, 6: 3},
    3: {2: 5, 4: 4, 6: 5, 7: 4},
}

# Generate simulated ratings for users 4-55
for user_id in range(4, 56):
    # Each user rates between 3-6 random products with ratings 3-5
    num_ratings = random.randint(3, 6)
    rated_products = random.sample(list(PRODUCTS.keys()), num_ratings)
    USER_RATINGS[user_id] = {pid: random.randint(3, 5) for pid in rated_products}

# Dictionary to store orders
ORDERS = {}

# Reviews data
REVIEWS = {
    1: [
        {
            'username': 'user1',
            'rating': 5,
            'comment': 'Excellent sound quality!',
            'timestamp': datetime(2023, 5, 15)
        },
        {
            'username': 'user2',
            'rating': 4,
            'comment': 'Very comfortable but battery could last longer.',
            'timestamp': datetime(2023, 4, 20)
        }
    ],
    2: [
        {
            'username': 'user3',
            'rating': 5,
            'comment': 'Best smartwatch I have ever used!',
            'timestamp': datetime(2023, 6, 10)
        }
    ]
}

# Login required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page', 'error')
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

# Initialize cart in session
@app.before_request
def before_request():
    if 'cart' not in session:
        session['cart'] = {}

# Routes
@app.route('/')
def home():
    featured_products = dict(list(PRODUCTS.items())[:6])
    return render_template('home.html', featured_products=featured_products)

@app.route('/product/<int:product_id>')
def product_detail(product_id):
    if product_id not in PRODUCTS:
        flash('Product not found', 'error')
        return redirect(url_for('home'))
    
    product = PRODUCTS[product_id]
    
    # Get related products (same category)
    related_products = {}
    for pid, p in PRODUCTS.items():
        if p.category == product.category and pid != product_id:
            related_products[pid] = p
            if len(related_products) >= 4:
                break
    
    # Get reviews for this product
    product_reviews = REVIEWS.get(product_id, [])
    
    return render_template('product_detail.html', 
                         product=product,
                         related_products=related_products,
                         reviews=product_reviews)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        if username in USERS and check_password_hash(USERS[username]['password'], password):
            session['user_id'] = USERS[username]['user_id']
            session['username'] = username
            flash('Login successful!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('home'))
        else:
            flash('Invalid username or password', 'error')
    
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        
        if username in USERS:
            flash('Username already exists', 'error')
        else:
            new_user_id = max([user['user_id'] for user in USERS.values()]) + 1
            USERS[username] = {
                'password': generate_password_hash(password),
                'email': email,
                'user_id': new_user_id
            }
            flash('Account created successfully! Please login.', 'success')
            return redirect(url_for('login'))
    
    return render_template('signup.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('home'))

# Cart routes
@app.route('/add_to_cart/<int:product_id>', methods=['POST'])
@login_required
def add_to_cart(product_id):
    if product_id not in PRODUCTS:
        flash('Product not found', 'error')
        return redirect(url_for('home'))
    
    quantity = int(request.form.get('quantity', 1))
    
    if str(product_id) in session['cart']:
        session['cart'][str(product_id)] += quantity
    else:
        session['cart'][str(product_id)] = quantity
    
    session.modified = True
    flash(f'{PRODUCTS[product_id].name} added to cart!', 'success')
    return redirect(request.referrer or url_for('home'))

@app.route('/cart')
@login_required
def view_cart():
    cart_items = []
    total = 0
    
    for product_id_str, quantity in session['cart'].items():
        product_id = int(product_id_str)
        if product_id in PRODUCTS:
            product = PRODUCTS[product_id]
            item_total = product.price * quantity
            cart_items.append({
                'product': product,
                'quantity': quantity,
                'total': item_total
            })
            total += item_total
    
    return render_template('cart.html', cart_items=cart_items, total=total)

@app.route('/remove_from_cart/<int:product_id>')
@login_required
def remove_from_cart(product_id):
    if str(product_id) in session['cart']:
        session['cart'].pop(str(product_id))
        session.modified = True
        flash('Item removed from cart', 'success')
    return redirect(url_for('view_cart'))

@app.route('/update_cart/<int:product_id>', methods=['POST'])
@login_required
def update_cart(product_id):
    if str(product_id) in session['cart']:
        quantity = int(request.form.get('quantity', 1))
        if quantity > 0:
            session['cart'][str(product_id)] = quantity
            session.modified = True
            flash('Cart updated successfully', 'success')
        else:
            session['cart'].pop(str(product_id))
            session.modified = True
            flash('Item removed from cart', 'success')
    return redirect(url_for('view_cart'))

@app.route('/checkout', methods=['GET', 'POST'])
@login_required
def checkout():
    if not session['cart']:
        flash('Your cart is empty', 'error')
        return redirect(url_for('view_cart'))
    
    if request.method == 'POST':
        # Process payment
        payment_method = request.form.get('payment_method')
        
        # Create order
        order_id = str(uuid.uuid4())
        items = []
        total = 0
        
        for product_id_str, quantity in session['cart'].items():
            product_id = int(product_id_str)
            if product_id in PRODUCTS:
                product = PRODUCTS[product_id]
                item_total = product.price * quantity
                items.append({
                    'product': product,
                    'quantity': quantity
                })
                total += item_total
        
        # Add tax and shipping
        shipping = 200  # 200 INR
        tax = total * 0.18  # 18% GST
        grand_total = total + shipping + tax
        
        # Create order
        order = Order(
            order_id=order_id,
            user_id=session['user_id'],
            items=items,
            total=grand_total,
            status='paid',
            payment_method=payment_method,
            timestamp=datetime.now()
        )
        
        # Store order
        ORDERS[order_id] = order
        
        # Clear cart
        session['cart'] = {}
        session.modified = True
        
        flash('Order placed successfully! Thank you for your purchase.', 'success')
        return redirect(url_for('order_confirmation', order_id=order_id))
    
    # Calculate totals for GET request
    cart_items = []
    subtotal = 0
    
    for product_id_str, quantity in session['cart'].items():
        product_id = int(product_id_str)
        if product_id in PRODUCTS:
            product = PRODUCTS[product_id]
            item_total = product.price * quantity
            cart_items.append({
                'product': product,
                'quantity': quantity,
                'total': item_total
            })
            subtotal += item_total
    
    shipping = 200  # 200 INR
    tax = subtotal * 0.18  # 18% GST
    total = subtotal + shipping + tax
    
    return render_template('checkout.html', 
                         cart_items=cart_items,
                         subtotal=subtotal,
                         shipping=shipping,
                         tax=tax,
                         total=total)

@app.route('/order-confirmation/<order_id>')
@login_required
def order_confirmation(order_id):
    if order_id not in ORDERS or ORDERS[order_id].user_id != session['user_id']:
        flash('Order not found', 'error')
        return redirect(url_for('home'))
    
    order = ORDERS[order_id]
    return render_template('order_confirmation.html', order=order)

@app.route('/order-history')
@login_required
def order_history():
    # Get all orders for current user
    user_orders = [order for order in ORDERS.values() if order.user_id == session['user_id']]
    user_orders.sort(key=lambda x: x.timestamp, reverse=True)
    
    return render_template('order_history.html', orders=user_orders)

@app.route('/order/<order_id>')
@login_required
def order_detail(order_id):
    if order_id not in ORDERS or ORDERS[order_id].user_id != session['user_id']:
        flash('Order not found', 'error')
        return redirect(url_for('home'))
    
    order = ORDERS[order_id]
    return render_template('order_detail.html', order=order)

@app.route('/submit_review/<int:product_id>', methods=['POST'])
@login_required
def submit_review(product_id):
    if product_id not in PRODUCTS:
        flash('Product not found', 'error')
        return redirect(url_for('home'))
    
    rating = int(request.form.get('rating'))
    comment = request.form.get('comment').strip()
    
    if not comment or rating < 1 or rating > 5:
        flash('Invalid review data', 'error')
        return redirect(url_for('product_detail', product_id=product_id))
    
    # Store the review
    review = {
        'user_id': session['user_id'],
        'username': session['username'],
        'product_id': product_id,
        'rating': rating,
        'comment': comment,
        'timestamp': datetime.now()
    }
    
    # Initialize product reviews if not exists
    if product_id not in REVIEWS:
        REVIEWS[product_id] = []
    
    REVIEWS[product_id].append(review)
    
    flash('Thank you for your review!', 'success')
    return redirect(url_for('product_detail', product_id=product_id))

@app.route('/search')
def search():
    query = request.args.get('query', '').lower()
    if not query:
        return redirect(url_for('home'))
    
    # Simple search in product names and descriptions
    search_results = {}
    for pid, product in PRODUCTS.items():
        if (query in product.name.lower() or 
            query in product.description.lower() or 
            query in product.category.lower()):
            search_results[pid] = product
    
    return render_template('search_results.html', 
                         products=search_results, 
                         query=query)

@app.route('/category/<category_name>')
def category(category_name):
    category_products = {pid: p for pid, p in PRODUCTS.items() 
                        if p.category.lower() == category_name.lower()}
    return render_template('category.html', 
                         category_name=category_name,
                         products=category_products)

# Recommendation routes
@app.route('/recommend', methods=['GET', 'POST'])
def recommend():
    if request.method == 'POST':
        user_id = int(request.form['user_id'])
        
        # Generate both types of recommendations
        content_recs = get_content_based_recommendations(user_id, 3)
        collab_recs = get_collaborative_recommendations(user_id, 3)
        
        # Combine recommendations (prioritize collaborative filtering)
        all_recommendations = {}
        all_recommendations.update(collab_recs)
        
        # Add content-based recommendations if we don't have enough
        for pid, product in content_recs.items():
            if pid not in all_recommendations:
                all_recommendations[pid] = product
                if len(all_recommendations) >= 6:
                    break
        
        return render_template('recommendations.html', 
                             products=all_recommendations, 
                             user_id=user_id)
    
    return render_template('recommend_form.html')

@app.route('/api/recommendations/<int:user_id>')
def api_recommendations(user_id):
    """JSON API endpoint for recommendations"""
    recommendations = get_enhanced_recommendations(user_id)
    return jsonify([p.to_dict() for p in recommendations.values()])

@app.route('/track_click/<int:product_id>')
@login_required
def track_click(product_id):
    """Track product views for better recommendations"""
    if 'viewed_products' not in session:
        session['viewed_products'] = []
    session['viewed_products'].append(product_id)
    session.modified = True
    return jsonify(success=True)

@app.route('/api/recently-viewed')
@login_required
def recently_viewed():
    if 'viewed_products' not in session:
        return jsonify([])
    
    viewed = list(set(session['viewed_products']))[-4:]  # Get last 4 unique viewed
    products = [p.to_dict() for pid, p in PRODUCTS.items() if pid in viewed]
    return jsonify(products)

@app.route('/api/feedback')
@login_required
def handle_feedback():
    product_id = int(request.args.get('pid'))
    action = request.args.get('action')
    
    # Store feedback for future recommendations
    if 'feedback' not in session:
        session['feedback'] = {}
    session['feedback'][product_id] = action
    session.modified = True
    
    return jsonify(success=True)

   
# Recommendation algorithms
def get_content_based_recommendations(user_id, num_recommendations=6):
    """Generate content-based recommendations using product descriptions"""
    if user_id not in USER_RATINGS:
        # For new users, return popular products
        return dict(list(PRODUCTS.items())[:num_recommendations])
    
    user_ratings = USER_RATINGS[user_id]
    
    # Get products the user has rated highly (4 or 5 stars)
    liked_products = [pid for pid, rating in user_ratings.items() if rating >= 4]
    
    if not liked_products:
        return dict(list(PRODUCTS.items())[:num_recommendations])
    
    # Create TF-IDF vectors for product descriptions
    descriptions = [PRODUCTS[pid].description + " " + PRODUCTS[pid].category for pid in PRODUCTS.keys()]
    vectorizer = TfidfVectorizer(stop_words='english')
    tfidf_matrix = vectorizer.fit_transform(descriptions)
    
    # Calculate similarity scores
    cosine_sim = cosine_similarity(tfidf_matrix)
    
    # Get recommendations based on liked products
    recommendations = {}
    product_ids = list(PRODUCTS.keys())
    
    for liked_pid in liked_products:
        liked_idx = product_ids.index(liked_pid)
        sim_scores = list(enumerate(cosine_sim[liked_idx]))
        sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)
        
        for idx, score in sim_scores:
            pid = product_ids[idx]
            if pid not in user_ratings and pid not in recommendations:
                recommendations[pid] = PRODUCTS[pid]
                if len(recommendations) >= num_recommendations:
                    break
        
        if len(recommendations) >= num_recommendations:
            break
    
    # Fill remaining slots with popular products if needed
    if len(recommendations) < num_recommendations:
        for pid in PRODUCTS.keys():
            if pid not in user_ratings and pid not in recommendations:
                recommendations[pid] = PRODUCTS[pid]
                if len(recommendations) >= num_recommendations:
                    break
    
    return recommendations

def get_collaborative_recommendations(user_id, num_recommendations=6):
    """Generate collaborative filtering recommendations"""
    if user_id not in USER_RATINGS:
        return dict(list(PRODUCTS.items())[:num_recommendations])
    
    # Create user-item matrix
    all_products = list(PRODUCTS.keys())
    user_ids = list(USER_RATINGS.keys())
    
    user_item_matrix = []
    for uid in user_ids:
        row = []
        for pid in all_products:
            rating = USER_RATINGS[uid].get(pid, 0)
            row.append(rating)
        user_item_matrix.append(row)
    
    user_item_matrix = np.array(user_item_matrix)
    
    # Calculate user similarity
    user_similarity = cosine_similarity(user_item_matrix)
    user_idx = user_ids.index(user_id)
    
    # Find similar users
    similar_users = []
    for i, similarity in enumerate(user_similarity[user_idx]):
        if i != user_idx and similarity > 0:
            similar_users.append((user_ids[i], similarity))
    
    similar_users.sort(key=lambda x: x[1], reverse=True)
    
    # Get recommendations from similar users
    recommendations = {}
    user_ratings = USER_RATINGS[user_id]
    
    for similar_user_id, similarity in similar_users[:3]:  # Top 3 similar users
        for pid, rating in USER_RATINGS[similar_user_id].items():
            if pid not in user_ratings and rating >= 4 and pid not in recommendations:
                recommendations[pid] = PRODUCTS[pid]
                if len(recommendations) >= num_recommendations:
                    break
        
        if len(recommendations) >= num_recommendations:
            break
    
    # Fill with popular products if needed
    if len(recommendations) < num_recommendations:
        for pid in PRODUCTS.keys():
            if pid not in user_ratings and pid not in recommendations:
                recommendations[pid] = PRODUCTS[pid]
                if len(recommendations) >= num_recommendations:
                    break
    
    return recommendations

def get_view_based_recommendations(user_id, num_recommendations=4):
    """Generate recommendations based on viewed products"""
    if 'viewed_products' not in session or not session['viewed_products']:
        return {}
    
    viewed = list(set(session['viewed_products']))
    recommendations = {}
    
    # For each viewed product, find similar products
    for pid in viewed:
        if pid in PRODUCTS:
            product = PRODUCTS[pid]
            # Simple similarity based on category
            for other_pid, other_product in PRODUCTS.items():
                if (other_pid != pid and 
                    other_product.category == product.category and 
                    other_pid not in recommendations):
                    recommendations[other_pid] = other_product
                    if len(recommendations) >= num_recommendations:
                        break
        if len(recommendations) >= num_recommendations:
            break
    
    return recommendations

def get_enhanced_recommendations(user_id):
    """Combines content-based, collaborative, and view-based recommendations"""
    # Get all three types
    content_recs = get_content_based_recommendations(user_id, 4)
    collab_recs = get_collaborative_recommendations(user_id, 4)
    view_recs = get_view_based_recommendations(user_id, 4)
    
    # Combine with weights
    combined = {}
    for rec in [content_recs, collab_recs, view_recs]:
        for pid, product in rec.items():
            if pid not in combined:
                combined[pid] = {'product': product, 'score': 0}
            combined[pid]['score'] += 1
    
    # Sort by score and return top products
    sorted_recs = sorted(combined.values(), key=lambda x: -x['score'])
    return {r['product'].id: r['product'] for r in sorted_recs[:12]}

# Initialize thread pool for image generation
executor = ThreadPoolExecutor(2)

def async_generate_image(product_name, filename):
    with app.app_context():
        generate_placeholder_image(product_name, filename)

# Update the image generation loop
for product in PRODUCTS.values():
    img_path = os.path.join(app.config['UPLOAD_FOLDER'], product.image)
    if not os.path.exists(img_path):
        executor.submit(async_generate_image, product.name, product.image)

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

if __name__ == '__main__':
    app.run(debug=True)