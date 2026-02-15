# routes.py
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import login_user, logout_user, login_required, current_user
from extensions import db
from forms import LoginForm, ProductForm, UserForm, ProductImportForm
from datetime import datetime, timedelta, date # Importa date e timedelta para os relatórios
import json
from functools import wraps
import pandas as pd
import io
from sqlalchemy import or_, func # Importa or_ e func explicitamente para clareza

main_bp = Blueprint('main', __name__)

# --- Decoradores Personalizados ---

def admin_required(f):
    """
    Decorador para rotas que exigem que o usuário autenticado seja um administrador.
    Redireciona para o dashboard com uma mensagem de erro se o usuário não for admin.
    Usa @wraps para preservar os metadados da função original, evitando erros de endpoint.
    """
    @wraps(f)
    @login_required # Garante que o usuário esteja logado antes de verificar a role
    def decorated_function(*args, **kwargs):
        # Importa User aqui, dentro da função decorada, para garantir que models.py
        # seja carregado apenas quando uma rota decorada for acessada e db já esteja inicializado.
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
    """
    Rota para o login de usuários.
    Se o usuário já estiver autenticado, redireciona para o dashboard.
    Processa o formulário de login, autentica o usuário e redireciona.
    """
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    form = LoginForm()
    if form.validate_on_submit():
        from models import User # Importa User aqui
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            next_page = request.args.get('next') # Redireciona para a página que o usuário tentou acessar
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

    # Importa os modelos aqui, pois são necessários para as queries do dashboard
    from models import Product, Sale

    total_products = Product.query.count()
    # Filtra vendas do dia atual (UTC)
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
    from models import Product # Importa Product aqui
    products = Product.query.all()
    return render_template('products.html', products=products)

@main_bp.route('/product/add', methods=['GET', 'POST'])
@admin_required
def add_product():
    """
    Adiciona um novo produto ao estoque.
    Apenas administradores podem acessar.
    Processa o formulário de adição de produto.
    """
    from models import Product # Importa Product aqui
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
    """
    Edita um produto existente pelo seu ID.
    Apenas administradores podem acessar.
    Preenche o formulário com os dados atuais do produto e processa as atualizações.
    """
    from models import Product # Importa Product aqui
    product = Product.query.get_or_404(product_id)
    form = ProductForm(obj=product) # Preenche o formulário com os dados do produto
    if form.validate_on_submit():
        # Atualiza os campos do produto com os dados do formulário
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
    """
    Deleta um produto existente pelo seu ID.
    Apenas administradores podem acessar.
    Requer um método POST para segurança.
    """
    from models import Product # Importa Product aqui
    product = Product.query.get_or_404(product_id)
    db.session.delete(product)
    db.session.commit()
    flash('Produto excluído com sucesso!', 'success')
    return redirect(url_for('main.products'))

# --- Rotas de Gerenciamento de Usuários (Admin Apenas) ---

@main_bp.route('/users')
@admin_required
def users():
    """
    Lista todos os usuários do sistema.
    Apenas administradores podem acessar.
    """
    from models import User # Importa User aqui
    users = User.query.all()
    return render_template('users.html', users=users)

@main_bp.route('/user/add', methods=['GET', 'POST'])
@admin_required
def add_user():
    """
    Adiciona um novo usuário ao sistema.
    Apenas administradores podem acessar.
    Inclui verificação para nome de usuário duplicado.
    """
    from models import User # Importa User aqui
    form = UserForm()
    if form.validate_on_submit():
        # --- VERIFICAÇÃO ADICIONADA AQUI ---
        existing_user = User.query.filter_by(username=form.username.data).first()
        if existing_user:
            flash('Nome de usuário já existe. Por favor, escolha outro.', 'danger')
            return render_template('add_user.html', form=form, title='Adicionar Usuário')
        # --- FIM DA VERIFICAÇÃO ---

        user = User(
            username=form.username.data,
            email=form.email.data,
            role=form.role.data
        )
        user.set_password(form.password.data) # Define a senha com hash
        db.session.add(user)
        db.session.commit()
        flash('Usuário adicionado com sucesso!', 'success')
        return redirect(url_for('main.users'))
    return render_template('add_user.html', form=form, title='Adicionar Usuário')

# --- Rotas do PDV ---

@main_bp.route('/pdv')
@login_required
def pdv():
    """
    Página principal do Ponto de Venda.
    """
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
        search_filters.append(Product.id == product_id)
        current_app.logger.debug(f"PDV Search: Adicionada condição de busca por ID: {product_id}")
    except ValueError:
        current_app.logger.debug(f"PDV Search: Query '{query}' não é um ID numérico.")
        pass

    # Busca por Código de Barras (busca exata)
    search_filters.append(Product.barcode == query)
    current_app.logger.debug(f"PDV Search: Adicionada condição de busca por Código de Barras: '{query}'")

    # Busca por Nome (parcial e insensível a maiúsculas/minúsculas)
    search_filters.append(Product.name.ilike(f'%{query}%'))
    current_app.logger.debug(f"PDV Search: Adicionada condição de busca por Nome (ilike): '%{query}%'")

    # 3. Execução da Consulta
    # Combina todas as condições com OR.

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
            'price': float(p.price), # Garante que o preço seja um float
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
    Registra o valor pago e o troco.
    """
    from models import Product, Sale, SaleItem
    data = request.get_json()
    cart_items = data.get('cart', [])
    payment_method = data.get('payment_method')
    total_amount = data.get('total_amount')
    paid_amount = data.get('paid_amount') # Recebe o valor pago
    change_amount = data.get('change_amount') # Recebe o troco

    if not cart_items or not payment_method or total_amount is None:
        return jsonify({'success': False, 'message': 'Dados da venda incompletos.'}), 400

    # Validação adicional para dinheiro: valor pago deve ser suficiente
    if payment_method == 'Dinheiro' and (paid_amount is None or float(paid_amount) < float(total_amount)):
        return jsonify({'success': False, 'message': 'Valor pago insuficiente para pagamento em dinheiro.'}), 400

    try:
        new_sale = Sale(
            total_amount=total_amount,
            payment_method=payment_method,
            user_id=current_user.id,
            paid_amount=paid_amount,   # Salva o valor pago
            change_amount=change_amount # Salva o troco
        )
        db.session.add(new_sale)
        db.session.flush() # Garante que new_sale.id esteja disponível antes de adicionar SaleItems

        list_of_receipt_htmls = []

        for item_data in cart_items:
            product_id = item_data['id']
            quantity_sold = item_data['quantity']
            price_at_sale = item_data['price']

            product = Product.query.get(product_id)
            if not product:
                db.session.rollback()
                return jsonify({'success': False, 'message': f'Produto com ID {product_id} não encontrado.'}), 400
            if product.stock < quantity_sold:
                db.session.rollback()
                return jsonify({'success': False, 'message': f'Estoque insuficiente para {product.name}. Disponível: {product.stock}, Solicitado: {quantity_sold}.'}), 400

            product.stock -= quantity_sold
            db.session.add(product)

            sale_item = SaleItem(
                sale_id=new_sale.id,
                product_id=product_id,
                quantity=quantity_sold,
                price_at_sale=price_at_sale
            )
            db.session.add(sale_item)

            # Gera um cupom para CADA UNIDADE vendida
            for i in range(quantity_sold):
                receipt_html = render_template('receipt.html',
                                               sale_id=new_sale.id,
                                               item=item_data,
                                               item_quantity=1, # Quantidade no cupom individual é 1
                                               item_price=price_at_sale,
                                               item_subtotal=price_at_sale, # Subtotal no cupom individual é o preço unitário
                                               payment_method=payment_method,
                                               operator_username=current_user.username,
                                               timestamp=datetime.utcnow(),
                                               company_name=current_app.config.get('COMPANY_NAME', 'Sua Empresa'),
                                               company_address=current_app.config.get('COMPANY_ADDRESS', 'Endereço da Empresa'),
                                               company_phone=current_app.config.get('COMPANY_PHONE', '(XX) XXXX-XXXX'),
                                               company_cnpj=current_app.config.get('COMPANY_CNPJ', 'XX.XXX.XXX/XXXX-XX'),
                                               logo_path=current_app.config.get('LOGO_PATH', url_for('static', filename='img/logo.png')),
                                               is_single_item_receipt=True,
                                               # Adiciona valor pago e troco ao cupom (se for o último item ou se quiser em todos)
                                               # Para simplificar, vamos passar para todos, mas o JS pode decidir exibir apenas no primeiro
                                               paid_amount=paid_amount,
                                               change_amount=change_amount
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
    """
    Página de visão geral dos relatórios.
    Apenas administradores podem acessar.
    """
    return render_template('reports.html')

@main_bp.route('/reports/cash_flow')
@admin_required
def cash_flow_report():
    """
    Endpoint para gerar relatório de fluxo de caixa.
    Apenas administradores podem acessar.
    Filtra por data e calcula totais por método de pagamento.
    """
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
        'cash_sales': float(cash_sales), # Garante que seja float para JSON
        'card_sales': float(card_sales),
        'pix_sales': float(pix_sales),
        'total_sales': float(total_sales),
        'sales_list': [{
            'id': s.id,
            'timestamp': s.timestamp.strftime('%d/%m/%Y %H:%M:%S'),
            'total_amount': float(s.total_amount),
            'payment_method': s.payment_method,
            'operator': s.user.username,
            'paid_amount': float(s.paid_amount) if s.paid_amount else None,
            'change_amount': float(s.change_amount) if s.change_amount else None
        } for s in sales]
    }
    return jsonify(report_data)

@main_bp.route('/reports/stock')
@admin_required
def stock_report():
    """
    Endpoint para gerar relatório de estoque.
    Apenas administradores podem acessar.
    Lista todos os produtos com suas informações de estoque.
    """
    from models import Product
    products = Product.query.order_by(Product.name).all()
    report_data = [{
        'id': p.id,
        'name': p.name,
        'stock': p.stock,
        'price': float(p.price), # Garante que seja float para JSON
        'description': p.description
    } for p in products]
    return jsonify(report_data)

# --- NOVOS ENDPOINTS PARA DADOS DOS GRÁFICOS DO DASHBOARD ---

@main_bp.route('/reports/top_products', methods=['GET'])
@admin_required
def top_products_report():
    """
    Retorna os 5 produtos mais vendidos por quantidade para o gráfico de barras.
    """
    from models import db, SaleItem, Product

    # Consulta para somar a quantidade de cada produto vendido
    top_products = db.session.query(
        Product.name,
        func.sum(SaleItem.quantity).label('total_quantity')
    ).join(SaleItem).group_by(Product.name).order_by(func.sum(SaleItem.quantity).desc()).limit(5).all()

    results = [{'name': p.name, 'quantity': p.total_quantity} for p in top_products]
    return jsonify(results)

@main_bp.route('/reports/daily_sales', methods=['GET'])
@admin_required
def daily_sales_report():
    """
    Retorna a receita total por dia para os últimos 7 dias para o gráfico de linha.
    """
    from models import db, Sale
    from datetime import timedelta, date

    today = date.utcnow()
    # Gera uma lista das últimas 7 datas
    dates = [(today - timedelta(days=i)) for i in range(6, -1, -1)] # Do mais antigo ao mais recente

    daily_revenue = []
    for d in dates:
        # Soma o total_amount para todas as vendas naquele dia
        revenue = db.session.query(func.sum(Sale.total_amount)).filter(
            func.date(Sale.timestamp) == d
        ).scalar() or 0.0
        daily_revenue.append({
            'date': d.strftime('%d/%m'), # Formata a data para exibição
            'revenue': float(revenue) # Garante que seja um float
        })

    return jsonify(daily_revenue)

# --- Rota de Importação de Produtos ---

@main_bp.route('/import_products', methods=['GET', 'POST'])
@admin_required
def import_products():
    """
    Página e lógica para importar produtos via arquivo (CSV, XLSX, XLSM)
    ou via tabela manual.
    Apenas administradores podem acessar.
    """
    from models import Product
    form = ProductImportForm()

    if form.validate_on_submit(): # Processa o upload de arquivo
        file = form.file.data
        filename = file.filename
        file_extension = filename.rsplit('.', 1)[1].lower()

        df = None
        try:
            file_content = file.read()

            if file_extension == 'csv':
                try:
                    df = pd.read_csv(io.BytesIO(file_content), encoding='utf-8')
                except UnicodeDecodeError: # Tenta outra codificação se a primeira falhar
                    df = pd.read_csv(io.BytesIO(file_content), encoding='latin1')
                except Exception as e:
                    raise ValueError(f"Erro ao ler CSV: {e}")
            elif file_extension in ['xlsx', 'xlsm']:
                df = pd.read_excel(io.BytesIO(file_content))
            else:
                flash('Formato de arquivo não suportado.', 'danger')
                return redirect(url_for('main.import_products'))

            # Normaliza os nomes das colunas para minúsculas
            df.columns = df.columns.str.lower()

            # Mapeamento de nomes de colunas esperados para nomes de modelo
            column_mapping = {
                'nome': 'name',
                'codigo_barras': 'barcode',
                'preco_venda': 'price',
                'estoque_atual': 'stock',
            }

            # Renomeia as colunas do DataFrame
            df.rename(columns=column_mapping, inplace=True)

            # Verifica se todas as colunas necessárias estão presentes após o renomeio
            required_columns = ['name', 'barcode', 'price', 'stock']
            if not all(col in df.columns for col in required_columns):
                missing_cols = [col for col in required_columns if col not in df.columns]
                flash(f'O arquivo está faltando colunas essenciais: {", ".join(missing_cols)}. Verifique os cabeçalhos.', 'danger')
                return redirect(url_for('main.import_products'))

            imported_count = 0
            updated_count = 0
            errors = []

            # Itera sobre as linhas do DataFrame para processar os produtos
            for index, row in df.iterrows():
                name = str(row.get('name', '')).strip()
                barcode = str(row.get('barcode', '')).strip()

                # Validação e conversão de preço
                try:
                    price = float(str(row.get('price', 0)).replace(',', '.'))
                    if price < 0: raise ValueError("Preço negativo")
                except (ValueError, TypeError):
                    errors.append(f"Linha {index+2}: Preço inválido para '{name}' ('{barcode}'): '{row.get('price', 'N/A')}'.")
                    continue

                # Validação e conversão de estoque
                try:
                    stock = int(float(str(row.get('stock', 0)).replace(',', '.')))
                    if stock < 0: raise ValueError("Estoque negativo")
                except (ValueError, TypeError):
                    errors.append(f"Linha {index+2}: Estoque inválido para '{name}' ('{barcode}'): '{row.get('stock', 'N/A')}'.")
                    continue

                # Validação de campos obrigatórios
                if not name:
                    errors.append(f"Linha {index+2}: Nome do produto ausente para código de barras '{barcode}'.")
                    continue
                if not barcode:
                    errors.append(f"Linha {index+2}: Código de barras ausente para produto '{name}'.")
                    continue

                # Tenta encontrar um produto existente pelo código de barras
                existing_product = Product.query.filter_by(barcode=barcode).first()

                if existing_product:
                    # Atualiza o produto existente
                    existing_product.name = name
                    existing_product.price = price
                    existing_product.stock = stock
                    db.session.add(existing_product)
                    updated_count += 1
                else:
                    # Cria um novo produto
                    new_product = Product(
                        name=name,
                        barcode=barcode,
                        price=price,
                        stock=stock
                    )
                    db.session.add(new_product)
                    imported_count += 1

            # Confirma as alterações no banco de dados e exibe mensagens flash
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
            db.session.rollback() # Desfaz as operações em caso de erro
            current_app.logger.error(f"Erro ao processar arquivo de importação: {e}")
            flash(f'Erro ao processar arquivo: {str(e)}', 'danger')
            return redirect(url_for('main.import_products'))

    elif request.method == 'POST' and request.form.get('products_json'): # Processa a importação da tabela manual
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

            # Validação dos dados da tabela manual
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
