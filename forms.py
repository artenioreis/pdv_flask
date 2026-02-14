# forms.py
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, DecimalField, IntegerField, SelectField, FileField
from wtforms.validators import DataRequired, Length, Email, EqualTo, NumberRange, Optional, ValidationError
from flask_wtf.file import FileRequired, FileAllowed
import email_validator # Importa explicitamente para garantir que está disponível

class LoginForm(FlaskForm):
    """Formulário de login para usuários."""
    username = StringField('Usuário', validators=[DataRequired(), Length(min=2, max=64)])
    password = PasswordField('Senha', validators=[DataRequired()])
    submit = SubmitField('Entrar')

class ProductForm(FlaskForm):
    """Formulário para adicionar ou editar produtos."""
    name = StringField('Nome do Produto', validators=[DataRequired(), Length(min=2, max=100)])
    description = StringField('Descrição', validators=[Optional(), Length(max=500)])
    price = DecimalField('Preço de Venda', validators=[DataRequired(), NumberRange(min=0.01)], places=2)
    stock = IntegerField('Estoque Atual', validators=[DataRequired(), NumberRange(min=0)])
    barcode = StringField('Código de Barras', validators=[Optional(), Length(max=128)])
    submit = SubmitField('Salvar Produto')

class UserForm(FlaskForm):
    """Formulário para adicionar ou editar usuários."""
    username = StringField('Usuário', validators=[DataRequired(), Length(min=2, max=64)])
    email = StringField('Email', validators=[DataRequired(), Email(), Length(max=120)])
    password = PasswordField('Senha', validators=[DataRequired(), Length(min=6)])
    role = SelectField('Função', choices=[('operator', 'Operador'), ('admin', 'Administrador')], validators=[DataRequired()])
    submit = SubmitField('Salvar Usuário')

class ProductImportForm(FlaskForm):
    """
    Formulário para upload de arquivo de produtos (CSV, XLSX, XLSM).
    """
    file = FileField('Arquivo de Produtos', validators=[
        FileRequired('Por favor, selecione um arquivo.'),
        FileAllowed(['csv', 'xlsx', 'xlsm'], 'Apenas arquivos CSV, XLSX e XLSM são permitidos!')
    ])
    submit = SubmitField('Importar Arquivo')

