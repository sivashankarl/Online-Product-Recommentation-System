import os
from PIL import Image, ImageDraw, ImageFont

def create_directories():
    """Create necessary directories"""
    directories = ['templates', 'static', 'static/images', 'static/css', 'static/js']
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        print(f"Created directory: {directory}")

def create_custom_placeholder(product_name, filename):
    """Generate an image with the product name as text"""
    img = Image.new('RGB', (300, 200), color='lightgray')
    draw = ImageDraw.Draw(img)

    try:
        font = ImageFont.truetype("arial.ttf", 18)
    except:
        font = ImageFont.load_default()

    text = product_name
    text_width, text_height = draw.textsize(text, font=font)
    x = (300 - text_width) // 2
    y = (200 - text_height) // 2
    draw.text((x, y), text, fill='black', font=font)

    img.save(f'static/images/{filename}')
    print(f"Created image: static/images/{filename}")

def create_all_product_images():
    """Generate placeholder images for all products"""
    products = [
        ("Wireless Bluetooth Headphones", "headphones.jpg"),
        ("Smart Fitness Watch", "fitness_watch.jpg"),
        ("Organic Coffee Beans", "coffee_beans.jpg"),
        ("Yoga Mat Pro", "yoga_mat.jpg"),
        ("LED Desk Lamp", "desk_lamp.jpg"),
        ("Wireless Phone Charger", "phone_charger.jpg"),
        ("Stainless Steel Water Bottle", "water_bottle.jpg"),
        ("Bluetooth Speaker", "speaker.jpg"),
    ]

    for name, file in products:
        create_custom_placeholder(name, file)

if __name__ == "__main__":
    print("Setting up project directories and generating product images...")
    create_directories()
    try:
        create_all_product_images()
    except ImportError:
        print("⚠ Pillow not installed. Run: pip install Pillow")
    print("\n Setup complete!")
    print("1. Move HTML files to the 'templates/' folder")
    print("2. Start your Flask app with: python app.py")
