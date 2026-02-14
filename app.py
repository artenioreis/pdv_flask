# app.py
from flask import Flask
# Importa db e login_manager do novo arquivo extensions.py
from extensions import db, login_manager
from config import Config

# login_manager.login_view e mensagens podem ser configuradas aqui ou em extensions.py
login_manager.login_view = 'main.login'
login_manager.login_message_category = 'info'
login_manager.login_message = 'Por favor, faça login para acessar esta página.'

def create_app(config_class=Config):
    """Cria e configura a aplicação Flask."""
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Inicializa as extensões com a aplicação
    db.init_app(app)
    login_manager.init_app(app)

    # Importa os modelos e as rotas APÓS a inicialização das extensões
    # Isso garante que 'db' e 'login_manager' já estejam ligados ao 'app'
    # quando os módulos 'models' e 'routes' são carregados.
    from models import User # Importa User para a lógica de criação do admin
    from routes import main_bp

    # O user_loader agora será definido em models.py, onde User está disponível.
    # Não precisamos defini-lo aqui.

    app.register_blueprint(main_bp)

    with app.app_context():
        db.create_all() # Cria as tabelas do banco de dados se não existirem
        # Exemplo de criação de um usuário admin inicial se o banco estiver vazio
        if not User.query.filter_by(username='admin').first():
            admin_user = User(username='admin', email='admin@pdv.com', role='admin')
            admin_user.set_password('admin123') # Senha padrão para o admin
            db.session.add(admin_user)
            db.session.commit()
            print("Usuário administrador 'admin' criado com senha 'admin123'.")

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)
