# forms.py
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, DecimalField, IntegerField, SelectField, FileField
from wtforms.validators import DataRequired, Email, EqualTo, Length, NumberRange, Optional, ValidationError
from models import User, Product # Importe Product também

class LoginForm(FlaskForm):
    username = StringField('Usuário', validators=[DataRequired()])
    password = PasswordField('Senha', validators=[DataRequired()])
    submit = SubmitField('Entrar')

class ProductForm(FlaskForm):
    name = StringField('Nome do Produto', validators=[DataRequired(), Length(max=100)])
    description = StringField('Descrição', validators=[Optional()])
    price = DecimalField('Preço de Venda', validators=[DataRequired(), NumberRange(min=0.01)], places=2)
    stock = IntegerField('Estoque Atual', validators=[DataRequired(), NumberRange(min=0)])
    barcode = StringField('Código de Barras', validators=[Optional(), Length(max=100)])
    submit = SubmitField('Salvar Produto')

    def validate_barcode(self, barcode):
        if barcode.data: # Apenas valida se um código de barras foi fornecido
            product = Product.query.filter_by(barcode=barcode.data).first()
            if product:
                # Se estiver editando, permite que o próprio produto tenha seu código de barras
                if product.id != self.id.data: # Assumindo que você passa o id do produto para o formulário em edição
                    raise ValidationError('Este código de barras já está em uso.')

class UserForm(FlaskForm):
    username = StringField('Nome de Usuário', validators=[DataRequired(), Length(min=2, max=64)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Senha', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirmar Senha', validators=[DataRequired(), EqualTo('password', message='As senhas devem ser iguais.')])
    role = SelectField('Função', choices=[('user', 'Usuário Padrão'), ('admin', 'Administrador')], validators=[DataRequired()])
    submit = SubmitField('Salvar Usuário')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            # Se estiver editando, permite que o próprio usuário tenha seu username
            if not hasattr(self, 'original_username') or self.original_username != username.data:
                raise ValidationError('Este nome de usuário já está em uso. Por favor, escolha outro.')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            # Se estiver editando, permite que o próprio usuário tenha seu email
            if not hasattr(self, 'original_email') or self.original_email != email.data:
                raise ValidationError('Este email já está em uso. Por favor, escolha outro.')

class ProductImportForm(FlaskForm):
    file = FileField('Arquivo de Produtos (CSV, XLSX, XLSM)', validators=[DataRequired()])
    submit = SubmitField('Importar Produtos')
