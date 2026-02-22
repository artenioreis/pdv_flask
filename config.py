import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'uma-chave-secreta-muito-segura-e-dificil-de-adivinhar'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///pdv.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    LOGO_PATH = '/static/img/logo.png'
    COMPANY_NAME = 'HOUSEHOT SWING CLUB'
