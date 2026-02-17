# routes.py
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import login_user, logout_user, login_required, current_user
from extensions import db
from forms import LoginForm, ProductForm, UserForm, ProductImportForm
from datetime import datetime, timedelta, date
import json
from functools import wraps
import pandas as pd
import io
import time
from sqlalchemy import or_, func
from werkzeug.security import generate_password_hash

# Importar as classes de modelo
from models import User, Product, Sale, SaleItem

main_bp = Blueprint('main', __name__)

# --- Decoradores ---

def admin_required(f):
    """
    Decorador para rotas que exigem que o usuário autenticado seja um administrador.
    """
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if not current_user.is_admin():
            flash('Você não tem permissão para acessar esta página.', 'danger')
            return redirect(url_for('main.dashboard'))
        return f(*args, **kwargs)
    return decorated_function

# --- Rotas de Autenticação ---

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
            next_page = request.args.get('next')
            flash(f'Bem-vindo, {user.username}!', 'success')
            return redirect(next_page or url_for('main.dashboard'))
        else:
            flash('Login inválido. Verifique seu usuário e senha.', 'danger')
    return render_template('login.html', form=form)

@main_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Você foi desconectado.', 'info')
    return redirect(url_for('main.login'))

# --- Rota do Dashboard ---

@main_bp.route('/dashboard')
@login_required
def dashboard():
    if not current_user.is_admin():
        return redirect(url_for('main.pdv'))

    total_products = Product.query.count()
    today = datetime.utcnow().date()
    total_sales_today = Sale.query.filter(func.date(Sale.timestamp) == today).count()
    total_revenue_today = db.session.query(func.sum(Sale.total_amount)).filter(func.date(Sale.timestamp) == today).scalar() or 0

    return render_template('dashboard.html',
                           total_products=total_products,
                           total_sales_today=total_sales_today,
                           total_revenue_today=total_revenue_today)

# --- Rotas de Gerenciamento de Produtos ---

@main_bp.route('/products')
@admin_required
def products():
    products = Product.query.all()
    return render_template('products.html', products=products)

@main_bp.route('/product/add', methods=['GET', 'POST'])
@admin_required
def add_product():
    form = ProductForm()
    if form.validate_on_submit():
        # LÓGICA PARA EVITAR IntegrityError NO BARCODE
        barcode_val = form.barcode.data.strip() if form.barcode.data else ""
        if not barcode_val:
            # Gera um código automático baseado no tempo para evitar o erro de UNIQUE
            barcode_val = f"SEM-COD-{int(time.time())}"

        new_product = Product(
            name=form.name.data,
            description=form.description.data,
            price=form.price.data,
            stock=form.stock.data,
            barcode=barcode_val
        )
        
        if form.return_alert_days.data is not None and form.return_alert_days.data != '':
            new_product.return_alert_days = form.return_alert_days.data
        else:
            new_product.return_alert_days = None

        try:
            db.session.add(new_product)
            db.session.commit()
            flash('Produto adicionado com sucesso!', 'success')
            return redirect(url_for('main.products'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao salvar: O código de barras "{barcode_val}" já existe.', 'danger')
            
    return render_template('add_edit_product.html', title='Adicionar Produto', form=form)

@main_bp.route('/product/edit/<int:product_id>', methods=['GET', 'POST'])
@admin_required
def edit_product(product_id):
    product = Product.query.get_or_404(product_id)
    form = ProductForm(obj=product)
    if form.validate_on_submit():
        form.populate_obj(product)
        # Garante que não fique vazio no edit também para não dar erro
        if not product.barcode or not product.barcode.strip():
            product.barcode = f"SEM-COD-{int(time.time())}"
        
        db.session.commit()
        flash('Produto atualizado com sucesso!', 'success')
        return redirect(url_for('main.products'))
    return render_template('add_edit_product.html', title='Editar Produto', form=form)

@main_bp.route('/product/delete/<int:product_id>', methods=['POST'])
@admin_required
def delete_product(product_id):
    product = Product.query.get_or_404(product_id)
    db.session.delete(product)
    db.session.commit()
    flash('Produto excluído com sucesso!', 'success')
    return redirect(url_for('main.products'))

@main_bp.route('/products/import', methods=['GET', 'POST'])
@admin_required
def import_products():
    form = ProductImportForm()
    imported_products_data = []
    if form.validate_on_submit():
        file = form.file.data
        if file:
            try:
                if file.filename.endswith('.xlsx'):
                    df = pd.read_excel(file)
                elif file.filename.endswith('.csv'):
                    df = pd.read_csv(file)
                else:
                    flash('Formato não suportado.', 'danger')
                    return render_template('import_products.html', form=form, imported_products_data=[])

                column_mapping = {
                    'Nome': 'name', 'Preço': 'price', 'Estoque': 'stock', 'Código': 'barcode'
                }
                df.rename(columns=column_mapping, inplace=True)

                for index, row in df.iterrows():
                    product_data = {
                        'name': row.get('name'),
                        'price': row.get('price'),
                        'stock': row.get('stock'),
                        'barcode': row.get('barcode') or f"IMP-{int(time.time())}-{index}"
                    }
                    imported_products_data.append(product_data)

                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({'success': True, 'products': imported_products_data})
            except Exception as e:
                flash(f'Erro: {str(e)}', 'danger')

    return render_template('import_products.html', form=form, imported_products_data=imported_products_data)

# --- Rotas do PDV ---

@main_bp.route('/pdv')
@login_required
def pdv():
    return render_template('pdv.html')

@main_bp.route('/pdv/search_product', methods=['GET'])
@login_required
def pdv_search_product():
    query = request.args.get('query', '').strip()
    if not query:
        return jsonify([])
    products = Product.query.filter(or_(Product.name.ilike(f'%{query}%'), Product.barcode == query)).limit(10).all()
    return jsonify([{'id': p.id, 'name': p.name, 'price': float(p.price), 'stock': p.stock, 'barcode': p.barcode} for p in products])

@main_bp.route('/pdv/checkout', methods=['POST'])
@login_required
def pdv_checkout():
    """
    Processa o checkout e gera o cupom com as 5 regras de personalização.
    """
    data = request.get_json()
    cart_items = data.get('cart', [])
    payment_method = data.get('payment_method')
    paid_amount = float(data.get('paid_amount', 0))
    change_amount = float(data.get('change_amount', 0))
    total_amount = float(data.get('total_amount', 0))

    if not cart_items:
        return jsonify({'success': False, 'message': 'Carrinho vazio.'}), 400

    try:
        new_sale = Sale(user_id=current_user.id, total_amount=total_amount, payment_method=payment_method, paid_amount=paid_amount, change_amount=change_amount)
        db.session.add(new_sale)
        db.session.flush()

        all_receipt_htmls = []
        receipt_counter = 0

        for item_data in cart_items:
            product = Product.query.get(item_data['id'])
            if not product or product.stock < item_data['quantity']:
                db.session.rollback()
                return jsonify({'success': False, 'message': f'Estoque insuficiente para {item_data["name"]}.'}), 400

            sale_item = SaleItem(sale_id=new_sale.id, product_id=product.id, quantity=item_data['quantity'], price_at_sale=item_data['price'])
            db.session.add(sale_item)
            product.stock -= item_data['quantity']

            # GERAÇÃO DO CUPOM PERSONALIZADO
            for i in range(item_data['quantity']):
                receipt_counter += 1
                receipt_html = f"""
                <div class="receipt-container" style="font-weight: bold; margin-bottom: 60px; font-family: Courier, monospace; text-align: center;">
                    <div class="receipt-header">
                        <p style="font-size: 1.4em; margin: 5px 0;">HOUSEHOT SWING CLUB</p>
                        <p style="margin: 2px 0;">VENDA: #{new_sale.id}</p>
                        <hr style="border-top: 1px dashed #000;">
                        <p>Cupom Não Fiscal</p>
                        <p>Item {receipt_counter} de {sum(item['quantity'] for item in cart_items)}</p>
                        <p>{new_sale.timestamp.strftime('%d/%m/%Y %H:%M:%S')}</p>
                        <hr style="border-top: 1px dashed #000;">
                    </div>
                    <div class="receipt-body">
                        <p>PRODUTO:</p>
                        <p style="font-size: 1.5em; border: 2px solid #000; padding: 8px; margin: 10px 0; display: inline-block; text-transform: uppercase;">{item_data['name']}</p>
                        <p>1 UN x R$ {item_data['price']:.2f}</p>
                        <hr style="border-top: 1px dashed #000;">
                        <p style="font-size: 1.2em;">TOTAL: R$ {item_data['price']:.2f}</p>
                        <p>Pagamento: {payment_method}</p>
                    </div>
                    <div class="receipt-footer">
                        <hr style="border-top: 1px dashed #000;">
                        <p>Obrigado pela preferência!</p>
                        <div style="height: 30px;"></div>
                    </div>
                </div>
                """
                all_receipt_htmls.append(receipt_html)

        db.session.commit()
        return jsonify({'success': True, 'message': 'Venda realizada!', 'receipt_htmls': all_receipt_htmls}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

# --- Rotas de Gerenciamento de Usuários ---

@main_bp.route('/users')
@admin_required
def users():
    users = User.query.all()
    return render_template('users.html', users=users)

@main_bp.route('/user/add', methods=['GET', 'POST'])
@admin_required
def add_user():
    form = UserForm()
    if form.validate_on_submit():
        hashed_password = generate_password_hash(form.password.data, method='pbkdf2:sha256')
        new_user = User(username=form.username.data, password_hash=hashed_password, is_admin=form.is_admin.data)
        db.session.add(new_user)
        db.session.commit()
        flash('Usuário adicionado!', 'success')
        return redirect(url_for('main.users'))
    return render_template('add_edit_user.html', title='Adicionar Usuário', form=form)

@main_bp.route('/user/edit/<int:user_id>', methods=['GET', 'POST'])
@admin_required
def edit_user(user_id):
    user = User.query.get_or_404(user_id)
    form = UserForm(obj=user)
    if form.validate_on_submit():
        user.username = form.username.data
        user.is_admin = form.is_admin.data
        if form.password.data:
            user.password_hash = generate_password_hash(form.password.data, method='pbkdf2:sha256')
        db.session.commit()
        flash('Usuário atualizado!', 'success')
        return redirect(url_for('main.users'))
    return render_template('add_edit_user.html', title='Editar Usuário', form=form)

@main_bp.route('/user/delete/<int:user_id>', methods=['POST'])
@admin_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    flash('Usuário removido!', 'success')
    return redirect(url_for('main.users'))

# --- Relatórios ---

@main_bp.route('/reports')
@admin_required
def reports():
    return render_template('reports.html')

@main_bp.route('/reports/sales_by_period')
@admin_required
def sales_by_period_report():
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')
    sales_query = Sale.query
    if start_date_str:
        sales_query = sales_query.filter(Sale.timestamp >= datetime.strptime(start_date_str, '%Y-%m-%d'))
    if end_date_str:
        sales_query = sales_query.filter(Sale.timestamp < datetime.strptime(end_date_str, '%Y-%m-%d') + timedelta(days=1))
    sales = sales_query.order_by(Sale.timestamp.desc()).all()
    return render_template('reports_sales_by_period.html', sales=sales, total_sales_count=len(sales), total_revenue=sum(s.total_amount for s in sales), start_date=start_date_str, end_date=end_date_str)

@main_bp.route('/reports/top_products')
@admin_required
def top_products_report():
    top_products = db.session.query(Product.name, func.sum(SaleItem.quantity).label('total')).join(SaleItem).group_by(Product.name).order_by(func.sum(SaleItem.quantity).desc()).limit(10).all()
    return render_template('reports_top_products.html', top_products=top_products)