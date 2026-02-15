# app.py
from flask import Flask
from extensions import db, login_manager, migrate # Importe 'migrate' aqui
from routes import main_bp
from models import User # Importe User para o user_loader

def create_app():
    """
    Cria e configura a instância da aplicação Flask.
    """
    app = Flask(__name__, instance_relative_config=True)

    # Carrega a configuração padrão do objeto config.Config
    app.config.from_object('config.Config')

    # Tenta carregar a configuração local da pasta instance (para segredos, etc.)
    try:
        app.config.from_pyfile('config.py')
    except FileNotFoundError:
        # Não há problema se o arquivo de configuração local não existir
        pass

    # Inicializa as extensões com a instância do app
    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db) # Inicializa Flask-Migrate com o app e o db

    # Configura a view de login para Flask-Login
    login_manager.login_view = 'main.login'
    login_manager.login_message_category = 'info'
    login_manager.login_message = 'Por favor, faça login para acessar esta página.'

    # Função user_loader para Flask-Login
    @login_manager.user_loader
    def load_user(user_id):
        """
        Carrega um usuário a partir do ID armazenado na sessão.
        Essencial para o Flask-Login funcionar.
        """
        return User.query.get(int(user_id))

    # Registra o Blueprint principal que contém as rotas da aplicação
    app.register_blueprint(main_bp)

    return app

# Bloco principal para executar a aplicação ou scripts de inicialização
if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        # Este bloco só será executado quando você rodar 'python app.py' diretamente.
        # Não será executado por 'flask db init', 'flask db migrate', etc.
        # Use-o para criar o primeiro admin se o banco de dados estiver vazio.
        # Verifique se o banco de dados já existe e se há usuários.
        db.create_all() # Cria as tabelas se elas não existirem (apenas para desenvolvimento inicial)
        if User.query.count() == 0:
            print("Nenhum usuário encontrado. Criando usuário administrador padrão...")
            admin_user = User(username='admin', email='admin@example.com', role='admin')
            admin_user.set_password('admin123') # Altere esta senha em produção!
            db.session.add(admin_user)
            db.session.commit()
            print("Usuário administrador 'admin' criado com senha 'admin123'.")
        else:
            print(f"Total de usuários no sistema: {User.query.count()}")

    app.run(debug=True)
