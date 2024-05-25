from flask import Flask, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin, LoginManager
import os

from App.db.models.database import db


def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL_LOCALE_ADMIN')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False



    login_manager = LoginManager()  # inizializzo il login manager
    login_manager.login_view = 'auth.login'  # definisco la pagina di login
    login_manager.init_app(app)  # inizializzo il login manager

    db.init_app(app)

    from App.blueprints.auth import auth  # importo il blueprints auth
    app.register_blueprint(auth, url_prefix='/')  # registro il blueprints auth

    from App.blueprints.student import student  # importo il blueprints views
    app.register_blueprint(student, url_prefix='/student')  # registro il blueprints views

    from App.blueprints.teacher import teacher  # importo il blueprints views
    app.register_blueprint(teacher, url_prefix='/teacher')  # registro il blueprints views

    from App.blueprints.admin import admin  # importo il blueprints views
    app.register_blueprint(admin, url_prefix='/admin')  # registro il blueprints views

    from App.db.models.database import Studenti, Docenti, Admin  # importo le classi Student e Docenti

    @login_manager.user_loader  # definisco la funzione che carica l'utente, essenziale per il login_user(..
    def load_user(id):
        # utilizzo le funzioni fornite da UserMixin
        if session['user_type'] == Docenti.__name__:  # Discrimino in base all'insegnante
           # conn.execute("SET ROLE docente") #da testare
            return Docenti.query.get(int(id))
        if session['user_type'] == Admin.__name__:  # Discrimino in base all'admin
              # conn.execute("SET ROLE admin") #da testare
                return Admin.query.get(int(id))
        elif session['user_type'] == Studenti.__name__:  # Discrimino in base allo studente
          #  conn.execute("SET ROLE studente") #da testare
            return Studenti.query.get(int(id))

    return app


