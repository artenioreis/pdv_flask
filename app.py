# app.py
from flask import Flask
from extensions import db, login_manager, migrate # Importe migrate
from models import User # Importe User para que o Flask-Login saiba qual modelo usar
from routes import main_bp # Importe seu Blueprint

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'sua_chave_secreta_aqui' # Mude para uma chave forte
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///pdv.db' # Garanta que o nome do DB é 'pdv.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db) # Inicialize o Flask-Migrate

    login_manager.login_view = 'main.login'

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    app.register_blueprint(main_bp)

    # Cria o banco de dados e o usuário admin inicial se não existirem
    with app.app_context():
        db.create_all() # Isso cria as tabelas se elas não existirem.
                        # Para migrações, 'flask db upgrade' é o que atualiza.
        # Código para criar usuário admin inicial (se ainda não tiver)
        if not User.query.filter_by(username='admin').first():
            admin_user = User(username='admin', email='admin@pdv.com', role='admin')
            admin_user.set_password('admin123') # Defina uma senha forte para produção
            db.session.add(admin_user)
            db.session.commit()
            print("Usuário administrador 'admin' criado com sucesso!")

    return app

if __name__ == '__main__':
    app = create_app()
    # Ajustado para habilitar debug e permitir acesso na rede local (host='0.0.0.0')
    app.run(debug=True, host='0.0.0.0', port=5000)