from flask import Blueprint, render_template, request, redirect, url_for
from flask_login import login_required, current_user

from App.checkFunctions import checkAdmin
from App.db.models.database import db, Studenti, Docenti, Esami

admin = Blueprint('admin', __name__, url_prefix='/admin', template_folder='templates')

@admin.route('/')
@login_required
@checkAdmin
def adminPage():
    return render_template('admin/home.html', professore = current_user)


@admin.route('/creaStudente')
@login_required
@checkAdmin
def creaStudente():
    return render_template('admin/creaStudente.html')


@admin.route('/creaStudente/inserisciStudente', methods=['POST'])
@login_required
@checkAdmin
def inserisciStudente():
    nome = request.form['name']
    cognome = request.form['surname']
    matricola = request.form['matricola']
    password = request.form['password']
    phone = request.form['phone']

    db.session.add(Studenti(matricola=matricola, name=nome, surname=cognome, password=password, phone=phone, admin= current_user.codAdmin))
    db.session.commit()

    studente = Studenti.query.filter_by(matricola=matricola).first()

    #piano di studi
    esami = Esami.query.all()
    for esame in esami:
        studente.esami.append(esame)
    db.session.commit()

    return redirect(url_for('admin.adminPage'))

@admin.route('/creaDocente')
@login_required
@checkAdmin
def creaDocente():
    return render_template('admin/creaDocente.html')

@admin.route('creaDocente/inserisciDocente', methods=['POST'])
@login_required
@checkAdmin
def inserisciDocente():
    nome = request.form['name']
    cognome = request.form['surname']
    password = request.form['password']

    db.session.add(Docenti(name=nome, surname=cognome, password=password))
    db.session.commit()

    return redirect(url_for('admin.adminPage'))



@admin.route('/creaEsame')
@login_required
@checkAdmin
def creaEsame():
    docenti = Docenti.query.all()
    return render_template('admin/creaEsame.html', docenti=docenti)


@admin.route('/creaEsame/inserisciEsame', methods=['POST'])
@login_required
@checkAdmin
def inserisciEsame():
    nome = request.form['name']
    codice = request.form['cod']
    cfu = request.form['cfu']
    anno = request.form['anno']
    docente_cod = request.form['docente_cod']

    db.session.add(Esami(name=nome, cod=codice, cfu=cfu, anno=anno))
    db.session.commit()

    #docente_Cod è listea?
    docente = Docenti.query.get(docente_cod)
    docente.esami.append(Esami.query.get(codice))
    db.session.commit()

    return redirect(url_for('admin.adminPage'))


@admin.route('/visualizzaStudenti')
@login_required
@checkAdmin
def visualizzaStudenti():
    studenti = Studenti.query.all()
    return render_template('admin/visualizzaStudenti.html', studenti=studenti)


@admin.route('/visualizzaDocenti')
@login_required
@checkAdmin
def visualizzaDocenti():
    docenti = Docenti.query.all()
    return render_template('admin/visualizzaDocenti.html', docenti=docenti)


@admin.route('/visualizzaEsami')
@login_required
@checkAdmin
def visualizzaEsami():
    esami = Esami.query.all()
    return render_template('admin/visualizzaEsami.html', esami=esami)


@admin.route('/visualizzaEsami/ricercaDocente/<codEsame>', methods=['GET', 'POST'])
@login_required
@checkAdmin
def ricercaDocente(codEsame):
    esame = Esami.query.get(codEsame)
    docenti = Docenti.query.all()
    docenti_esame = esame.docenti
    docenti_da_aggiungere = set(docenti )- set(docenti_esame)
    return render_template('admin/ricercaDocenti.html', esame=esame, docenti = docenti_da_aggiungere)


@admin.route('/visualizzaEsami/ricercaDocente/<codEsame>/aggiungiDocente/<codDocente>', methods=['GET', 'POST'])
@login_required
@checkAdmin
def aggiungiDocente(codEsame, codDocente):
    esame = Esami.query.get(codEsame)
    docente = Docenti.query.get(codDocente)
    esame.docenti.append(docente)
    db.session.commit()
    return redirect(url_for('admin.visualizzaEsami'))

