import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import re

st.set_page_config(page_title="Prezzi Benzina", layout="wide")

def fetch_data(city, fuel):
    # Trasformiamo i nomi per l'URL
    fuel_url = {"Gasolio": "prezzo-diesel", "Benzina": "prezzo-benzina", "GPL": "prezzo-gpl"}[fuel]
    city_url = city.lower().replace(" ", "-")
    url = f"https://www.komparing.com/it/{fuel_url}/{city_url}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36",
        "Accept-Language": "it-IT,it;q=0.9"
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            return None, f"Sito non raggiungibile (Errore {response.status_code})"

        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Cerchiamo tutti i blocchi che contengono un prezzo (es. 1.745 o 1,745)
        results = []
        
        # Cerchiamo dentro le tabelle, che sono le più comuni
        for row in soup.find_all('tr'):
            text = row.get_text(" ", strip=True).replace(",", ".")
            # Cerchiamo un prezzo nel testo
            match = re.search(r'(\d\.\d{3})', text)
            if match:
                results.append({
                    "Prezzo": float(match.group(1)),
                    "Dettaglio": text.replace(match.group(1), "").strip()[:80]
                })

        # Se non ci sono tabelle, cerchiamo in ogni div della pagina
        if not results:
            for div in soup.find_all('div'):
                if len(div.text) < 150: # Evitiamo blocchi di testo enormi
                    text = div.get_text(" ", strip=True).replace(",", ".")
                    match = re.search(r'(\d\.\d{3})', text)
                    if match:
                        results.append({
                            "Prezzo": float(match.group(1)),
                            "Dettaglio": text.replace(match.group(1), "").strip()[:80]
                        })

        if results:
            df = pd.DataFrame(results).drop_duplicates().sort_values("Prezzo")
            return df, "OK"
        
        return None, "Il sito ha risposto, ma non sono stati trovati prezzi nella pagina."

    except Exception as e:
        return None, f"Errore di connessione: {e}"

# --- INTERFACCIA ---
st.title("⛽ Prezzi Carburante Online")

with st.sidebar:
    st.header("Ricerca")
    citta = st.text_input("Inserisci Città", "Caltanissetta")
    tipo = st.selectbox("Carburante", ["Gasolio", "Benzina", "GPL"])
    btn = st.button("Trova i prezzi più bassi")

if btn or citta:
    with st.spinner("Cerco i prezzi aggiornati..."):
        df, status = fetch_data(citta, tipo)
        
        if df is not None:
            st.subheader(f"Migliori prezzi per {tipo} a {citta}")
            
            # Griglia di card (stile app mobile)
            cols = st.columns(2)
            for i, (_, row) in enumerate(df.head(10).iterrows()):
                with cols[i % 2]:
                    st.markdown(f"""
                    <div style="background-color: white; padding: 15px; border-radius: 10px; 
                                border-left: 10px solid #28a745; margin-bottom: 10px; 
                                box-shadow: 2px 2px 5px rgba(0,0,0,0.1); display: flex; 
                                justify-content: space-between; align-items: center;">
                        <div style="color: #333; font-weight: bold; font-size: 0.9em;">
                            {row['Dettaglio']}
                        </div>
                        <div style="background: #28a745; color: white; padding: 5px 10px; 
                                    border-radius: 5px; font-weight: bold; font-size: 1.2em;">
                            {row['Prezzo']:.3f}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
        else:
            st.error(f"⚠️ Attenzione: {status}")
            st.warning("I server di questo sito potrebbero aver bloccato la richiesta automatica.")
            st.info("💡 Suggerimento: Prova a scrivere una città diversa (es: Roma o Milano) per vedere se il servizio risponde.")
