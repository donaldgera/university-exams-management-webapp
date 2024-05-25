from copy import copy
from datetime import datetime
from flask import Blueprint, render_template, request, url_for, redirect, json, flash, get_flashed_messages
from flask_login import login_required, current_user
from sqlalchemy import select, and_
from sqlalchemy.exc import DatabaseError
from sqlalchemy.orm.sync import update

from App.checkFunctions import checkStudente
from App.db.models.database import Appelli, db, formalizzazioneEsami, iscrizioni, Prove

student = Blueprint('student', __name__, url_prefix='/student', template_folder='templates')


@student.route('/')
@login_required
@checkStudente
def studentPage():
    print("sono in studentPage")
    return render_template('student/home.html', student=current_user)


@student.route('/appelliDisponibili')
@login_required
@checkStudente
def appelliDisponibili():
    #rendere disponibili gli appelli per lo studente che non ha ancora prenotato un appello
    #ma ha la possibilità di iscriversi ad un altro appello relativo ad una prova che ha gia passato, ma con voto non formalizzato
    print("sono in prenotaAppello")
    messaggi = get_flashed_messages()
    appelli_disp = current_user.getAppelliDisponibili()
    appelli_non_validi = current_user.getAppelliNonValidi()
    appelli_a_cui_sei_iscritto = set(current_user.appelli) - set(appelli_non_validi)
    prove_a_cui_sono_iscritto = [appello.prove for appello in appelli_a_cui_sei_iscritto]
    return render_template('student/appelliDisponibili.html', appelli_disponibili=appelli_disp, studente = current_user, prove_a_cui_sono_iscritto = prove_a_cui_sono_iscritto, messaggi = messaggi)



@student.route('/appelliDisponibili/prenota/<codAppello>', methods=['POST', 'GET'])
@login_required
@checkStudente
def prenotaAppello(codAppello):
    try:
        print("sono in prenotaAppello")

        selected_appointment_id = codAppello
        appello = Appelli.query.get(selected_appointment_id)
        current_user.appelli.append(appello)

        # Get the prova (exam) associated with the selected appointment
        selected_appointment = Appelli.query.get(selected_appointment_id)
        selected_prova = selected_appointment.prova

        # Use SQLAlchemy's update method on the Iscrizioni table to set 'isValid' to False for existing appointments
        stmt = iscrizioni.update().where(
            and_(
                iscrizioni.c.studente == current_user.matricola,
                iscrizioni.c.appello != selected_appointment_id,
                iscrizioni.c.appello.in_(
                    select(Appelli.codAppello).where(Appelli.prova == selected_prova)
                )
            )
        ).values(isValid=False)


        #Qui si attiverà il trigger che mettera isValid a False per tutte le altre prove che ne dipendono.


        with db.engine.begin() as connection:
            connection.execute(stmt)

        # Commit the changes to the database
        db.session.commit()

        return redirect(url_for('student.appelliDisponibili'))
    except DatabaseError as e:
        print(e)
        flash('Non puoi iscriverti a questa prova, perche non hai ricevuto nessun voto per la prova precedente')
        return redirect(url_for('student.appelliDisponibili'))




@student.route('/prenotazioni')
@login_required
@checkStudente
def prenotazioni():
    print("sono in prenotazioni")
    print(prenotazioni)
    return render_template('student/prenotazioni.html', studente=current_user, datetime= datetime)


@student.route('/prenotazioni/eliminaPrenotazione/<codAppello>', methods=['POST', 'GET'])
@login_required
@checkStudente
def eliminaPrenotazioneAppello(codAppello):
    print("sono in prenotaAppello")
    appello = Appelli.query.get(codAppello)
    if appello in current_user.appelli:
        current_user.appelli.remove(appello)

    db.session.commit()

    return redirect(url_for('student.prenotazioni'))





@student.route('/pianoDiStudi')
@login_required
@checkStudente
def pianoDiStudi():
    print("sono in EsamiFormalizzati")
    print(current_user.esami)
    #for each element in piano di studi, se formalizzato aggiungi il voto

    return render_template('student/pianoDiStudi.html', studente=current_user)


@student.route('/bachecaEsiti')
@login_required
@checkStudente
def esiti():
    #renderizza la pagina di gestione della formalizzazione
    esami_non_form = current_user.getEsamiNonFormalizzatiandPassati()
    return render_template('student/esiti.html', esami=esami_non_form, student = current_user)


@student.route('/bachecaEsiti/formalizza/<codEsame>', methods=['POST', 'GET'])
@login_required
@checkStudente
def formalizza(codEsame):
    #effettua la formalizzazione vera e propria, conclude con un redirect a esiti.
    esame_cod = codEsame
    current_user.formalizzaEsame(esame_cod)
    return redirect(url_for('student.esiti'))


@student.route('/bachecaEsiti/rifiuta/<codEsame>', methods=['POST', 'GET'])
@login_required
@checkStudente
def rifiuta(codEsame):
    #effettua la formalizzazione vera e propria, conclude con un redirect a esiti.
    esame_cod = codEsame
    # Begin a transaction
    current_user.rifiutaEsame(esame_cod)
    return redirect(url_for('student.esiti'))
