from functools import wraps

from flask import render_template
from flask_login import current_user

from App.db.models.database import Docenti, Studenti, Admin


def checkDocente(function):
    @wraps(function)
    def wrapper(*args, **kwargs):
        if not isinstance(current_user, Docenti):
            return render_template('error.html', error='Non hai accesso a questa pagina')
        return function(*args, **kwargs)

    return wrapper

def checkStudente(function):
    @wraps(function)
    def wrapper(*args, **kwargs):
        if not isinstance(current_user, Studenti):
            return render_template('error.html', error='Non hai accesso a questa pagina')
        return function(*args, **kwargs)

    return wrapper

def checkAdmin(function):
    @wraps(function)
    def wrapper(*args, **kwargs):
        if not isinstance(current_user, Admin):
            return render_template('error.html', error='Non hai accesso a questa pagina')
        return function(*args, **kwargs)

    return wrapper
