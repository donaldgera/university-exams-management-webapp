from dotenv import load_dotenv
from App import create_app

load_dotenv()  # carico le variabili d'ambiente

app = create_app()  # creo l'applicazione con la funzione create_app() definita in _init_.py