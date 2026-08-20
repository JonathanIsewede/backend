import os
import json
import sqlite3
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash

app = Flask(
    __name__,
    static_folder='static',
    template_folder='templates'
)
app.secret_key = 'lumen_ecommerce_super_secret_key'

DB_PATH = os.path.join(os.path.dirname(__file__), 'ecommerce.db')

# Demo credentials. Replace with a real user table + password hashing before deploying.
ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = 'lumen123'

ORDER_STATUSES = ['Pending', 'Processing', 'Shipped', 'Delivered', 'Cancelled']

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

_status_column_checked = False

def ensure_order_status_column():
    """Older databases were created before orders.status existed."""
    global _status_column_checked
    if _status_column_checked:
        return
    conn = get_db_connection()
    columns = [row['name'] for row in conn.execute('PRAGMA table_info(orders)').fetchall()]
    if 'status' not in columns:
        conn.execute("ALTER TABLE orders ADD COLUMN status TEXT NOT NULL DEFAULT 'Pending'")
        conn.commit()
    conn.close()
    _status_column_checked = True

def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get('is_admin'):
            flash('Please sign in to access the admin area.', 'error')
            return redirect(url_for('admin_login', next=request.path))
        return view(*args, **kwargs)
    return wrapped

@app.before_request
def ensure_db_and_cart():
    if not os.path.exists(DB_PATH):
        from seed_data import init_db
        init_db()
    ensure_order_status_column()
    if 'cart' not in session:
        session['cart'] = {}

@app.context_processor
def inject_cart_count():
    cart = session.get('cart', {})
    total_count = sum(item.get('quantity', 1) for item in cart.values())
    return dict(cart_count=total_count)

@app.route('/')
def index():
    conn = get_db_connection()
    featured_products = conn.execute('SELECT * FROM products LIMIT 4').fetchall()
    conn.close()
    return render_template('index.html', products=featured_products)

@app.route('/shop')
def shop():
    category = request.args.get('category', '')
    search = request.args.get('search', '')
    
    conn = get_db_connection()
    query = 'SELECT * FROM products WHERE 1=1'
    params = []
    
    if category:
        query += ' AND category = ?'
        params.append(category)
    if search:
        query += ' AND (title LIKE ? OR description LIKE ?)'
        params.append(f'%{search}%')
        params.append(f'%{search}%')
        
    products = conn.execute(query, params).fetchall()
    conn.close()
    return render_template('shop.html', products=products, current_category=category, search_query=search)

@app.route('/product/<int:product_id>')
def product_detail(product_id):
    conn = get_db_connection()
    product = conn.execute('SELECT * FROM products WHERE id = ?', (product_id,)).fetchone()
    related_products = conn.execute('SELECT * FROM products WHERE id != ? LIMIT 3', (product_id,)).fetchall()
    conn.close()
    
    if product is None:
        return "Product not found", 404
        
    return render_template('product-detail.html', product=product, related_products=related_products)

@app.route('/cart')
def cart_view():
    cart = session.get('cart', {})
    cart_items = []
    subtotal = 0.0
    
    conn = get_db_connection()
    for pid_str, details in list(cart.items()):
        p = conn.execute('SELECT * FROM products WHERE id = ?', (int(pid_str),)).fetchone()
        if p:
            qty = details.get('quantity', 1)
            item_total = p['price'] * qty
            subtotal += item_total
            cart_items.append({
                'id': p['id'],
                'title': p['title'],
                'price': p['price'],
                'category': p['category'],
                'image_url': p['image_url'],
                'quantity': qty,
                'total': item_total
            })
    conn.close()
    
    shipping = 15.0 if subtotal > 0 else 0.0
    tax = subtotal * 0.08
    grand_total = subtotal + shipping + tax
    
    return render_template('cart.html', items=cart_items, subtotal=subtotal, shipping=shipping, tax=tax, total=grand_total)

@app.route('/cart/add', methods=['POST'])
def cart_add():
    product_id = str(request.form.get('product_id'))
    try:
        quantity = int(request.form.get('quantity', 1))
    except ValueError:
        quantity = 1
    
    cart = session.get('cart', {})
    if product_id in cart:
        cart[product_id]['quantity'] += quantity
    else:
        cart[product_id] = {'quantity': quantity}
        
    session['cart'] = cart
    session.modified = True
    return redirect(url_for('cart_view'))

@app.route('/cart/update', methods=['POST'])
def cart_update():
    product_id = str(request.form.get('product_id'))
    try:
        new_quantity = int(request.form.get('quantity', 1))
    except ValueError:
        new_quantity = 1
        
    cart = session.get('cart', {})
    if product_id in cart:
        if new_quantity > 0:
            cart[product_id]['quantity'] = new_quantity
        else:
            del cart[product_id]
        session['cart'] = cart
        session.modified = True
        
    return redirect(url_for('cart_view'))

@app.route('/cart/remove', methods=['POST'])
def cart_remove():
    product_id = str(request.form.get('product_id'))
    cart = session.get('cart', {})
    
    if product_id in cart:
        del cart[product_id]
        session['cart'] = cart
        session.modified = True
        
    return redirect(url_for('cart_view'))

@app.route('/cart/clear', methods=['POST'])
def cart_clear():
    session['cart'] = {}
    session.modified = True
    return redirect(url_for('cart_view'))

@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    if request.method == 'POST':
        name = request.form.get('full_name', 'Customer')
        email = request.form.get('email', 'customer@example.com')
        address = request.form.get('address', '123 Main St')
        city = request.form.get('city', 'City')
        payment = request.form.get('payment_method', 'Credit Card')
        
        cart = session.get('cart', {})
        cart_payload = request.form.get('cart', '')
        if cart_payload:
            try:
                submitted_items = json.loads(cart_payload)
                cart = {
                    str(item['id']): {'quantity': max(int(item.get('qty', 1)), 1)}
                    for item in submitted_items
                    if item.get('id') is not None
                }
                session['cart'] = cart
                session.modified = True
            except (TypeError, ValueError, json.JSONDecodeError):
                cart = session.get('cart', {})
        if not cart:
            return redirect(url_for('shop'))
            
        conn = get_db_connection()
        subtotal = 0.0
        for pid, item in cart.items():
            p = conn.execute('SELECT price FROM products WHERE id = ?', (int(pid),)).fetchone()
            if p:
                subtotal += p['price'] * item.get('quantity', 1)
                
        total = subtotal + 15.0 + (subtotal * 0.08)
        
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO orders (customer_name, customer_email, address, city, payment_method, total_amount)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (name, email, address, city, payment, total))
        order_id = cursor.lastrowid
        
        for pid, item in cart.items():
            p = conn.execute('SELECT title, price FROM products WHERE id = ?', (int(pid),)).fetchone()
            if p:
                cursor.execute('''
                    INSERT INTO order_items (order_id, product_id, product_name, price, quantity)
                    VALUES (?, ?, ?, ?, ?)
                ''', (order_id, int(pid), p['title'], p['price'], item.get('quantity', 1)))
            
        conn.commit()
        conn.close()
        
        session['cart'] = {}
        session.modified = True
        return redirect(url_for('order_success', order_id=order_id))
        
    # GET request
    return render_template('checkout.html')

@app.route('/order-success')
def order_success():
    order_id = request.args.get('order_id', 'LUMEN-98234')
    return render_template('order-success.html', order_id=order_id)

@app.route('/contact')
def contact():
    return render_template('contact.html')

# ---------------------------------------------------------------------------
# Admin
# ---------------------------------------------------------------------------

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username', '')
        password = request.form.get('password', '')
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['is_admin'] = True
            session.modified = True
            next_url = request.form.get('next') or url_for('admin_dashboard')
            if not next_url.startswith('/'):
                next_url = url_for('admin_dashboard')
            return redirect(next_url)
        flash('Invalid username or password.', 'error')
    return render_template('admin/login.html', next=request.args.get('next', ''))

@app.route('/admin/logout')
def admin_logout():
    session.pop('is_admin', None)
    session.modified = True
    flash('Signed out.', 'success')
    return redirect(url_for('admin_login'))

@app.route('/admin')
@admin_required
def admin_dashboard():
    conn = get_db_connection()
    stats = {
        'products': conn.execute('SELECT COUNT(*) AS c FROM products').fetchone()['c'],
        'orders': conn.execute('SELECT COUNT(*) AS c FROM orders').fetchone()['c'],
        'revenue': conn.execute('SELECT COALESCE(SUM(total_amount), 0) AS s FROM orders').fetchone()['s'],
        'low_stock': conn.execute('SELECT COUNT(*) AS c FROM products WHERE stock < 20').fetchone()['c'],
    }
    recent_orders = conn.execute(
        'SELECT * FROM orders ORDER BY id DESC LIMIT 5'
    ).fetchall()
    low_stock_products = conn.execute(
        'SELECT * FROM products WHERE stock < 20 ORDER BY stock ASC LIMIT 5'
    ).fetchall()
    top_products = conn.execute('''
        SELECT product_name, SUM(quantity) AS units, SUM(price * quantity) AS revenue
        FROM order_items
        GROUP BY product_name
        ORDER BY units DESC
        LIMIT 5
    ''').fetchall()
    conn.close()
    return render_template(
        'admin/dashboard.html',
        stats=stats,
        recent_orders=recent_orders,
        low_stock_products=low_stock_products,
        top_products=top_products
    )

@app.route('/admin/products')
@admin_required
def admin_products():
    search = request.args.get('search', '')
    conn = get_db_connection()
    if search:
        products = conn.execute(
            'SELECT * FROM products WHERE title LIKE ? OR category LIKE ? ORDER BY id DESC',
            (f'%{search}%', f'%{search}%')
        ).fetchall()
    else:
        products = conn.execute('SELECT * FROM products ORDER BY id DESC').fetchall()
    conn.close()
    return render_template('admin/products.html', products=products, search_query=search)

def _product_form_values():
    """Read + coerce the product form. Returns (values, errors)."""
    errors = []
    values = {
        'title': request.form.get('title', '').strip(),
        'category': request.form.get('category', '').strip(),
        'tag': request.form.get('tag', '').strip(),
        'description': request.form.get('description', '').strip(),
        'image_url': request.form.get('image_url', '').strip() or 'static/images/aura-pro-headphones.svg',
        'price': request.form.get('price', ''),
        'old_price': request.form.get('old_price', ''),
        'rating': request.form.get('rating', ''),
        'reviews_count': request.form.get('reviews_count', ''),
        'stock': request.form.get('stock', ''),
    }

    if not values['title']:
        errors.append('Title is required.')
    if not values['category']:
        errors.append('Category is required.')
    if not values['description']:
        errors.append('Description is required.')

    def to_number(key, caster, default, label):
        raw = values[key]
        if raw in ('', None):
            return default
        try:
            return caster(raw)
        except (TypeError, ValueError):
            errors.append(f'{label} must be a number.')
            return default

    values['price'] = to_number('price', float, 0.0, 'Price')
    values['old_price'] = to_number('old_price', float, None, 'Old price')
    values['rating'] = to_number('rating', float, 4.8, 'Rating')
    values['reviews_count'] = to_number('reviews_count', int, 0, 'Reviews count')
    values['stock'] = to_number('stock', int, 0, 'Stock')

    if values['price'] is not None and values['price'] < 0:
        errors.append('Price cannot be negative.')
    if values['stock'] is not None and values['stock'] < 0:
        errors.append('Stock cannot be negative.')

    return values, errors

@app.route('/admin/products/new', methods=['GET', 'POST'])
@admin_required
def admin_product_new():
    if request.method == 'POST':
        values, errors = _product_form_values()
        if errors:
            for message in errors:
                flash(message, 'error')
            return render_template('admin/product-form.html', product=values, mode='new')

        conn = get_db_connection()
        conn.execute('''
            INSERT INTO products (title, category, price, old_price, rating, reviews_count, tag, description, image_url, stock)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            values['title'], values['category'], values['price'], values['old_price'],
            values['rating'], values['reviews_count'], values['tag'] or None,
            values['description'], values['image_url'], values['stock']
        ))
        conn.commit()
        conn.close()
        flash(f"Product \"{values['title']}\" created.", 'success')
        return redirect(url_for('admin_products'))

    return render_template('admin/product-form.html', product=None, mode='new')

@app.route('/admin/products/<int:product_id>/edit', methods=['GET', 'POST'])
@admin_required
def admin_product_edit(product_id):
    conn = get_db_connection()
    product = conn.execute('SELECT * FROM products WHERE id = ?', (product_id,)).fetchone()

    if product is None:
        conn.close()
        flash('Product not found.', 'error')
        return redirect(url_for('admin_products'))

    if request.method == 'POST':
        values, errors = _product_form_values()
        if errors:
            conn.close()
            for message in errors:
                flash(message, 'error')
            values['id'] = product_id
            return render_template('admin/product-form.html', product=values, mode='edit')

        conn.execute('''
            UPDATE products
            SET title = ?, category = ?, price = ?, old_price = ?, rating = ?,
                reviews_count = ?, tag = ?, description = ?, image_url = ?, stock = ?
            WHERE id = ?
        ''', (
            values['title'], values['category'], values['price'], values['old_price'],
            values['rating'], values['reviews_count'], values['tag'] or None,
            values['description'], values['image_url'], values['stock'], product_id
        ))
        conn.commit()
        conn.close()
        flash(f"Product \"{values['title']}\" updated.", 'success')
        return redirect(url_for('admin_products'))

    conn.close()
    return render_template('admin/product-form.html', product=product, mode='edit')

@app.route('/admin/products/<int:product_id>/delete', methods=['POST'])
@admin_required
def admin_product_delete(product_id):
    conn = get_db_connection()
    product = conn.execute('SELECT title FROM products WHERE id = ?', (product_id,)).fetchone()
    if product is None:
        conn.close()
        flash('Product not found.', 'error')
        return redirect(url_for('admin_products'))

    conn.execute('DELETE FROM products WHERE id = ?', (product_id,))
    conn.commit()
    conn.close()
    flash(f"Product \"{product['title']}\" deleted.", 'success')
    return redirect(url_for('admin_products'))

@app.route('/admin/orders')
@admin_required
def admin_orders():
    status = request.args.get('status', '')
    conn = get_db_connection()
    if status:
        orders = conn.execute(
            'SELECT * FROM orders WHERE status = ? ORDER BY id DESC', (status,)
        ).fetchall()
    else:
        orders = conn.execute('SELECT * FROM orders ORDER BY id DESC').fetchall()
    conn.close()
    return render_template(
        'admin/orders.html', orders=orders, statuses=ORDER_STATUSES, current_status=status
    )

@app.route('/admin/orders/<int:order_id>')
@admin_required
def admin_order_detail(order_id):
    conn = get_db_connection()
    order = conn.execute('SELECT * FROM orders WHERE id = ?', (order_id,)).fetchone()
    if order is None:
        conn.close()
        flash('Order not found.', 'error')
        return redirect(url_for('admin_orders'))

    items = conn.execute(
        'SELECT * FROM order_items WHERE order_id = ?', (order_id,)
    ).fetchall()
    conn.close()

    subtotal = sum(item['price'] * item['quantity'] for item in items)
    return render_template(
        'admin/order-detail.html',
        order=order, items=items, subtotal=subtotal, statuses=ORDER_STATUSES
    )

@app.route('/admin/orders/<int:order_id>/status', methods=['POST'])
@admin_required
def admin_order_status(order_id):
    new_status = request.form.get('status', '')
    if new_status not in ORDER_STATUSES:
        flash('Unknown order status.', 'error')
        return redirect(url_for('admin_order_detail', order_id=order_id))

    conn = get_db_connection()
    conn.execute('UPDATE orders SET status = ? WHERE id = ?', (new_status, order_id))
    conn.commit()
    conn.close()
    flash(f'Order #{order_id} marked as {new_status}.', 'success')
    return redirect(url_for('admin_order_detail', order_id=order_id))

if __name__ == '__main__':
    app.run(debug=True, port=int(os.environ.get('PORT', 5000)))
