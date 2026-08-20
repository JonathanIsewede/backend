import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'ecommerce.db')
SCHEMA_PATH = os.path.join(os.path.dirname(__file__), 'schema.sql')

PRODUCTS = [
    (
        "Aura Pro Wireless Headphones",
        "audio",
        249.99,
        299.99,
        4.9,
        342,
        "BESTSELLER",
        "Active noise-canceling wireless headphones with 40-hour battery life, spatial audio, and premium memory foam earcups.",
        "static/images/aura-pro-headphones.svg",
        45
    ),
    (
        "Chronos X Smartwatch",
        "wearables",
        199.99,
        249.99,
        4.8,
        215,
        "NEW",
        "High-definition AMOLED display smartwatch with cardiac health monitoring, GPS tracking, and 7-day battery life.",
        "static/images/chronos-x-smartwatch.svg",
        30
    ),
    (
        "Apex RGB Mechanical Keyboard",
        "accessories",
        149.99,
        179.99,
        4.9,
        188,
        "HOT",
        "Custom hot-swappable tactile mechanical keyboard with per-key RGB backlight, aluminum chassis, and wireless Bluetooth 5.2.",
        "static/images/apex-rgb-keyboard.svg",
        20
    ),
    (
        "Lumen Soundbar Mini",
        "audio",
        119.99,
        149.99,
        4.7,
        96,
        "FEATURED",
        "Compact room-filling Bluetooth soundbar with deep bass subwoofers and optical audio connection.",
        "static/images/lumen-soundbar-mini.svg",
        15
    ),
    (
        "CyberDeck Ergo Wireless Mouse",
        "accessories",
        79.99,
        99.99,
        4.6,
        140,
        "SALE",
        "Ergonomic vertical wireless mouse with high-precision optical sensor and customizable macro buttons.",
        "static/images/cyberdeck-ergo-mouse.svg",
        60
    ),
    (
        "PulseFit Fitness Tracker Band",
        "wearables",
        59.99,
        79.99,
        4.5,
        88,
        "POPULAR",
        "Lightweight waterproof fitness band with sleep monitoring, oxygen tracking, and 14-day battery life.",
        "static/images/pulsefit-fitness-band.svg",
        100
    ),
    (
        "Nova Pulse True Wireless Earbuds",
        "audio",
        129.99,
        159.99,
        4.7,
        268,
        "NEW",
        "Immersive true wireless earbuds with adaptive noise isolation and a wireless charging case.",
        "static/images/nova-pulse-earbuds.svg",
        40
    ),
    (
        "Aurora Studio Monitor Headset",
        "audio",
        179.99,
        219.99,
        4.6,
        74,
        None,
        "Reference-grade studio headphones with an ultra-flat frequency response made for creators.",
        "static/images/aurora-studio-headset.svg",
        25
    ),
    (
        "EchoPod Bluetooth Speaker",
        "audio",
        89.99,
        119.99,
        4.5,
        152,
        "HOT",
        "Portable 360-degree Bluetooth speaker with 24-hour playtime and an IPX7 waterproof rating.",
        "static/images/echopod-speaker.svg",
        80
    ),
    (
        "Vertex 4K Streaming Webcam",
        "accessories",
        99.99,
        129.99,
        4.6,
        203,
        "SALE",
        "Crisp 4K webcam with auto-framing, low-light correction, and dual noise-canceling mics.",
        "static/images/vertex-4k-webcam.svg",
        55
    ),
    (
        "TitanTrek 11-in-1 USB-C Dock",
        "accessories",
        139.99,
        None,
        4.5,
        66,
        "NEW",
        "Thunderbolt-ready USB-C dock with dual 4K output and 100W power delivery.",
        "static/images/titantrek-usb-c-dock.svg",
        35
    ),
    (
        "Chronos Fit Pro Smartwatch",
        "wearables",
        159.99,
        199.99,
        4.7,
        94,
        "FEATURED",
        "Premium sports smartwatch with dual-band GPS and advanced recovery insights.",
        "static/images/chronos-fit-pro.svg",
        28
    )
]

def init_db():
    conn = sqlite3.connect(DB_PATH)
    with open(SCHEMA_PATH, 'r') as f:
        conn.executescript(f.read())
    
    cursor = conn.cursor()
    cursor.executemany('''
        INSERT INTO products (title, category, price, old_price, rating, reviews_count, tag, description, image_url, stock)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', PRODUCTS)
    
    conn.commit()
    conn.close()
    print("Database successfully initialized and seeded!")

if __name__ == '__main__':
    init_db()
