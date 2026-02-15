# models.py
from extensions import db
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin

class User(db.Model, UserMixin):
    """
    Modelo para representar usuários do sistema.
    Inclui autenticação e controle de acesso baseado em função.
    """
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    role = db.Column(db.String(20), default='user') # 'admin' ou 'user'
    sales = db.relationship('Sale', backref='user', lazy=True) # Relacionamento com vendas

    def set_password(self, password):
        """Define a senha do usuário, armazenando-a como hash."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Verifica se a senha fornecida corresponde ao hash armazenado."""
        return check_password_hash(self.password_hash, password)

    def is_admin(self):
        """Verifica se o usuário tem a função de administrador."""
        return self.role == 'admin'

    def __repr__(self):
        """Representação string do objeto User."""
        return f'<User {self.username}>'

class Product(db.Model):
    """
    Modelo para representar produtos no estoque.
    """
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    stock = db.Column(db.Integer, default=0)
    barcode = db.Column(db.String(100), unique=True, nullable=True) # Código de barras opcional

    def __repr__(self):
        """Representação string do objeto Product."""
        return f'<Product {self.name} - {self.barcode}>'

class Sale(db.Model):
    """
    Modelo para registrar vendas.
    Inclui informações sobre o total, método de pagamento, operador,
    valor pago e troco.
    """
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    total_amount = db.Column(db.Numeric(10, 2), nullable=False)
    payment_method = db.Column(db.String(50), nullable=False) # Ex: 'Dinheiro', 'Cartao', 'Pix'
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    # Novas colunas para valor pago e troco
    paid_amount = db.Column(db.Numeric(10, 2), nullable=True) 
    change_amount = db.Column(db.Numeric(10, 2), nullable=True)

    items = db.relationship('SaleItem', backref='sale', lazy=True) # Itens da venda

    def __repr__(self):
        """Representação string do objeto Sale."""
        return f'<Sale {self.id} - {self.total_amount}>'

class SaleItem(db.Model):
    """
    Modelo para registrar os itens individuais de cada venda.
    """
    id = db.Column(db.Integer, primary_key=True)
    sale_id = db.Column(db.Integer, db.ForeignKey('sale.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    price_at_sale = db.Column(db.Numeric(10, 2), nullable=False) # Preço do produto no momento da venda

    product = db.relationship('Product', backref='sale_items', lazy=True) # Relacionamento com produto

    def __repr__(self):
        """Representação string do objeto SaleItem."""
        return f'<SaleItem {self.id} - Sale: {self.sale_id} - Product: {self.product.name}>'
