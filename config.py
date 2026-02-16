import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'uma-chave-secreta-muito-segura-e-dificil-de-adivinhar'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///pdv.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # Caminho para o logotipo da empresa (usado nos templates e cupons)
    LOGO_PATH = '/static/img/logo.png'
    COMPANY_NAME = 'HOUSEHOT SWING CLUB'
    COMPANY_ADDRESS = 'R.Carlos Vasconcelos,2206-Aldeota,'
    ##COMPANY_PHONE = '(85)98676-4926'
    COMPANY_CNPJ = 'Copyright By Cachorrão'
