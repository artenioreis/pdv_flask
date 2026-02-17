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
from sqlalchemy import or_, func
from werkzeug.security import generate_password_hash # Importar para setar senha de admin inicial

# Importar as classes de modelo aqui
from models import User, Product, Sale, SaleItem

main_bp = Blueprint('main', __name__)

# --- Decoradores Personalizados ---

def admin_required(f):
    """
    Decorador para rotas que exigem que o usuário autenticado seja um administrador.
    Redireciona para o dashboard com uma mensagem de erro se o usuário não for admin.
    Usa @wraps para preservar os metadados da função original, evitando erros de endpoint.
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
    """
    Rota para o login de usuários.
    Se o usuário já estiver autenticado, redireciona para o dashboard.
    Processa o formulário de login, autentica o usuário e redireciona.
    """
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
    """
    Rota para logout de usuários.
    Desconecta o usuário e redireciona para a página de login.
    """
    logout_user()
    flash('Você foi desconectado.', 'info')
    return redirect(url_for('main.login'))

# --- Rota do Dashboard ---

@main_bp.route('/dashboard')
@login_required
def dashboard():
    """
    Dashboard principal do sistema.
    Se o usuário não for administrador, redireciona-o diretamente para o PDV.
    Para administradores, exibe um resumo de produtos e vendas do dia.
    """
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

# --- Rotas de Gerenciamento de Produtos (Admin Apenas) ---

@main_bp.route('/products')
@admin_required
def products():
    """
    Lista todos os produtos cadastrados no sistema.
    Apenas administradores podem acessar.
    """
    products = Product.query.all()
    return render_template('products.html', products=products)

@main_bp.route('/product/add', methods=['GET', 'POST'])
@admin_required
def add_product():
    """
    Adiciona um novo produto ao sistema.
    Apenas administradores podem acessar.
    """
    form = ProductForm()
    if form.validate_on_submit():
        new_product = Product(
            name=form.name.data,
            description=form.description.data,
            price=form.price.data,
            stock=form.stock.data,
            barcode=form.barcode.data
        )
        # Atribui o campo opcional, garantindo que seja None se vazio
        if form.return_alert_days.data is not None and form.return_alert_days.data != '':
            new_product.return_alert_days = form.return_alert_days.data
        else:
            new_product.return_alert_days = None

        db.session.add(new_product)
        db.session.commit()
        flash('Produto adicionado com sucesso!', 'success')
        return redirect(url_for('main.products'))
    return render_template('add_edit_product.html', title='Adicionar Produto', form=form)

@main_bp.route('/product/edit/<int:product_id>', methods=['GET', 'POST'])
@admin_required
def edit_product(product_id):
    """
    Edita um produto existente no sistema.
    Apenas administradores podem acessar.
    """
    product = Product.query.get_or_404(product_id)
    form = ProductForm(obj=product) # Preenche o formulário com os dados do produto
    if form.validate_on_submit():
        form.populate_obj(product) # Atualiza o objeto produto com os dados do formulário
        # Garante que o campo opcional seja None se vazio
        if form.return_alert_days.data is not None and form.return_alert_days.data == '':
            product.return_alert_days = None
        db.session.commit()
        flash('Produto atualizado com sucesso!', 'success')
        return redirect(url_for('main.products'))
    return render_template('add_edit_product.html', title='Editar Produto', form=form)

@main_bp.route('/product/delete/<int:product_id>', methods=['POST'])
@admin_required
def delete_product(product_id):
    """
    Exclui um produto do sistema.
    Apenas administradores podem acessar.
    """
    product = Product.query.get_or_404(product_id)
    db.session.delete(product)
    db.session.commit()
    flash('Produto excluído com sucesso!', 'success')
    return redirect(url_for('main.products'))

@main_bp.route('/products/import', methods=['GET', 'POST'])
@admin_required
def import_products():
    """
    Importa produtos de um arquivo Excel ou CSV.
    Apenas administradores podem acessar.
    """
    form = ProductImportForm()
    imported_products_data = []

    if form.validate_on_submit():
        file = form.file.data
        if file:
            try:
                # Determina o tipo de arquivo e lê com pandas
                if file.filename.endswith('.xlsx'):
                    df = pd.read_excel(file)
                elif file.filename.endswith('.csv'):
                    df = pd.read_csv(file)
                else:
                    flash('Formato de arquivo não suportado. Use .xlsx ou .csv', 'danger')
                    return render_template('import_products.html', form=form, imported_products_data=[])

                # Mapeamento de colunas (ajuste conforme os cabeçalhos do seu arquivo)
                column_mapping = {
                    'Nome do Produto': 'name',
                    'Nome': 'name',
                    'Descrição': 'description',
                    'Preço de Venda': 'price',
                    'Preço': 'price',
                    'Estoque Atual': 'stock',
                    'Estoque': 'stock',
                    'Código de Barras': 'barcode',
                    'Código': 'barcode',
                    'Alerta Retorno (dias)': 'return_alert_days',
                    'Alerta Retorno': 'return_alert_days',
                    'return_alert_days': 'return_alert_days' # Para compatibilidade direta
                }

                # Renomeia as colunas do DataFrame para corresponder aos nomes do modelo
                df.rename(columns=column_mapping, inplace=True)

                # Converte o DataFrame para uma lista de dicionários
                # Garante que apenas as colunas relevantes para o ProductForm sejam incluídas
                for index, row in df.iterrows():
                    product_data = {
                        'name': row.get('name'),
                        'description': row.get('description'),
                        'price': row.get('price'),
                        'stock': row.get('stock'),
                        'barcode': row.get('barcode'),
                        'return_alert_days': row.get('return_alert_days')
                    }
                    # Filtra None values para campos que podem não existir no Excel
                    imported_products_data.append({k: v for k, v in product_data.items() if v is not None})

                # Se a requisição for AJAX para pré-visualização
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({'success': True, 'products': imported_products_data})

            except Exception as e:
                flash(f'Erro ao processar o arquivo: {str(e)}', 'danger')
                current_app.logger.error(f"Erro na importação de produtos: {e}")

    # Se a requisição for POST para salvar os produtos
    if request.method == 'POST' and not form.file.data: # Verifica se não é um upload de arquivo, mas sim o envio dos dados da tabela
        products_to_save = request.get_json().get('products', [])
        if products_to_save:
            try:
                for p_data in products_to_save:
                    # Tenta encontrar um produto existente pelo código de barras
                    existing_product = Product.query.filter_by(barcode=p_data.get('barcode')).first()

                    if existing_product:
                        # Atualiza o produto existente
                        existing_product.name = p_data.get('name', existing_product.name)
                        existing_product.description = p_data.get('description', existing_product.description)
                        existing_product.price = p_data.get('price', existing_product.price)
                        existing_product.stock = p_data.get('stock', existing_product.stock)
                        existing_product.return_alert_days = p_data.get('return_alert_days', existing_product.return_alert_days)
                    else:
                        # Cria um novo produto
                        new_product = Product(
                            name=p_data.get('name'),
                            description=p_data.get('description'),
                            price=p_data.get('price'),
                            stock=p_data.get('stock'),
                            barcode=p_data.get('barcode'),
                            return_alert_days=p_data.get('return_alert_days')
                        )
                        db.session.add(new_product)
                db.session.commit()
                flash('Produtos importados e/ou atualizados com sucesso!', 'success')
                return jsonify({'success': True, 'message': 'Produtos importados com sucesso!'})
            except Exception as e:
                db.session.rollback()
                flash(f'Erro ao salvar produtos: {str(e)}', 'danger')
                current_app.logger.error(f"Erro ao salvar produtos importados: {e}")
                return jsonify({'success': False, 'message': f'Erro ao salvar produtos: {str(e)}'}), 500
        else:
            flash('Nenhum produto para salvar.', 'warning')
            return jsonify({'success': False, 'message': 'Nenhum produto para salvar.'}), 400

    return render_template('import_products.html', form=form, imported_products_data=imported_products_data)

# --- Rotas de Gerenciamento de Usuários (Admin Apenas) ---

@main_bp.route('/users')
@admin_required
def users():
    """
    Lista todos os usuários cadastrados no sistema.
    Apenas administradores podem acessar.
    """
    users = User.query.all()
    return render_template('users.html', users=users)

@main_bp.route('/user/add', methods=['GET', 'POST'])
@admin_required
def add_user():
    """
    Adiciona um novo usuário ao sistema.
    Apenas administradores podem acessar.
    """
    form = UserForm()
    if form.validate_on_submit():
        hashed_password = generate_password_hash(form.password.data, method='pbkdf2:sha256')
        new_user = User(
            username=form.username.data,
            password_hash=hashed_password,
            is_admin=form.is_admin.data
        )
        db.session.add(new_user)
        db.session.commit()
        flash('Usuário adicionado com sucesso!', 'success')
        return redirect(url_for('main.users'))
    return render_template('add_edit_user.html', title='Adicionar Usuário', form=form)

@main_bp.route('/user/edit/<int:user_id>', methods=['GET', 'POST'])
@admin_required
def edit_user(user_id):
    """
    Edita um usuário existente no sistema.
    Apenas administradores podem acessar.
    """
    user = User.query.get_or_404(user_id)
    form = UserForm(obj=user)
    if form.validate_on_submit():
        user.username = form.username.data
        user.is_admin = form.is_admin.data
        if form.password.data: # Apenas atualiza a senha se um novo valor for fornecido
            user.password_hash = generate_password_hash(form.password.data, method='pbkdf2:sha256')
        db.session.commit()
        flash('Usuário atualizado com sucesso!', 'success')
        return redirect(url_for('main.users'))
    return render_template('add_edit_user.html', title='Editar Usuário', form=form)

@main_bp.route('/user/delete/<int:user_id>', methods=['POST'])
@admin_required
def delete_user(user_id):
    """
    Exclui um usuário do sistema.
    Apenas administradores podem acessar.
    """
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    flash('Usuário excluído com sucesso!', 'success')
    return redirect(url_for('main.users'))

# --- Rotas do PDV (Ponto de Venda) ---

@main_bp.route('/pdv')
@login_required
def pdv():
    """
    Página principal do Ponto de Venda.
    Acessível por qualquer usuário logado.
    """
    return render_template('pdv.html')

@main_bp.route('/pdv/search_product', methods=['GET'])
@login_required
def pdv_search_product():
    """
    Endpoint para buscar produtos por nome ou código de barras para o PDV.
    Retorna uma lista de produtos em formato JSON.
    """
    query = request.args.get('query', '').strip()
    if not query:
        return jsonify([])

    # Busca por nome (case-insensitive) ou código de barras exato
    products = Product.query.filter(
        or_(
            Product.name.ilike(f'%{query}%'),
            Product.barcode == query
        )
    ).limit(10).all() # Limita o número de resultados para melhor performance

    products_data = [{
        'id': p.id,
        'name': p.name,
        'price': float(p.price), # Garante que seja float para JSON
        'stock': p.stock,
        'barcode': p.barcode
    } for p in products]

    return jsonify(products_data)

@main_bp.route('/pdv/checkout', methods=['POST'])
@login_required
def pdv_checkout():
    """
    Processa o checkout de uma venda no PDV.
    Cria uma nova venda e atualiza o estoque dos produtos.
    Gera um cupom HTML para CADA UNIDADE de produto vendida.
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
        new_sale = Sale(
            user_id=current_user.id,
            total_amount=total_amount,
            payment_method=payment_method,
            paid_amount=paid_amount,
            change_amount=change_amount
        )
        db.session.add(new_sale)
        db.session.flush() # Para obter o ID da venda antes do commit

        all_receipt_htmls = [] # Lista para armazenar todos os HTMLs de cupom
        receipt_counter = 0 # Contador para o número do cupom

        for item_data in cart_items:
            product_id = item_data['id']
            quantity_sold_in_item = item_data['quantity'] # Quantidade deste item no carrinho
            product_name = item_data['name']
            price_at_sale = item_data['price']

            product = Product.query.get(product_id)
            if not product or product.stock < quantity_sold_in_item:
                db.session.rollback()
                return jsonify({'success': False, 'message': f'Estoque insuficiente para {product_name}.'}), 400

            # Cria um SaleItem para a quantidade total do item no carrinho
            sale_item = SaleItem(
                sale_id=new_sale.id,
                product_id=product_id,
                quantity=quantity_sold_in_item,
                price_at_sale=price_at_sale
            )
            db.session.add(sale_item)

            product.stock -= quantity_sold_in_item # Atualiza o estoque
            db.session.add(product)

            # --- GERA UM CUPOM PARA CADA UNIDADE VENDIDA DESTE ITEM ---
            for i in range(quantity_sold_in_item):
                receipt_counter += 1
                receipt_html = f"""
                <div class="receipt-container">
                    <div class="receipt-header">
                        <p><strong>PDV Flask</strong></p>
                        <p>Cupom Não Fiscal - Venda #{new_sale.id}</p>
                        <p>Item {receipt_counter} de {sum(item['quantity'] for item in cart_items)}</p>
                        <p>Data: {new_sale.timestamp.strftime('%d/%m/%Y %H:%M:%S')}</p>
                        <p>Operador: {current_user.username}</p>
                        <hr>
                    </div>
                    <div class="receipt-body">
                        <p><strong>ITEM:</strong></p>
                        <p><span class="product-name-highlight">{product_name}</span></p>
                        <p>1 UN x R$ {price_at_sale:.2f} = R$ {price_at_sale:.2f}</p>
                        <hr>
                        <p><strong>TOTAL DESTE CUPOM: R$ {price_at_sale:.2f}</strong></p>
                        <p>Pagamento: {payment_method}</p>
                        <p>Valor Pago: R$ {paid_amount:.2f}</p>
                        <p>Troco: R$ {change_amount:.2f}</p>
                    </div>
                    <div class="receipt-footer">
                        <hr>
                        <p>Obrigado pela preferência!</p>
                    </div>
                </div>
                """
                all_receipt_htmls.append(receipt_html)

        db.session.commit()

        return jsonify({'success': True, 'message': 'Venda finalizada com sucesso!', 'receipt_htmls': all_receipt_htmls}), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Erro no checkout: {e}")
        return jsonify({'success': False, 'message': f'Erro ao finalizar venda: {str(e)}'}), 500

# --- Rotas de Relatórios (Admin Apenas) ---

@main_bp.route('/reports')
@admin_required
def reports():
    """
    Página principal de relatórios.
    Apenas administradores podem acessar.
    """
    return render_template('reports.html')

@main_bp.route('/reports/sales_by_period', methods=['GET'])
@admin_required
def sales_by_period_report():
    """
    Gera um relatório de vendas por período.
    """
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')

    sales_query = Sale.query

    if start_date_str:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
        sales_query = sales_query.filter(Sale.timestamp >= start_date)
    if end_date_str:
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d') + timedelta(days=1) # Inclui o dia inteiro
        sales_query = sales_query.filter(Sale.timestamp < end_date)

    sales = sales_query.order_by(Sale.timestamp.desc()).all()

    total_sales_count = len(sales)
    total_revenue = sum(sale.total_amount for sale in sales)

    return render_template('reports_sales_by_period.html',
                           sales=sales,
                           total_sales_count=total_sales_count,
                           total_revenue=total_revenue,
                           start_date=start_date_str,
                           end_date=end_date_str)

@main_bp.route('/reports/top_products', methods=['GET'])
@admin_required
def top_products_report():
    """
    Gera um relatório dos produtos mais vendidos.
    """
    # Consulta para somar a quantidade vendida de cada produto
    top_products = db.session.query(
        Product.name,
        func.sum(SaleItem.quantity).label('total_quantity_sold'),
        func.sum(SaleItem.quantity * SaleItem.price_at_sale).label('total_revenue_generated')
    ).join(SaleItem).group_by(Product.name).order_by(func.sum(SaleItem.quantity).desc()).limit(10).all()

    return render_template('reports_top_products.html', top_products=top_products)

@main_bp.route('/reports/sales_by_user', methods=['GET'])
@admin_required
def sales_by_user_report():
    """
    Gera um relatório de vendas por usuário (operador).
    """
    sales_by_user = db.session.query(
        User.username,
        func.count(Sale.id).label('total_sales_count'),
        func.sum(Sale.total_amount).label('total_revenue')
    ).join(Sale).group_by(User.username).order_by(func.sum(Sale.total_amount).desc()).all()

    return render_template('reports_sales_by_user.html', sales_by_user=sales_by_user)
