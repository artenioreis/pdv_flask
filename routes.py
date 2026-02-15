# routes.py
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import login_user, logout_user, login_required, current_user
from extensions import db
from forms import LoginForm, ProductForm, UserForm, ProductImportForm
from datetime import datetime
import json
from functools import wraps
import pandas as pd
import io
from sqlalchemy import or_

main_bp = Blueprint('main', __name__)

# --- Decoradores Personalizados ---

def admin_required(f):
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        from models import User
        if not current_user.is_admin():
            flash('Você não tem permissão para acessar esta página.', 'danger')
            return redirect(url_for('main.dashboard'))
        return f(*args, **kwargs)
    return decorated_function

# --- Rotas de Autenticação ---

@main_bp.route('/')
@main_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    form = LoginForm()
    if form.validate_on_submit():
        from models import User
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

    from models import Product, Sale

    total_products = Product.query.count()
    today = datetime.utcnow().date()
    total_sales_today = Sale.query.filter(db.func.date(Sale.timestamp) == today).count()
    total_revenue_today = db.session.query(db.func.sum(Sale.total_amount)).filter(db.func.date(Sale.timestamp) == today).scalar() or 0

    return render_template('dashboard.html',
                           total_products=total_products,
                           total_sales_today=total_sales_today,
                           total_revenue_today=total_revenue_today)

# --- Rotas de Gerenciamento de Produtos (Admin Apenas) ---

@main_bp.route('/products')
@admin_required
def products():
    from models import Product
    products = Product.query.all()
    return render_template('products.html', products=products)

@main_bp.route('/product/add', methods=['GET', 'POST'])
@admin_required
def add_product():
    from models import Product
    form = ProductForm()
    if form.validate_on_submit():
        product = Product(
            name=form.name.data,
            description=form.description.data,
            price=form.price.data,
            stock=form.stock.data,
            barcode=form.barcode.data if form.barcode.data else None
        )
        db.session.add(product)
        db.session.commit()
        flash('Produto adicionado com sucesso!', 'success')
        return redirect(url_for('main.products'))
    return render_template('add_product.html', form=form, title='Adicionar Produto')

@main_bp.route('/product/edit/<int:product_id>', methods=['GET', 'POST'])
@admin_required
def edit_product(product_id):
    from models import Product
    product = Product.query.get_or_404(product_id)
    form = ProductForm(obj=product)
    if form.validate_on_submit():
        product.name = form.name.data
        product.description = form.description.data
        product.price = form.price.data
        product.stock = form.stock.data
        product.barcode = form.barcode.data if form.barcode.data else None
        db.session.commit()
        flash('Produto atualizado com sucesso!', 'success')
        return redirect(url_for('main.products'))
    return render_template('add_product.html', form=form, title='Editar Produto')

@main_bp.route('/product/delete/<int:product_id>', methods=['POST'])
@admin_required
def delete_product(product_id):
    from models import Product
    product = Product.query.get_or_404(product_id)
    db.session.delete(product)
    db.session.commit()
    flash('Produto excluído com sucesso!', 'success')
    return redirect(url_for('main.products'))

# --- Rotas de Gerenciamento de Usuários (Admin Apenas) ---

@main_bp.route('/users')
@admin_required
def users():
    from models import User
    users = User.query.all()
    return render_template('users.html', users=users)

@main_bp.route('/user/add', methods=['GET', 'POST'])
@admin_required
def add_user():
    from models import User
    form = UserForm()
    if form.validate_on_submit():
        user = User(
            username=form.username.data,
            email=form.email.data,
            role=form.role.data
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Usuário adicionado com sucesso!', 'success')
        return redirect(url_for('main.users'))
    return render_template('add_user.html', form=form, title='Adicionar Usuário')

# --- Rotas do PDV ---

@main_bp.route('/pdv')
@login_required
def pdv():
    return render_template('pdv.html')

@main_bp.route('/pdv/search_product', methods=['GET'])
@login_required
def pdv_search_product():
    """
    Endpoint para buscar produtos por ID, nome ou código de barras para o PDV.
    Implementa busca robusta com validação e priorização.
    """
    from models import Product # Importa Product aqui para evitar importação circular
    query = request.args.get('query', '').strip()

    current_app.logger.debug(f"PDV Search: Recebida query '{query}'")

    # 1. Validação da Query
    if not query:
        current_app.logger.debug("PDV Search: Query vazia, retornando resultados vazios.")
        return jsonify([])

    # 2. Construção das Condições de Busca
    search_filters = []

    # Tenta buscar por ID (prioridade alta se for um número exato)
    try:
        product_id = int(query)
        # Se a query é um número, busca por ID exato.
        # Poderíamos adicionar uma condição para retornar apenas este produto se encontrado,
        # mas para uma busca "geral", combinamos com OR.
        search_filters.append(Product.id == product_id)
        current_app.logger.debug(f"PDV Search: Adicionada condição de busca por ID: {product_id}")
    except ValueError:
        # Se não for um número, não é um ID válido, então não adiciona a condição de ID.
        current_app.logger.debug(f"PDV Search: Query '{query}' não é um ID numérico.")
        pass

    # Busca por Código de Barras (busca exata)
    # Códigos de barras são geralmente strings exatas.
    search_filters.append(Product.barcode == query)
    current_app.logger.debug(f"PDV Search: Adicionada condição de busca por Código de Barras: '{query}'")

    # Busca por Nome (parcial e insensível a maiúsculas/minúsculas)
    # Usamos ilike para compatibilidade com diferentes bancos de dados para busca insensível a maiúsculas/minúsculas.
    search_filters.append(Product.name.ilike(f'%{query}%'))
    current_app.logger.debug(f"PDV Search: Adicionada condição de busca por Nome (ilike): '%{query}%'")

    # 3. Execução da Consulta
    # Combina todas as condições com OR.
    # Se a query for um ID, ele será encontrado. Se for um código de barras, será encontrado.
    # Se for parte de um nome, será encontrado.
    # A ordem das condições no OR não afeta o resultado, mas pode afetar ligeiramente a performance
    # dependendo do otimizador do banco de dados.

    # Verifica se há filtros para evitar erro com or_() vazio
    if not search_filters:
        current_app.logger.warning("PDV Search: Nenhuma condição de busca válida foi gerada.")
        return jsonify([])

    try:
        products = Product.query.filter(or_(*search_filters)).limit(10).all()
        current_app.logger.debug(f"PDV Search: Query SQL executada. Encontrados {len(products)} produtos.")
    except Exception as e:
        current_app.logger.error(f"PDV Search: Erro ao executar query no banco de dados: {e}")
        return jsonify({'error': 'Erro interno na busca de produtos.'}), 500


    # 4. Formatação e Retorno dos Resultados
    results = []
    for p in products:
        results.append({
            'id': p.id,
            'name': p.name,
            'price': p.price,
            'stock': p.stock,
            'barcode': p.barcode
        })

    # 5. Verificação de Validação (Opcional, para logs ou depuração)
    if not results and query:
        current_app.logger.info(f"PDV Search: Nenhum produto encontrado para a busca: '{query}'")
    elif results:
        current_app.logger.debug(f"PDV Search: Produtos encontrados para '{query}': {[p['name'] for p in results]}")

    return jsonify(results)

@main_bp.route('/pdv/checkout', methods=['POST'])
@login_required
def pdv_checkout():
    """
    Finaliza uma venda, processando os itens do carrinho, atualizando o estoque
    e gerando um cupom não fiscal PARA CADA UNIDADE VENDIDA.
    """
    from models import Product, Sale, SaleItem
    data = request.get_json()
    cart_items = data.get('cart', [])
    payment_method = data.get('payment_method')
    total_amount = data.get('total_amount') # Este total_amount será o total da venda, não do item

    if not cart_items or not payment_method or total_amount is None:
        return jsonify({'success': False, 'message': 'Dados da venda incompletos.'}), 400

    try:
        # Cria uma venda "mãe" para agrupar todos os itens para fins de relatório
        new_sale = Sale(
            total_amount=total_amount, # Total da transação completa
            payment_method=payment_method,
            user_id=current_user.id
        )
        db.session.add(new_sale)
        db.session.flush() # Obtém o ID da venda antes do commit final

        list_of_receipt_htmls = [] # Lista para armazenar o HTML de cada cupom de unidade

        # Itera sobre cada item no carrinho
        for item_data in cart_items:
            product_id = item_data['id']
            quantity_sold = item_data['quantity'] # Quantidade total deste produto no carrinho
            price_at_sale = item_data['price']

            product = Product.query.get(product_id)
            if not product:
                db.session.rollback()
                return jsonify({'success': False, 'message': f'Produto com ID {product_id} não encontrado.'}), 400
            if product.stock < quantity_sold: # Verifica o estoque para a quantidade total
                db.session.rollback()
                return jsonify({'success': False, 'message': f'Estoque insuficiente para {product.name}. Disponível: {product.stock}, Solicitado: {quantity_sold}.'}), 400

            # Atualiza o estoque do produto UMA VEZ para a quantidade total vendida
            product.stock -= quantity_sold
            db.session.add(product) # Adiciona a alteração de estoque para ser commitada

            # Cria um item de venda associado à venda "mãe" para a quantidade total
            sale_item = SaleItem(
                sale_id=new_sale.id,
                product_id=product_id,
                quantity=quantity_sold, # Registra a quantidade total vendida deste item
                price_at_sale=price_at_sale
            )
            db.session.add(sale_item)

            # Geração do conteúdo do cupom não fiscal PARA CADA UNIDADE
            # Este loop interno é o que garante um cupom por unidade
            for i in range(quantity_sold):
                # Para cada unidade, geramos um cupom individual
                receipt_html = render_template('receipt.html',
                                               sale_id=new_sale.id, # ID da venda mãe
                                               item=item_data, # Dados do item (nome, barcode, etc.)
                                               item_quantity=1, # A quantidade no cupom individual é sempre 1
                                               item_price=price_at_sale,
                                               item_subtotal=price_at_sale, # Subtotal para uma única unidade
                                               payment_method=payment_method,
                                               operator_username=current_user.username,
                                               timestamp=datetime.utcnow(),
                                               company_name=current_app.config['COMPANY_NAME'],
                                               company_address=current_app.config['COMPANY_ADDRESS'],
                                               company_phone=current_app.config['COMPANY_PHONE'],
                                               company_cnpj=current_app.config['COMPANY_CNPJ'],
                                               logo_path=current_app.config['LOGO_PATH'],
                                               is_single_item_receipt=True # Flag para o template
                                               )
                list_of_receipt_htmls.append(receipt_html)

        db.session.commit() # Confirma todas as alterações no banco de dados

        return jsonify({'success': True, 'message': 'Venda realizada com sucesso!', 'receipt_htmls': list_of_receipt_htmls}), 200

    except Exception as e:
        db.session.rollback() # Em caso de erro, desfaz todas as operações no banco
        current_app.logger.error(f"Erro ao finalizar venda: {e}")
        return jsonify({'success': False, 'message': f'Erro interno ao processar a venda: {str(e)}'}), 500

# --- Rotas de Relatórios (Admin Apenas) ---
@main_bp.route('/reports')
@admin_required
def reports():
    return render_template('reports.html')

@main_bp.route('/reports/cash_flow')
@admin_required
def cash_flow_report():
    from models import Sale, User
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')

    query = Sale.query

    if start_date_str:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
        query = query.filter(Sale.timestamp >= start_date)
    if end_date_str:
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
        query = query.filter(Sale.timestamp <= end_date.replace(hour=23, minute=59, second=59))

    sales = query.all()

    cash_sales = sum(s.total_amount for s in sales if s.payment_method == 'Dinheiro')
    card_sales = sum(s.total_amount for s in sales if s.payment_method == 'Cartao')
    pix_sales = sum(s.total_amount for s in sales if s.payment_method == 'Pix')
    total_sales = sum(s.total_amount for s in sales)

    report_data = {
        'cash_sales': cash_sales,
        'card_sales': card_sales,
        'pix_sales': pix_sales,
        'total_sales': total_sales,
        'sales_list': [{
            'id': s.id,
            'timestamp': s.timestamp.strftime('%d/%m/%Y %H:%M:%S'),
            'total_amount': s.total_amount,
            'payment_method': s.payment_method,
            'operator': s.user.username
        } for s in sales]
    }
    return jsonify(report_data)

@main_bp.route('/reports/stock')
@admin_required
def stock_report():
    from models import Product
    products = Product.query.order_by(Product.name).all()
    report_data = [{
        'id': p.id,
        'name': p.name,
        'stock': p.stock,
        'price': p.price,
        'description': p.description
    } for p in products]
    return jsonify(report_data)

# --- Rota de Importação de Produtos ---

@main_bp.route('/import_products', methods=['GET', 'POST'])
@admin_required
def import_products():
    from models import Product
    form = ProductImportForm()

    if form.validate_on_submit():
        file = form.file.data
        filename = file.filename
        file_extension = filename.rsplit('.', 1)[1].lower()

        df = None
        try:
            file_content = file.read()

            if file_extension == 'csv':
                try:
                    df = pd.read_csv(io.BytesIO(file_content), encoding='utf-8')
                except UnicodeDecodeError:
                    df = pd.read_csv(io.BytesIO(file_content), encoding='latin1')
                except Exception as e:
                    raise ValueError(f"Erro ao ler CSV: {e}")
            elif file_extension in ['xlsx', 'xlsm']:
                df = pd.read_excel(io.BytesIO(file_content))
            else:
                flash('Formato de arquivo não suportado.', 'danger')
                return redirect(url_for('main.import_products'))

            df.columns = df.columns.str.lower()

            column_mapping = {
                'nome': 'name',
                'codigo_barras': 'barcode',
                'preco_venda': 'price',
                'estoque_atual': 'stock',
            }

            df.rename(columns=column_mapping, inplace=True)

            required_columns = ['name', 'barcode', 'price', 'stock']
            if not all(col in df.columns for col in required_columns):
                missing_cols = [col for col in required_columns if col not in df.columns]
                flash(f'O arquivo está faltando colunas essenciais: {", ".join(missing_cols)}. Verifique os cabeçalhos.', 'danger')
                return redirect(url_for('main.import_products'))

            imported_count = 0
            updated_count = 0
            errors = []

            for index, row in df.iterrows():
                name = str(row.get('name', '')).strip()
                barcode = str(row.get('barcode', '')).strip()

                try:
                    price = float(str(row.get('price', 0)).replace(',', '.'))
                    if price < 0: raise ValueError("Preço negativo")
                except (ValueError, TypeError):
                    errors.append(f"Linha {index+2}: Preço inválido para '{name}' ('{barcode}'): '{row.get('price', 'N/A')}'.")
                    continue

                try:
                    stock = int(float(str(row.get('stock', 0)).replace(',', '.')))
                    if stock < 0: raise ValueError("Estoque negativo")
                except (ValueError, TypeError):
                    errors.append(f"Linha {index+2}: Estoque inválido para '{name}' ('{barcode}'): '{row.get('stock', 'N/A')}'.")
                    continue

                if not name:
                    errors.append(f"Linha {index+2}: Nome do produto ausente para código de barras '{barcode}'.")
                    continue
                if not barcode:
                    errors.append(f"Linha {index+2}: Código de barras ausente para produto '{name}'.")
                    continue

                existing_product = Product.query.filter_by(barcode=barcode).first()

                if existing_product:
                    existing_product.name = name
                    existing_product.price = price
                    existing_product.stock = stock
                    db.session.add(existing_product)
                    updated_count += 1
                else:
                    new_product = Product(
                        name=name,
                        barcode=barcode,
                        price=price,
                        stock=stock
                    )
                    db.session.add(new_product)
                    imported_count += 1

            db.session.commit()
            if imported_count > 0:
                flash(f'{imported_count} produtos novos importados com sucesso!', 'success')
            if updated_count > 0:
                flash(f'{updated_count} produtos existentes atualizados com sucesso!', 'info')
            if errors:
                flash(f'Alguns produtos tiveram erros e não foram importados/atualizados: {len(errors)} erros. Detalhes: {"; ".join(errors[:5])}{"..." if len(errors) > 5 else ""}', 'warning')
            if imported_count == 0 and updated_count == 0 and not errors:
                flash('Nenhum produto foi importado ou atualizado a partir do arquivo.', 'info')

            return redirect(url_for('main.products'))

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Erro ao processar arquivo de importação: {e}")
            flash(f'Erro ao processar arquivo: {str(e)}', 'danger')
            return redirect(url_for('main.import_products'))

    elif request.method == 'POST' and request.form.get('products_json'):
        products_json = request.form.get('products_json')
        if not products_json:
            flash('Nenhum dado de produto foi enviado da tabela.', 'danger')
            return redirect(url_for('main.import_products'))

        try:
            products_data = json.loads(products_json)
        except json.JSONDecodeError:
            flash('Formato de dados JSON inválido da tabela.', 'danger')
            return redirect(url_for('main.import_products'))

        imported_count = 0
        updated_count = 0
        errors = []

        for item_data in products_data:
            name = str(item_data.get('name', '')).strip()
            barcode = str(item_data.get('barcode', '')).strip()
            price = item_data.get('price')
            stock = item_data.get('stock')

            if not name:
                errors.append(f"Produto com nome ausente para código de barras '{barcode}'.")
                continue
            if not barcode:
                errors.append(f"Produto '{name}' com código de barras ausente.")
                continue
            if not isinstance(price, (int, float)) or price < 0:
                errors.append(f"Preço inválido para '{name}' ('{barcode}'): '{price}'.")
                continue
            if not isinstance(stock, int) or stock < 0:
                errors.append(f"Estoque inválido para '{name}' ('{barcode}'): '{stock}'.")
                continue

            existing_product = Product.query.filter_by(barcode=barcode).first()

            if existing_product:
                existing_product.name = name
                existing_product.price = price
                existing_product.stock = stock
                db.session.add(existing_product)
                updated_count += 1
            else:
                new_product = Product(
                    name=name,
                    barcode=barcode,
                    price=price,
                    stock=stock
                )
                db.session.add(new_product)
                imported_count += 1

        try:
            db.session.commit()
            if imported_count > 0:
                flash(f'{imported_count} produtos novos importados da tabela com sucesso!', 'success')
            if updated_count > 0:
                flash(f'{updated_count} produtos existentes da tabela atualizados com sucesso!', 'info')
            if errors:
                flash(f'Alguns produtos da tabela tiveram erros e não foram importados/atualizados: {"; ".join(errors)}', 'warning')
            if imported_count == 0 and updated_count == 0 and not errors:
                flash('Nenhum produto foi importado ou atualizado da tabela.', 'info')

            return redirect(url_for('main.products'))

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Erro ao importar produtos (JSON da tabela): {e}")
            flash(f'Erro ao importar produtos (JSON da tabela): {str(e)}', 'danger')
            return redirect(url_for('main.import_products'))

    return render_template('import_products.html', title='Importar Produtos', form=form)
