# models.py
from datetime import datetime
# Importa db e login_manager do novo arquivo extensions.py
from extensions import db, login_manager
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

# O user_loader é definido aqui, pois a classe User está disponível neste módulo
@login_manager.user_loader
def load_user(user_id):
    """Carrega um usuário pelo ID para o Flask-Login."""
    # User.query agora funcionará porque db já foi inicializado com o app
    # quando models.py é importado em app.py (após db.init_app(app)).
    return User.query.get(int(user_id))

class User(db.Model, UserMixin):
    """Modelo para usuários do sistema (administradores e operadores)."""
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(20), default='operator', nullable=False) # 'admin' ou 'operator'

    def set_password(self, password):
        """Define a senha do usuário, armazenando-a como hash."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Verifica se a senha fornecida corresponde ao hash armazenado."""
        return check_password_hash(self.password_hash, password)

    def is_admin(self):
        """Verifica se o usuário é um administrador."""
        return self.role == 'admin'

    def __repr__(self):
        return f'<User {self.username} ({self.role})>'

class Product(db.Model):
    """Modelo para produtos no estoque."""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Float, nullable=False)
    stock = db.Column(db.Integer, default=0, nullable=False)
    barcode = db.Column(db.String(128), unique=True, nullable=True) # Código de barras opcional

    def __repr__(self):
        return f'<Product {self.name} - R${self.price:.2f} - Estoque: {self.stock}>'

class Sale(db.Model):
    """Modelo para uma venda completa."""
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    total_amount = db.Column(db.Float, nullable=False)
    payment_method = db.Column(db.String(20), nullable=False) # 'Dinheiro', 'Cartao', 'Pix'
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', backref=db.backref('sales', lazy=True))
    items = db.relationship('SaleItem', backref='sale', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Sale {self.id} - R${self.total_amount:.2f} - {self.payment_method} - {self.timestamp}>'

class SaleItem(db.Model):
    """Modelo para um item dentro de uma venda."""
    id = db.Column(db.Integer, primary_key=True)
    sale_id = db.Column(db.Integer, db.ForeignKey('sale.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    product = db.relationship('Product', backref=db.backref('sale_items', lazy=True))
    quantity = db.Column(db.Integer, nullable=False)
    price_at_sale = db.Column(db.Float, nullable=False) # Preço do produto no momento da venda

    def __repr__(self):
        return f'<SaleItem {self.id} - Produto: {self.product.name} - Qtd: {self.quantity} - Preço: R${self.price_at_sale:.2f}>'
