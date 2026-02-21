# extensions.py
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate # Importe Migrate aqui

# Instancie suas extensões
db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate() # Instancie Migrate aqui