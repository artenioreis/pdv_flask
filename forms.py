# forms.py
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, DecimalField, IntegerField, TextAreaField, SelectField
from wtforms.validators import DataRequired, Email, EqualTo, NumberRange, Optional

class LoginForm(FlaskForm):
    username = StringField('Usuário', validators=[DataRequired()])
    password = PasswordField('Senha', validators=[DataRequired()])
    submit = SubmitField('Entrar')

class ProductForm(FlaskForm):
    name = StringField('Nome do Produto', validators=[DataRequired()])
    description = TextAreaField('Descrição', validators=[Optional()])
    price = DecimalField('Preço de Venda', validators=[DataRequired(), NumberRange(min=0, message='O preço deve ser positivo.')])
    stock = IntegerField('Estoque Atual', validators=[DataRequired(), NumberRange(min=0, message='O estoque não pode ser negativo.')])
    barcode = StringField('Código de Barras', validators=[Optional()])
    # CAMPO 'return_alert_days' - ESTE É O CAMPO CRÍTICO
    return_alert_days = IntegerField('Alerta de Retorno (dias)', validators=[Optional(), NumberRange(min=0, message='O número de dias deve ser positivo.')],
                                     description='Número de dias para alerta de retorno do produto (opcional).')
    submit = SubmitField('Salvar Produto')

class UserForm(FlaskForm):
    username = StringField('Usuário', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Senha', validators=[DataRequired(), EqualTo('confirm_password', message='As senhas devem ser iguais.')])
    confirm_password = PasswordField('Confirmar Senha', validators=[DataRequired()])
    role = SelectField('Função', choices=[('user', 'Usuário Padrão'), ('admin', 'Administrador')], validators=[DataRequired()])
    submit = SubmitField('Salvar Usuário')

class ProductImportForm(FlaskForm):
    file = StringField('Arquivo Excel/CSV', validators=[Optional()]) # Campo dummy para o label do arquivo
    submit_file = SubmitField('Importar do Arquivo')
    submit_table = SubmitField('Importar da Tabela')
