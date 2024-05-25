from flask_sqlalchemy.session import Session
from sqlalchemy import text

from App.utils.utilies import set_voto
from main import app
from App.db.models.database import Studenti, Docenti, Esami, db, Prove, Appelli, iscrizioni, Superamenti, \
    formalizzazioneEsami, Admin

query = Session(db)

def add(obj):
    db.session.add(obj)
    db.session.commit()


def create_admin():
    admin = Admin(name='main', surname='admin', password='12345678')
    add(admin)
def create_trigger():
    # Comando SQL per creare il trigger PostgreSQL
    create_trigger_sql = """
        CREATE TRIGGER invalidate_trial 
        BEFORE INSERT ON Iscrizioni 
        FOR EACH ROW 
        EXECUTE FUNCTION invalidate_trial_function(); 
    """

    # Comando SQL per creare la funzione PostgreSQL
    create_function_sql = """
        CREATE OR REPLACE FUNCTION invalidate_trial_function() RETURNS TRIGGER AS $$ 
        BEGIN
            UPDATE Iscrizioni 
            SET "isValid" = FALSE 
            WHERE studente = new.studente 
            AND appello IN (
                SELECT Appelli."codAppello"
                FROM Appelli JOIN Iscrizioni ON  Appelli."codAppello" = appello
                WHERE Iscrizioni."isValid" = TRUE 
                AND Iscrizioni."voto" >= 18 
                AND prova IN (
                    SELECT prova 
                    FROM Appelli 
                    WHERE Appelli."codAppello" = new.appello
                )
            );
            RETURN NEW;
        END; 
        $$ LANGUAGE plpgsql;"""

    create_trigger_sql2= """
        CREATE TRIGGER invalidate_exam_cascade
        BEFORE UPDATE ON Iscrizioni 
        FOR EACH ROW 
        WHEN (new."isValid" = FALSE)
        EXECUTE FUNCTION invalidate_exam_cascade_function(); """

    create_function_sql2 = """
        CREATE OR REPLACE FUNCTION invalidate_exam_cascade_function() RETURNS TRIGGER AS $$ 
        BEGIN
            -- Rimozione dell'esame che era formalizzabile, in quanto una prova che lo costituiva non è più valida
            UPDATE "formalizzazioneEsami"	
            SET "passato" = FALSE 		 
            WHERE studente = new.studente 
            AND passato = TRUE 
            AND "formalizzazioneEsami".esame IN (
                SELECT esame 
                FROM appelli JOIN prove ON  appelli."prova" = prove."cod"
                WHERE appelli."codAppello" = new.appello
            ); 

            -- Gestione invalida prove che richiedevano una prova che è stata invalidata, produce ricorsione di chiamate 
            UPDATE Iscrizioni
            SET "isValid" = FALSE
            WHERE studente = new.studente AND "isValid" = TRUE 
            AND appello IN (
                SELECT appelli."codAppello"
                FROM Appelli 
                WHERE prova IN (
                    SELECT superamenti."provaSuccessiva"
                    FROM Superamenti JOIN Appelli ON prova = superamenti."provaPrimaria"
                    WHERE appelli."codAppello" = NEW.appello
                )
            );	 
            RETURN NEW; 
        END; 
        $$ LANGUAGE plpgsql;
    """

    create_trigger_sql3 = """ CREATE TRIGGER check_if_other_tests_are_required 
                                BEFORE INSERT ON Iscrizioni 
                                FOR EACH ROW EXECUTE FUNCTION check_if_other_tests_are_required(); 
                                """


    create_function_sql3= """ CREATE OR REPLACE FUNCTION check_if_other_tests_are_required() RETURNS TRIGGER AS $$ 
                                BEGIN 
                                IF(
                                (SELECT COUNT(superamenti."provaPrimaria") FROM Superamenti WHERE superamenti."provaSuccessiva" IN (SELECT prova FROM Appelli WHERE appelli."codAppello" = NEW.appello)) != 
                                (SELECT COUNT(prova) FROM Appelli JOIN Iscrizioni ON appelli."codAppello" = appello WHERE studente = NEW.studente AND voto >= 18 AND iscrizioni."isValid" = TRUE AND prova IN
                                    (SELECT superamenti."provaPrimaria" FROM Superamenti WHERE superamenti."provaSuccessiva" IN    
                                                                                                (SELECT prova
                                                                                                 FROM Appelli 
                                                                                                 WHERE appelli."codAppello" = NEW.appello)
                                ))) THEN 
                                 RAISE EXCEPTION 'La condizione è stata soddisfatta per NEW.appello = % e NEW.studente = %', NEW.appello, NEW.studente;
                                RETURN NULL; 
                                END IF; 
                                 RETURN NEW;
                                END; 
                                $$ LANGUAGE plpgsql; """

    create_trigger_sql4 = """ CREATE TRIGGER set_final_score
                                AFTER UPDATE ON Iscrizioni
                                FOR EACH ROW
                                EXECUTE FUNCTION set_final_score_function();                          """

    create_function_sql4 = """CREATE OR REPLACE FUNCTION set_final_score_function() RETURNS TRIGGER AS $$ 
BEGIN 
    IF (
        (SELECT COUNT(prove."cod") 
        FROM Prove 
        WHERE esame IN (
            SELECT esame 
            FROM Appelli 
            JOIN Prove ON prova = prove."cod"
            WHERE appelli."codAppello" = new.appello
        ) AND (prove.idoneità = TRUE OR prove.peso != 0) ) =
        (SELECT COUNT(prove."cod") 
        FROM Appelli 
        JOIN Iscrizioni ON appelli."codAppello" = appello 
        JOIN Prove ON prova = prove."cod" 
        WHERE studente = new.studente
            AND voto >= 18 
            AND iscrizioni."isValid" = TRUE 
            AND esame IN (
                SELECT esame 
                FROM Appelli 
                JOIN Prove ON prova = prove."cod" 
                WHERE appelli."codAppello" = new.appello
            ) AND (prove.idoneità = TRUE OR prove.peso != 0)
        )
    )
     THEN
        UPDATE "formalizzazioneEsami"
        SET "voto" = (
            SELECT SUM(( CASE WHEN voto = NULL THEN 0 ELSE voto END ) *
                    peso + ( CASE WHEN prove."Bonus" = NULL THEN 0 ELSE prove."Bonus" END )) 
            FROM (Iscrizioni 
            JOIN Appelli ON appello = appelli."codAppello" ) JOIN Prove ON prova = prove."cod"
            WHERE studente = NEW.studente 
                AND voto >= 18 
                AND iscrizioni."isValid" = TRUE 
                AND prova IN (
                    SELECT prove."cod" 
                    FROM Prove 
                    WHERE esame IN (
                        SELECT esame 
                        FROM Appelli 
                        JOIN Prove ON prova = prove."cod" 
                        WHERE NEW.appello = appelli."codAppello"
                    )
                )
        ),
        passato = TRUE
        WHERE studente = NEW.studente 
            AND esame IN (
                SELECT esame 
                FROM Appelli 
                JOIN Prove ON prova = prove."cod" 
                WHERE NEW.appello = appelli."codAppello"
            );
    END IF; 
    RETURN NULL;
END; 
$$ LANGUAGE plpgsql;                  """

    # Esegui i comandi SQL per creare il trigger e la funzione

    with db.engine.connect() as conn:
        # Ottieni una connessione al database
        conn = db.session.connection()

        # Esegui i comandi SQL per creare il trigger e la funzione
        conn.execute(text(create_function_sql))
        conn.execute(text(create_function_sql2))
        conn.execute(text(create_function_sql3))
        conn.execute(text(create_function_sql4))
        conn.execute(text(create_trigger_sql))
        conn.execute(text(create_trigger_sql2))
        conn.execute(text(create_trigger_sql3))
        conn.execute(text(create_trigger_sql4))



    db.session.commit()

        # Chiamata alla funzione per creare il trigger e la funzione


def creates_students():
    domenico_sosta = Studenti(name='Domenico', surname='Sosta', matricola=892075, password='12345678', phone='3479145154')
    add(domenico_sosta)
    luca_bianchi = Studenti(name='Luca', surname='Bianchi', matricola=892076, password='12345678', phone='3479145152')
    add(luca_bianchi)
    mario_rossi = Studenti(name='Mario', surname='Rossi', matricola=892077, password='12345678', phone='3479145153')
    add(mario_rossi)
    giusy_verdi = Studenti(name='Giusy', surname='Verdi', matricola=892078, password='12345678', phone='3479145155')
    add(giusy_verdi)

    return domenico_sosta, luca_bianchi, mario_rossi, giusy_verdi



def creat_exam_and_teacher():
    pietro_ferrara = Docenti(name='Pietro', surname='Ferrara', password='12345678')
    alvise_spano = Docenti(name='Alvise', surname='Spano', password='12345678')
    stefano_calzavara = Docenti(name='Stefano', surname='Calzavara', password='12345678')
    alessandra_raffaeta = Docenti(name='Alessandra', surname='Raffaeta', password='12345678')
    claudio_lucchese = Docenti(name='Claudio', surname='Lucchese', password='12345678')
    andrea_marin = Docenti(name='Andrea', surname='Marin', password='12345678')
    riccardo_focardi = Docenti(name='Riccardo', surname='Focardi', password='12345678')
    simonetta_balsamo = Docenti(name='Simonetta', surname='Balsamo', password='12345678')
    marcello_pelillo = Docenti(name='Marcello', surname='Pelillo', password='12345678')
    simeoni_marta = Docenti(name='Marta', surname='Simeoni', password='12345678')
    bergamasco_filippo = Docenti(name='Filippo', surname='Bergamasco', password='12345678')
    cristiana_pagliarusco = Docenti(name='Cristiana', surname='Pagliarusco', password='12345678')
    isadora_antoniano = Docenti(name='Isadora', surname='Antoniano', password='12345678')
    damiano_pasetto = Docenti(name='Damiano', surname='Pasetto', password='12345678')

    PO = Esami(name='Programmazione ad Oggetti', cod='01QWERTY', cfu=12, anno=2)
    add(PO)
    add(pietro_ferrara)
    add(alvise_spano)
    pietro_ferrara.esami.append(PO)
    alvise_spano.esami.append(PO)
    BD = Esami(name='Basi di dati', cod='02QWERTY', cfu=12, anno=2)
    add(BD)
    add(stefano_calzavara)
    stefano_calzavara.esami.append(BD)
    SO = Esami(name='Sistemi operativi', cod='03QWERTY', cfu=12, anno=2)
    add(SO)
    add(simonetta_balsamo)
    add(riccardo_focardi)
    simonetta_balsamo.esami.append(SO)
    riccardo_focardi.esami.append(SO)
    PL = Esami(name='Programmazione e Laboratorio', cod='04QWERTY', cfu=12, anno=1)
    add(PL)
    add(andrea_marin)
    andrea_marin.esami.append(PL)
    ASD = Esami(name='Algoritmi e Strutture Dati', cod='05QWERTY', cfu=12, anno=2)
    add(ASD)
    add(alessandra_raffaeta)
    add(marcello_pelillo)
    alessandra_raffaeta.esami.append(ASD)
    marcello_pelillo.esami.append(ASD)
    RC = Esami(name='Reti di Calcolatori', cod='06QWERTY', cfu=12, anno=3)
    add(RC)
    add(simonetta_balsamo)
    simonetta_balsamo.esami.append(RC)
    IAP = Esami(name='Introduzione alla programmazione', cod='07QWERTY', cfu=6, anno=1)
    DWM = Esami(name='Data and Web Mining', cod='08QWERTY', cfu=6, anno=3)
    add(IAP)
    add(DWM)
    add(claudio_lucchese)
    claudio_lucchese.esami.append(IAP)
    claudio_lucchese.esami.append(DWM)
    ADE = Esami(name='Architettura degli Elaboratori', cod='09QWERTY', cfu=12, anno=1)
    add(ADE)
    add(simeoni_marta)
    simeoni_marta.esami.append(ADE)
    ENG = Esami(name='Lingua Inglese', cod='10QWERTY', cfu=3, anno=1)
    add(ENG)
    add(cristiana_pagliarusco)
    cristiana_pagliarusco.esami.append(ENG)
    PES = Esami(name='Probabilità e Statistica', cod='11QWERTY', cfu=12, anno=2)
    add(PES)
    add(isadora_antoniano)
    isadora_antoniano.esami.append(PES)
    CL1 = Esami(name='Calcolo 1', cod='12QWERTY', cfu=6, anno=1)
    CL2 = Esami(name='Calcolo 2', cod='13QWERTY', cfu=6, anno=1)
    add(CL1)
    add(CL2)
    add(damiano_pasetto)
    damiano_pasetto.esami.append(CL1)
    damiano_pasetto.esami.append(CL2)
    CLF = Esami(name='Calcolabilità e Linguaggi Formali', cod='014QWERTY', cfu=6, anno=3)
    add(CLF)
    stefano_calzavara.esami.append(CLF)
    add(bergamasco_filippo)
    alvise_spano.esami.append(IAP)
    alessandra_raffaeta.esami.append(BD)

    obj = {}
    for docente in Docenti.query.all():
        obj[docente.email] = docente.cod
    return obj



def create_test(dict_docenti):
    ferrara_cod = dict_docenti['pietro.ferrara@unive.it']
    calzavara_cod = dict_docenti['stefano.calzavara@unive.it']
    focardi_cod = dict_docenti['riccardo.focardi@unive.it']
    marin_cod = dict_docenti['andrea.marin@unive.it']
    raffaeta_cod = dict_docenti['alessandra.raffaeta@unive.it']
    spano_cod = dict_docenti['alvise.spano@unive.it']
    balsamo_cod = dict_docenti['simonetta.balsamo@unive.it']
    pelillo_cod = dict_docenti['marcello.pelillo@unive.it']
    lucchese_cod = dict_docenti['claudio.lucchese@unive.it']
    isadora = Docenti.query.filter_by(email = 'isadora.antoniano@unive.it').first()
    cristiana_pagliarusco = Docenti.query.filter_by(email = 'cristiana.pagliarusco@unive.it').first()

    add(Prove(esame='01QWERTY', docente=ferrara_cod, peso=0.5, cod='PO1',  Tipologia='Scritto'))
    add(Prove(esame='01QWERTY', docente=spano_cod, peso=0.5, cod='PO2',Tipologia='Scritto'))

    add(Prove(esame='02QWERTY', docente=raffaeta_cod, peso=0.5, cod='BD1', Tipologia='Scritto'))
    add(Prove(esame='02QWERTY', docente=calzavara_cod, peso=0.3, cod='BD2', Tipologia='Scritto'))
    add(Prove(esame='02QWERTY', docente=calzavara_cod, peso=0.2,  cod='BDProject', Tipologia='Progetto'))

    add(Prove(esame='03QWERTY', docente=balsamo_cod, peso=0.5,  cod='SO1', Tipologia='Scritto'))
    add(Prove(esame='03QWERTY', docente=focardi_cod, peso=0.5,  cod='SO2', Tipologia='Scritto'))

    add(Prove(esame='04QWERTY', docente=marin_cod, peso=0.5,  cod='PL1', Tipologia='Scritto'))
    add(Prove(esame='04QWERTY', docente=marin_cod, peso=0.5, cod='PL2', Tipologia='Orale'))

    add(Prove(esame='05QWERTY', docente=raffaeta_cod, peso=0.5, cod='ASD1', Tipologia='Scritto'))
    add(Prove(esame='05QWERTY', docente=pelillo_cod, peso=0.5, cod='ASD2', Tipologia='Scritto'))

    add(Prove(esame='06QWERTY', docente=balsamo_cod, peso=1.0, cod='RC1', Tipologia='Scritto'))

    add(Prove(esame='07QWERTY', docente=lucchese_cod, peso=1.0, cod='IAP', Tipologia='Scritto'))

    add(Prove(esame='11QWERTY', docente=isadora.cod, peso=1.0, cod='PES', Tipologia='Scritto'))
    add(Prove(esame='11QWERTY', docente=isadora.cod, peso=0.0, Bonus=1, cod='Esercitazione-1', Tipologia='Scritto'))

    add(Prove(esame='10QWERTY', docente=cristiana_pagliarusco.cod, peso=0.0, cod='ENG', Tipologia='Scritto'))

def create_appelli():

    add(Appelli(data='2023-01-10 12:00:00', luogo='Aula1', prova='PO1'))
    add(Appelli(data='2023-01-10', luogo='Aula2', prova='PO2'))

    add(Appelli(data='2023-01-15', luogo='Aula1', prova='BD1'))
    add(Appelli(data='2023-01-15', luogo='Aula2', prova='BD2'))

    add(Appelli(data='2023-01-20', luogo='Aula1', prova='SO1'))
    add(Appelli(data='2023-01-20', luogo='Aula2', prova='SO2'))

    add(Appelli(data='2023-01-25', luogo='Aula1', prova='PL1'))
    add(Appelli(data='2023-01-25', luogo='Aula2', prova='PL2'))

    add(Appelli(data='2023-01-30', luogo='Aula1', prova='ASD1'))
    add(Appelli(data='2023-01-30', luogo='Aula2', prova='ASD2'))


    add(Appelli(data='2024-01-01', luogo='Aula1', prova='PO1'))
    add(Appelli(data='2024-01-01', luogo='Aula2', prova='PO2'))

    add(Appelli(data='2024-01-05', luogo='Aula1', prova='BD1'))
    add(Appelli(data='2024-01-05', luogo='Aula2', prova='BD2'))

    add(Appelli(data='2024-01-10', luogo='Aula1', prova='SO1'))
    add(Appelli(data='2024-01-10', luogo='Aula2', prova='SO2'))

    add(Appelli(data='2024-01-15', luogo='Aula1', prova='PL1'))
    add(Appelli(data='2024-01-15', luogo='Aula2', prova='PL2'))

    add(Appelli(data='2024-01-20', luogo='Aula1', prova='ASD1'))
    add(Appelli(data='2024-01-20', luogo='Aula2', prova='ASD2'))

    add(Appelli(data='2024-01-25', luogo='Aula1', prova='RC1'))

    add(Appelli(data='2024-01-19', luogo='Aula1', prova='IAP'))

    add(Appelli(data='2023-09-19', luogo='Aula1', prova='BD1'))
    add(Appelli(data='2023-09-19', luogo='Aula2', prova='BD2'))
    add(Appelli(data='2023-09-19', luogo='Aula3', prova='BDProject'))

    add(Appelli(data='2023-09-11', luogo='Aula1', prova='IAP'))

    add(Appelli(data='2023-09-11', luogo='Aula1', prova='PES'))
    add(Appelli(data='2023-02-11', luogo='Aula1', prova='Esercitazione-1'))

    add(Appelli(data='2023-09-11', luogo='Aula1', prova='ENG'))




def create_superamento():
    add(Superamenti(provaPrimaria='PO1', provaSuccessiva='PO2'))
    add(Superamenti(provaPrimaria='BD1', provaSuccessiva='BD2'))
    add(Superamenti(provaPrimaria='BD2', provaSuccessiva='BDProject'))
    add(Superamenti(provaPrimaria='SO1', provaSuccessiva='SO2'))
    add(Superamenti(provaPrimaria='PL1', provaSuccessiva='PL2'))
    add(Superamenti(provaPrimaria='ASD1', provaSuccessiva='ASD2'))


def create_iscrizioni():
    raffaeta = Docenti.query.filter_by(email = 'alessandra.raffaeta@unive.it').first()
    calza = Docenti.query.filter_by(email = 'stefano.calzavara@unive.it').first()
    ferrara = Docenti.query.filter_by(email = 'pietro.ferrara@unive.it').first()
    studenti = db.session.query(Studenti).filter().all()
    appello1 = db.session.get(Appelli, '1') #appello di po1
    appello2 = db.session.get(Appelli,'2') #appello di po2
    appello23 = db.session.get(Appelli,'23')#appeello di bd1
    appello9 = db.session.get(Appelli,'9') #appello di asd1
    appello24 = db.session.get(Appelli,'24') #appello di bd2
    appello25 = db.session.get(Appelli,'25') #appello di iap
    appello26 = db.session.get(Appelli,'26') #appello di bdproject
    appello27 = db.session.get(Appelli,'27') #appello di pes
    appello28 = db.session.get(Appelli,'28') #appello di esercitazione-1 per pes
    appello29 = db.session.get(Appelli,'29') #appello di eng
    for studente in studenti:

        studente.appelli.append(appello1)
        studente.appelli.append(appello23)
        studente.appelli.append(appello29)
        db.session.commit()
        raffaeta.set_voto_prova(studente.matricola, 26, '23')
        ferrara.set_voto_prova(studente.matricola, 26, '1')
        studente.appelli.append(appello9)
        studente.appelli.append(appello24)
        studente.appelli.append(appello2)
        db.session.commit()
        calza.set_voto_prova(studente.matricola, 24, '24')
        studente.appelli.append(appello25)
        studente.appelli.append(appello26)
        studente.appelli.append(appello27)
        studente.appelli.append(appello28)
    db.session.commit()


def create_piano_studi():
    studenti = db.session.query(Studenti).filter().all()
    esami = db.session.query(Esami).filter().all()
    for studente in studenti:
        for esame in esami:
            studente.esami.append(esame)
    db.session.commit()

def create_formalizzato():
    #attenzione!!! prima di aggiungere il voto ad una esame bisognerebbe calcolarlo in base alle prove relative a tale esame!!
    #Questa funzione serviva per testare la funzione di formalizzazione
    #list_studenti = db.session.query(Studenti).filter().all()
    #studente = list_studenti[0]
    #set_voto(studente.matricola, 18, '01QWERTY')
    #set_voto(studente.matricola, 29, '02QWERTY')
    #set_voto(studente.matricola, 26, '03QWERTY')
    #studente = list_studenti[1]
    #set_voto(studente.matricola, 18, '01QWERTY')
    #set_voto(studente.matricola, 29, '02QWERTY')
    #set_voto(studente.matricola, 26, '03QWERTY')

    #set_voto(892075, 18, '04QWERTY')
    #set_voto(892075, 25, '05QWERTY')
    pass


def init_db():
    print("Creating DB")
    db.create_all()

    print("DB created")

    create_admin()
    print("Admin creato")

    create_trigger()
    print("Trigger creati")

    list_docenti = creat_exam_and_teacher()
    print("Docenti ed esami creati")
    create_test(list_docenti)
    print("prove create")
    create_superamento()
    print("Superamenti creati")
    creates_students()
    print("Studenti creati")
    create_appelli()
    print("Appelli creati")
    create_iscrizioni()
    print("Iscrizioni create")
    create_piano_studi()
    print("Piano di studi creato")
    create_formalizzato()
    print("Formalizzato creato")


    db.session.commit()

def delete_db():
    with app.app_context():
        # Elimina tutti i dati dal database
        db.drop_all()

        # Elimina i ruoli
        sql_statements = [
            "DROP ROLE IF EXISTS Utente;",
            "DROP ROLE IF EXISTS Studente;",
            "DROP ROLE IF EXISTS Docente;",
        ]

        try:
            with db.engine.begin() as conn:
                for statement in sql_statements:
                    conn.execute(text(statement))
            print("Ruoli eliminati con successo.")
        except Exception as e:
            print(f"Errore nell'eliminazione dei ruoli: {e}")

        # Conferma le modifiche al database
        db.session.commit()

    print("DB deleted")

# Esegui la funzione delete_db()
delete_db()



with app.app_context():
    delete_db()
    init_db()
    print("DB created")

    def create_roles():
        sql_statements = [
            """
            CREATE ROLE Utente NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOREPLICATION LOGIN PASSWORD '0';
            """,
            """
            CREATE ROLE Studente NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOREPLICATION LOGIN PASSWORD '1';

            """,
            """
            CREATE ROLE Docente NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOREPLICATION LOGIN PASSWORD '2';
            """
        ]
        sql_statements_grant = [""" GRANT SELECT ON TABLE "public".docenti TO utente;
            GRANT SELECT ON TABLE "public".studenti TO utente;
        """,
                                """
                                  GRANT SELECT ON TABLE "public".esami TO studente;
                                     GRANT SELECT ON TABLE "public".prove TO studente;
                                     GRANT SELECT ON TABLE "public".appelli TO studente;
                                     GRANT SELECT ON TABLE "public".studenti TO studente;
                                     GRANT SELECT ON TABLE "public".docenti TO studente;
                                     GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE "public".iscrizioni TO studente;
                                     GRANT SELECT, UPDATE ON TABLE public."formalizzazioneEsami" TO studente;
                                     GRANT SELECT ON TABLE "public".superamenti TO studente;
                                 """,
                                """ 
                                 GRANT SELECT ON TABLE "public".esami TO docente;
                                     GRANT SELECT, INSERT, DELETE ON TABLE "public".prove TO docente;
                                     GRANT SELECT, INSERT, DELETE, UPDATE ON TABLE "public".appelli TO docente;
                                     GRANT SELECT ON TABLE "public".studenti TO docente;
                                     GRANT SELECT ON TABLE "public".docenti TO docente;
                                     GRANT SELECT ON TABLE "public".iscrizioni TO docente;
                                     GRANT SELECT, UPDATE ON TABLE public."formalizzazioneEsami" TO docente;
                                     GRANT SELECT, INSERT, DELETE ON TABLE "public".superamenti TO docente;
                                 """]

        try:
            with app.app_context():
                with db.engine.begin() as conn:
                    for statement in sql_statements:
                        conn.execute(text(statement))
                    for statement in sql_statements_grant:
                        conn.execute(text(statement))
                print("Roles created successfully.")
        except Exception as e:
            print(f"Error creating roles: {e}")


    # Chiamare la funzione per creare i ruoli
    create_roles()


