from pytz import UTC

from flask import Blueprint, render_template, request, redirect, url_for
from flask_login import current_user, login_required
from sqlalchemy import func

from App.checkFunctions import checkDocente
from App.db.models.database import Esami, Prove, db, Appelli, Docenti, iscrizioni, Superamenti, Studenti

teacher = Blueprint('teacher', __name__, url_prefix='/teacher', template_folder='templates')


@teacher.route('/')
@login_required
@checkDocente
def teacherPage():
    print("sono in teacherPage")
    return render_template('teacher/home.html', professore=current_user)


@teacher.route('/visualizzaCorsi')
@login_required
@checkDocente
def visualizzaCorsi():
    #visualizza l'elenco dei corsi tenuti dal professore e le relative prove
    print("sono in visualizzaEsami")
    print(current_user.esami)
    return render_template('teacher/corsi.html', user=current_user, esami=current_user.esami)

@teacher.route('/visualizzaCorsi/visualizzaStudentiInGradoDiFormalizzare/<codEsame>', methods=['GET'])
@login_required
@checkDocente
def visualizzaStudentiInGradoDiFormalizzare(codEsame):
    #visualizza gli studenti che hanno superato tutte le prove di un corso, ma non hanno ancora formalizzato il voto
    print("sono in visualizzaStudentiInGradoDiFormalizzare")
    esame = Esami.query.get(codEsame)
    studenti = esame.getStudentiInGradoDiFormalizzare()
    return render_template('teacher/visualizzaStudentiInGradoDiFormalizzare.html', studenti=studenti, codEsame=codEsame)

@teacher.route('/visualizzaCorsi/visualizzaStudentiInGradoDiFormalizzare/<codEsame>/VisualizzaProve/<matricola>', methods=['GET'])
@login_required
@checkDocente
def visualizzaProveStudente(codEsame, matricola):
    # Ottenere lo studente e le prove relative all'esame
    studente = Studenti.query.filter_by(matricola=matricola).first()
    esame = Esami.query.get(codEsame)
    prove_studente = studente.getProveEsame(codEsame)

    return render_template('teacher/visualizzaProveStudente.html', studente=studente, esame=esame,
                           prove_studente=prove_studente)



@teacher.route('/visualizzaCorsi/visualizzaDocenti/<codEsame>', methods=['GET'])
@login_required
@checkDocente
def visualizzaDocenti(codEsame):
    # Ottieni l'elenco dei docenti relativi all'esame con il codice fornito
    print("sono in visualizzaDocenti")
    print(codEsame)
    docenti = Esami.query.get(codEsame).docenti
    print(docenti)
    # Passa l'elenco dei docenti al template HTML
    return render_template('teacher/visualizzaDocenti.html', docenti=docenti, codEsame=codEsame)


@teacher.route('/visualizzaCorsi/visualizzaDocenti/<codEsame>/ricercaDocente', methods=['GET'])
@login_required
@checkDocente
def ricercaDocente(codEsame):
    # Ottieni l'elenco dei docenti relativi all'esame con il codice fornito
    print("sono in ricercaDocente")
    docenti = Docenti.query.all()
    esame = Esami.query.get(codEsame)
    docenti_relativi_esame = esame.docenti

    return render_template('teacher/ricercaDocente.html', docenti= set(set(docenti) - set(docenti_relativi_esame)),
                           codEsame=codEsame)


@teacher.route('/visualizzaCorsi/visualizzaDocenti/<codEsame>/ricercaDocente/aggiungiDocente/<codDocente>', methods=['POST', 'GET'])
@login_required
@checkDocente
def aggiungiDocente(codEsame, codDocente):
    # Ottieni l'elenco dei docenti relativi all'esame con il codice fornito
    esame = Esami.query.get(codEsame)
    docente = Docenti.query.get(codDocente)
    esame.docenti.append(docente)
    db.session.commit()
    docenti = Esami.query.get(codEsame).docenti

    return redirect(url_for('teacher.visualizzaDocenti', docenti = docenti, codEsame=codEsame))


@teacher.route('/visualizzaCorsi/eliminaProve', methods=['POST', 'GET'])
@login_required
@checkDocente
def eliminaProve():

    return redirect(url_for('teacher.visualizzaEsami'))


@teacher.route('/visualizzaCorsi/visualizzaProve/<codEsame>', methods=['POST', 'GET'])
@login_required
@checkDocente
def visualizzaProve(codEsame):
    #visualizza le prove relative ad un corso
    esame = Esami.query.get(codEsame)
    prove = esame.prove
    esiste_appello_realtivo_all_esame = any(prova.appelli for prova in esame.prove)
    #potrei passare anche un booleano che mi dice se si può creare la prova oppure no
    return render_template('teacher/visualizzaProve.html', user=current_user, prove=prove, esame=esame,
                           lista_prove_abilitate=current_user.prove, codEsame=codEsame,
                           nessun_appello_relativo_all_esame = esiste_appello_realtivo_all_esame)


@teacher.route('/visualizzaCorsi/visualizzaProve/<codEsame>/definisciProva', methods=['POST', 'GET'])
@login_required
@checkDocente
def definisciProva(codEsame):
    #la somma dei pesi delle prove relative a un corso deve fare 1.
    #se il professore non ha ancora creato prove per un corso, deve poterlo fare
    #se il professore ha già creato prove per un corso, deve poterle modificare
    #se il professore ha già creato prove per un corso, deve poterle eliminare
    #non è possibile per problemi di progettazione creare le prove una alla volta, ma solo tutte insieme
    docente = current_user
    esame = Esami.query.get(codEsame)
    prove = esame.prove
    return render_template('teacher/definisciProva.html', user=current_user, prove=prove, codEsame=codEsame)



@teacher.route('/visualizzaCorsi/visualizzaProve/<codEsame>/definisciProve/creaProva', methods=['POST', 'GET'])
@login_required
@checkDocente
def creaProva(codEsame):
    print("sono in creaProva")
    print(request.form)
    codProva = request.form['codProva']
    tipologia = request.form['tipologia']
    peso = request.form['peso']
    bonus = request.form['bonus']
    durata = request.form['durata']
    provePrimarie = request.form.getlist('prove_primarie[]')
    new_prova = Prove(cod=codProva, Tipologia=tipologia, peso=peso, Bonus=bonus, durata=durata, idoneità=True if request.form.get('idoneita') == 'true' else False )


    #richiede il superamento della prova....
    new_superamenti = []
    for provaPrimaria in provePrimarie:
         new_superamenti.append(Superamenti(provaPrimaria=provaPrimaria, provaSuccessiva=codProva))

    #controllare le invariatni....

    esame = Esami.query.get(codEsame)
    esame.prove.append(new_prova)
    current_user.prove.append(new_prova)
    db.session.add(new_prova)
    for superamento in new_superamenti:
        db.session.add(superamento)
    db.session.commit()

    return redirect(url_for('teacher.visualizzaProve', codEsame=codEsame))


@teacher.route('/visualizzaCorsi/visualizzaProve/<codEsame>/eliminaProva/<codProva>', methods=['POST', 'GET'])
@login_required
@checkDocente
def eliminaProva(codEsame, codProva):
    docente = current_user
    prova_to_delete = Prove.query.get(codProva)
    owner_prova = Docenti.query.get(prova_to_delete.docente)
    #Controllo che NON esista nessun appello relativo a nessuna prova relativa al corso.
    esame = Esami.query.get(codEsame)
    esiste_appello_esame = any(prova.appelli for prova in esame.prove)

    if owner_prova == docente and not esiste_appello_esame:
        print("Puoi eliminare questa prova")
        db.session.delete(prova_to_delete)
        db.session.commit()
    else:
        print("Non puoi eliminare questa prova")
    return redirect(url_for('teacher.visualizzaProve', codEsame=codEsame))


@teacher.route('/visualizzaCorsi/visualizzaProve/definisciAppello/<codProva>', methods=['POST', 'GET'])
@login_required
@checkDocente
def definisciAppello(codProva):
    print("sono in definisciAppello")
    isAbilitata = False   #una prova è abilitata quando la somma dei pesi delle prove abilitate per un corso è 1
    prova = Prove.query.get(codProva)
    esame = prova.esami
    codEsame = esame.cod
    pesoTot = 0
    for prova in esame.prove:
        pesoTot = pesoTot + prova.peso
    if pesoTot == 1:
        isAbilitata = True

    if isAbilitata or prova.idoneità == True:
        # crea un appello per una prova
        prova = Prove.query.get(codProva)
        return render_template('teacher/definisciAppello.html', user=current_user, prove=current_user.prove,
                               codEsame = codEsame, codProva=codProva)
    else:
        return redirect(url_for('teacher.visualizzaProve', codEsame=codEsame))


@teacher.route('/visualizzaCorsi/visualizzaProve/definisciAppello/<codProva>/creaAppello', methods=['POST', 'GET'])
@login_required
@checkDocente
def creaAppello(codProva):
    print("sono in creaAppello")
    #crea un appello per una prova
    #impedire la creazione di un appello per una prova il quale appello è definito per una certa distanza di data ?
    #bisognerebbe implementare delle politiche interne.
    prova_id = request.form['prova']
    luogo = request.form['luogo']
    data = request.form['data']
    print("prima di creare l'appello")
    print(Appelli.query.all())
    new_appello = Appelli(data=data, luogo=luogo, prova=codProva)
    db.session.add(new_appello)
    db.session.commit()
    print("dopo aver creato l'appello")
    print(Appelli.query.all())
    return redirect(url_for('teacher.teacherPage'))



#to do da implementare ancora def visualizzaAppelli.
@teacher.route('/visualizzaAppelli')
@login_required
@checkDocente
def visualizzaAppelli():
    print("sono in visualizzaAppelli")
    return render_template('teacher/visualizzaAppelli.html', docente=current_user)


@teacher.route('/visualizzaAppelli/studentiIscritti/<codAppello>', methods=['GET'])
@login_required
@checkDocente
def visualizzaStudentiIscritti(codAppello):
        studenti = Appelli.query.get(codAppello).studenti
        #gli studenti che hanno gia un voto devono comaparire con il voto settato.
        print("sono in visualizzaStudentiIscritti")
        appello = Appelli.query.get(codAppello)
        db_stamp = db.session.query(func.now()).scalar()
        appello_data_aware = appello.data.replace(tzinfo=UTC)
        is_appello_nel_passato = appello_data_aware < db_stamp
        return render_template('teacher/visualizzaStudentiIscritti.html', studenti=studenti, codAppello=codAppello,
                               is_appello_nel_passato=is_appello_nel_passato)


@teacher.route('/visualizzaAppelli/dettagliAppello/<codAppello>', methods=['GET'])
@login_required
@checkDocente
def visualizzaDettagliAppello(codAppello):

        return render_template('teacher/visualizzaDettagliAppello.html', appello=Appelli.query.get(codAppello))


@teacher.route('/visualizzaAppelli/studentiIscritti/setVoto', methods=['POST'])
@login_required
@checkDocente
def setVoto():
    if request.method == 'POST':
        voto = request.form['voto']
        studente_id = request.form['studente_id']
        codAppello = request.form['codAppello']

        current_user.set_voto_prova(studente_id, voto, codAppello)

    return redirect(url_for('teacher.visualizzaStudentiIscritti', codAppello=codAppello))


@teacher.route('/visualizzaAppelli/eliminaAppello', methods=['POST'])
@login_required
@checkDocente
def eliminaAppello():
    codAppello = request.form['codAppello']
    appello_to_delete = Appelli.query.get(codAppello)
    db.session.delete(appello_to_delete)
    db.session.commit()
    return redirect(url_for('teacher.visualizzaAppelli'))


@teacher.route('/visualizzaProveGestite')
@login_required
@checkDocente
def visualizzaProveGestite():
    print("sono in visualizzaProveGestite")
    print(current_user.prove)
    return render_template('teacher/visualizzaProveGestite.html', user=current_user, prove=current_user.prove,
                           esami=current_user.esami)

