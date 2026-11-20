# CalcioZone · Football AI Studio

Prima versione web brandizzata CalcioZone: prepara copioni calcistici e crea MP4 verticali con voce italiana.

## Avvio locale
1. Installa Python 3.10 o superiore.
2. Estrai lo ZIP.
3. Nel terminale, entra nella cartella ed esegui:
   `pip install -r requirements.txt`
4. Avvia:
   `streamlit run app.py`

Si apre una pagina web; puoi usarla anche dal browser del telefono se PC e telefono sono sulla stessa rete e avvii Streamlit con `--server.address 0.0.0.0`.

## Pubblicazione online
Puoi caricare `app.py` e `requirements.txt` su un repository GitHub e collegarlo a Streamlit Community Cloud. Per la generazione AI, inserisci la chiave OpenAI nel campo della sidebar. Non pubblicare mai la chiave nel repository.

## Limiti della versione iniziale
- Senza chiave OpenAI produce copioni modello/evergreen; con chiave genera copioni AI.
- La voce usa gTTS (qualità base, richiede internet).
- Il video è una scheda grafica verticale con voce, non un montaggio automatico di highlights o filmati di partita.
- Le notizie recenti vanno verificate manualmente prima della pubblicazione.
- Nessuna pubblicazione automatica su TikTok o YouTube in questa versione.
- Usa solo immagini e audio originali o con licenza.
