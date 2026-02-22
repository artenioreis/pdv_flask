from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import login_user, logout_user, login_required, current_user
from extensions import db
from forms import LoginForm, ProductForm, UserForm, ProductImportForm
from datetime import datetime, timedelta, date
import json
from functools import wraps
import io
import time
from sqlalchemy import or_, func
from werkzeug.security import generate_password_hash 

from models import User, Product, Sale, SaleItem

main_bp = Blueprint('main', __name__)

def admin_required(f):
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if not current_user.is_admin():
            flash('Você não tem permissão para acessar esta página.', 'danger')
            return redirect(url_for('main.dashboard'))
        return f(*args, **kwargs)
    return decorated_function

@main_bp.route('/', methods=['GET', 'POST'])
@main_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            return redirect(request.args.get('next') or url_for('main.dashboard'))
        flash('Login inválido.', 'danger')
    return render_template('login.html', form=form)

@main_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.login'))

@main_bp.route('/dashboard')
@login_required
def dashboard():
    if not current_user.is_admin():
        return redirect(url_for('main.pdv'))
    total_products = Product.query.count()
    today = datetime.utcnow().date()
    total_sales_today = Sale.query.filter(func.date(Sale.timestamp) == today).count()
    total_revenue_today = db.session.query(func.sum(Sale.total_amount)).filter(func.date(Sale.timestamp) == today).scalar() or 0
    low_stock_count = Product.query.filter(Product.stock <= 5).count()
    return render_template('dashboard.html', total_products=total_products, total_sales_today=total_sales_today, total_revenue_today=total_revenue_today, low_stock_count=low_stock_count)

@main_bp.route('/reports/top_products')
@admin_required
def top_products_api():
    top_products_data = db.session.query(
        Product.name, 
        func.sum(SaleItem.quantity).label('quantity'),
        func.sum(SaleItem.quantity * SaleItem.price_at_sale).label('revenue')
    ).join(SaleItem).group_by(Product.id).order_by(func.sum(SaleItem.quantity).desc()).limit(10).all()
    return jsonify([{'name': p.name, 'quantity': int(p.quantity), 'revenue': float(p.revenue)} for p in top_products_data])

@main_bp.route('/reports/daily_sales')
@admin_required
def daily_sales_api():
    today = datetime.utcnow().date()
    sales_data = []
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        revenue = db.session.query(func.sum(Sale.total_amount)).filter(func.date(Sale.timestamp) == day).scalar() or 0
        sales_data.append({'date': day.strftime('%d/%m'), 'revenue': float(revenue)})
    return jsonify(sales_data)

@main_bp.route('/reports/cash_flow')
@admin_required
def cash_flow_api():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    query = Sale.query
    if start_date: query = query.filter(Sale.timestamp >= datetime.strptime(start_date, '%Y-%m-%d'))
    if end_date: query = query.filter(Sale.timestamp < datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1))
    sales = query.all()
    operators_data = {}
    total_general = 0
    for sale in sales:
        op_name = sale.operator.username
        if op_name not in operators_data: 
            operators_data[op_name] = {'Dinheiro': 0, 'Cartao Credito': 0, 'Cartao Debito': 0, 'Pix': 0, 'Total': 0, 'VendasCount': 0}
        method = sale.payment_method
        if method in operators_data[op_name]: operators_data[op_name][method] += sale.total_amount
        operators_data[op_name]['Total'] += sale.total_amount
        operators_data[op_name]['VendasCount'] += 1
        total_general += sale.total_amount
    return jsonify({'operators': operators_data, 'total_general': float(total_general)})

@main_bp.route('/reports/stock')
@admin_required
def stock_report_api():
    products = Product.query.all()
    product_list = []
    total_value = 0
    for p in products:
        val = p.price * p.stock
        product_list.append({'name': p.name, 'stock': p.stock, 'price': float(p.price), 'value': float(val)})
        total_value += val
    return jsonify({'products': product_list, 'total_value': float(total_value)})

@main_bp.route('/products')
@admin_required
def products():
    return render_template('products.html', products=Product.query.all())

@main_bp.route('/product/add', methods=['GET', 'POST'])
@admin_required
def add_product():
    form = ProductForm()
    if form.validate_on_submit():
        barcode_val = form.barcode.data.strip() if form.barcode.data else ""
        if not barcode_val: barcode_val = f"INT-{int(time.time())}"
        new_product = Product(name=form.name.data, description=form.description.data, price=form.price.data, stock=form.stock.data, barcode=barcode_val)
        if form.return_alert_days.data: new_product.return_alert_days = form.return_alert_days.data
        try:
            db.session.add(new_product)
            db.session.commit()
            flash('Produto adicionado!', 'success')
            return redirect(url_for('main.products'))
        except:
            db.session.rollback()
            flash('Erro: Código de barras já existe.', 'danger')
    return render_template('add_edit_product.html', title='Adicionar Produto', form=form)

@main_bp.route('/product/edit/<int:product_id>', methods=['GET', 'POST'])
@admin_required
def edit_product(product_id):
    product = Product.query.get_or_404(product_id)
    form = ProductForm(obj=product)
    if form.validate_on_submit():
        form.populate_obj(product)
        if not product.barcode or not product.barcode.strip(): product.barcode = f"INT-{int(time.time())}"
        db.session.commit()
        return redirect(url_for('main.products'))
    return render_template('add_edit_product.html', title='Editar Produto', form=form)

@main_bp.route('/product/delete/<int:product_id>', methods=['POST'])
@admin_required
def delete_product(product_id):
    product = Product.query.get_or_404(product_id)
    has_sales = SaleItem.query.filter_by(product_id=product_id).first()
    if has_sales:
        flash('Não é possível excluir este produto pois ele possui vendas registradas. Você pode apenas editá-lo.', 'danger')
        return redirect(url_for('main.products'))
        
    db.session.delete(product)
    db.session.commit()
    flash('Produto excluído com sucesso!', 'success')
    return redirect(url_for('main.products'))

@main_bp.route('/products/import', methods=['GET', 'POST'])
@admin_required
def import_products():
    import pandas as pd
    form = ProductImportForm()
    imported_products_data = []
    if form.validate_on_submit():
        file = form.file.data
        if file:
            try:
                df = pd.read_excel(file) if file.filename.endswith('.xlsx') else pd.read_csv(file)
                df.rename(columns={'Nome': 'name', 'Preço': 'price', 'Estoque': 'stock', 'Código': 'barcode'}, inplace=True)
                for index, row in df.iterrows():
                    imported_products_data.append({'name': row.get('name'), 'price': row.get('price'), 'stock': row.get('stock'), 'barcode': row.get('barcode') or f"IMP-{int(time.time())}-{index}"})
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest': return jsonify({'success': True, 'products': imported_products_data})
            except Exception as e: flash(f'Erro: {str(e)}', 'danger')
    return render_template('import_products.html', form=form, imported_products_data=imported_products_data)

@main_bp.route('/pdv')
@login_required
def pdv():
    return render_template('pdv.html')

@main_bp.route('/pdv/search_product', methods=['GET'])
@login_required
def pdv_search_product():
    query = request.args.get('query', '').strip()
    if not query: return jsonify([])
    search = [Product.name.ilike(f'%{query}%'), Product.barcode == query]
    if query.isdigit(): search.append(Product.id == int(query))
    products = Product.query.filter(or_(*search)).limit(10).all()
    return jsonify([{'id': p.id, 'name': p.name, 'price': float(p.price), 'stock': p.stock, 'barcode': p.barcode} for p in products])

@main_bp.route('/pdv/checkout', methods=['POST'])
@login_required
def pdv_checkout():
    data = request.get_json()
    try:
        new_sale = Sale(user_id=current_user.id, total_amount=data['total_amount'], payment_method=data['payment_method'], paid_amount=data['paid_amount'], change_amount=data['change_amount'])
        db.session.add(new_sale)
        db.session.flush()
        
        current_time_str = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
        
        all_receipts = []
        counter = 0
        for item in data['cart']:
            p = Product.query.get(item['id'])
            if not p or p.stock < item['quantity']:
                db.session.rollback()
                return jsonify({'success': False, 'message': f'Sem estoque para {item["name"]}'}), 400
            db.session.add(SaleItem(sale_id=new_sale.id, product_id=p.id, quantity=item['quantity'], price_at_sale=item['price']))
            p.stock -= item['quantity']
            for _ in range(item['quantity']):
                counter += 1
                all_receipts.append(f"""<div class="receipt-container" style="font-weight: bold; margin-bottom: 70px; text-align: center; font-family: sans-serif;"><p style="font-size: 1.5em; margin: 0;">HOUSEHOT SWING CLUB</p><p style="margin: 5px 0;">VENDA: #{new_sale.id}</p><p style="margin: 2px 0;">DATA: {current_time_str}</p><hr style="border-top: 1px dashed #000;"><p>Item {counter} de {sum(i['quantity'] for i in data['cart'])}</p><p style="font-size: 1.6em; border: 2px solid #000; padding: 10px; margin: 10px 0; text-transform: uppercase;">{item['name']}</p><p>1 UN x R$ {item['price']:.2f}</p><hr style="border-top: 1px dashed #000;"><p style="font-size: 1.1em;">PAGAMENTO: {data['payment_method']}</p><p>VALOR PAGO: R$ {data['paid_amount']:.2f}</p><p>TROCO: R$ {data['change_amount']:.2f}</p><hr style="border-top: 1px dashed #000;"><p>Obrigado pela preferência!</p></div>""")
        db.session.commit()
        return jsonify({'success': True, 'receipt_htmls': all_receipts})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@main_bp.route('/users')
@admin_required
def users():
    return render_template('users.html', users=User.query.all())

@main_bp.route('/user/add', methods=['GET', 'POST'])
@admin_required
def add_user():
    form = UserForm()
    if form.validate_on_submit():
        hp = generate_password_hash(form.password.data, method='pbkdf2:sha256')
        new_user = User(username=form.username.data, email=form.email.data, password_hash=hp, role=form.role.data)
        db.session.add(new_user)
        db.session.commit()
        flash('Usuário adicionado com sucesso!', 'success')
        return redirect(url_for('main.users'))
    return render_template('add_edit_user.html', title='Novo Usuário', form=form)

@main_bp.route('/user/delete/<int:user_id>', methods=['POST'])
@admin_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.username == 'admin':
        flash('Não é possível excluir o administrador principal.', 'danger')
        return redirect(url_for('main.users'))
    
    has_sales = Sale.query.filter_by(user_id=user_id).first()
    if has_sales:
        flash('Não é possível excluir este usuário pois ele possui vendas registradas. Você pode apenas editá-lo.', 'danger')
        return redirect(url_for('main.users'))
        
    db.session.delete(user)
    db.session.commit()
    flash('Usuário excluído com sucesso!', 'success')
    return redirect(url_for('main.users'))

@main_bp.route('/reports')
@admin_required
def reports():
    return render_template('reports.html')

@main_bp.route('/reports/sales_by_period')
@admin_required
def sales_by_period_report():
    s_date = request.args.get('start_date')
    e_date = request.args.get('end_date')
    query = Sale.query
    if s_date: query = query.filter(Sale.timestamp >= datetime.strptime(s_date, '%Y-%m-%d'))
    if e_date: query = query.filter(Sale.timestamp < datetime.strptime(e_date, '%Y-%m-%d') + timedelta(days=1))
    sales = query.order_by(Sale.timestamp.desc()).all()
    return render_template('reports_sales_by_period.html', sales=sales, total_sales_count=len(sales), total_revenue=sum(s.total_amount for s in sales), start_date=s_date, end_date=e_date)