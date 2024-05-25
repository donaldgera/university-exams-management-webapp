import os

from flask import Blueprint, redirect, url_for, session, request, render_template, current_app
from flask_login import login_required, current_user, login_user, logout_user

from App.db.models.database import Docenti, Studenti, db, Admin
from App.utils.utilies import check_credentials

auth = Blueprint('auth', __name__)


@auth.route('/')
def home():
    print("sono in home")
    db.session.close()
    current_app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL_LOCALE_UTENTE')
    return render_template('home.html')


@auth.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        if session['user_type'] == Studenti.__name__:
            return redirect(url_for('student.studentPage'))
        if session['user_type'] == Admin.__name__:
            return redirect(url_for('admin.adminPage'))
        elif session['user_type'] == Docenti.__name__:
            return redirect(url_for('teacher.teacherPage'))

    db.session.close()
    current_app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL_LOCALE_UTENTE')
    print(current_app.config['SQLALCHEMY_DATABASE_URI'])
    if request.method == 'POST':
        print("request.form['user']:", request.form['user'])
        pair = check_credentials(request.form['user'], request.form['password'])
        print("pair:", pair)
        if pair[0]:
            print('login success')
            login_user(pair[1])
            db.session.close()
            if session['user_type'] == Studenti.__name__:
                current_app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL_LOCALE_STUDENTE')
                return redirect(url_for('student.studentPage'))
            if session['user_type'] == Admin.__name__:
                current_app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL_LOCALE_ADMIN')
                return redirect(url_for('admin.adminPage'))
            else:
                current_app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL_LOCALE_DOCENTE')
                return redirect(url_for('teacher.teacherPage'))

    print('login failed')
    return render_template('login.html')


@auth.route('/logout', methods=['GET', 'POST'])
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))