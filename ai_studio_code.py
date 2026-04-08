import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import re

# Configurazione Pagina
st.set_page_config(page_title="Prezzi Benzina & Diesel", layout="wide")

def get_fuel_data(city, fuel_type):
    # Mapping carburante per l'URL
    fuel_map = {
        "Gasolio": "prezzo-diesel",
        "Benzina": "prezzo-benzina",
        "GPL": "prezzo-gpl",
        "Metano": "prezzo-metano"
    }
    
    city_slug = city.lower().strip().replace(" ", "-")
    url = f"https://www.komparing.com/it/{fuel_map[fuel_type]}/{city_slug}"
    
    # Header più "umani" per evitare blocchi
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7",
        "Referer": "https://www.google.com/"
    }

    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code != 200:
            return None, f"Errore Sito: {response.status_code}"

        soup = BeautifulSoup(response.text, 'html.parser')
        stations = []

        # --- STRATEGIA 1: Cerca tabelle ---
        for row in soup.find_all('tr'):
            cells = row.find_all('td')
            if len(cells) >= 2:
                text = row.get_text(" ", strip=True).replace(",", ".")
                # Cerca il prezzo (formato X.XXX)
                price_match = re.search(r'(\d\.\d{3})', text)
                if price_match:
                    stations.append({
                        "Prezzo": float(price_match.group(1)),
                        "Nome": cells[0].get_text(" ", strip=True)[:60],
                        "Indirizzo": cells[1].get_text(" ", strip=True) if len(cells) > 2 else ""
                    })

        # --- STRATEGIA 2: Cerca blocchi div (se la tabella fallisce) ---
        if not stations:
            # Cerchiamo blocchi che contengono prezzi
            for div in soup.find_all(['div', 'li']):
                text = div.get_text(" ", strip=True).replace(",", ".")
                price_match = re.search(r'(\d\.\d{3})', text)
                if price_match and len(text) < 200: # Evitiamo blocchi troppo grandi
                    stations.append({
                        "Prezzo": float(price_match.group(1)),
                        "Nome": text.split(price_match.group(1))[0].strip()[:50],
                        "Indirizzo": "Dettaglio nel sito"
                    })

        # Rimuove duplicati e ordina
        if stations:
            df = pd.DataFrame(stations).drop_duplicates(subset=['Prezzo', 'Nome']).sort_values('Prezzo')
            return df, "OK"
        
        return None, "Nessun distributore trovato nella pagina."

    except Exception as e:
        return None, str(e)

# --- INTERFACCIA UTENTE ---
st.markdown(f"<h1 style='color: #0056b3; text-align: center;'>⛽ Monitor Prezzi Carburante</h1>", unsafe_allow_html=True)

# Sidebar per i controlli
with st.sidebar:
    st.header("Ricerca")
    citta_scelta = st.text_input("Città", "Caltanissetta")
    carburante_scelto = st.selectbox("Carburante", ["Gasolio", "Benzina", "GPL", "Metano"])
    tasto_cerca = st.button("Aggiorna Prezzi")

if tasto_cerca or citta_scelta:
    with st.spinner(f"Scansione prezzi per {citta_scelta}..."):
        df, status = get_fuel_data(citta_scelta, carburante_scelto)
        
        if df is not None:
            st.subheader(f"Risultati per {carburante_scelto} a {citta_scelta}")
            
            # Layout a griglia per i prezzi (simile allo screenshot)
            cols = st.columns(2)
            for i, (_, row) in enumerate(df.head(12).iterrows()):
                target_col = cols[i % 2]
                with target_col:
                    st.markdown(f"""
                    <div style="background: white; padding: 15px; border-radius: 10px; 
                                border-left: 10px solid #28a745; margin-bottom: 15px; 
                                box-shadow: 0 4px 6px rgba(0,0,0,0.1); display: flex; 
                                justify-content: space-between; align-items: center;">
                        <div style="flex: 1;">
                            <b style="font-size: 1.1em; color: #333;">{row['Nome']}</b><br>
                            <span style="font-size: 0.8em; color: #666;">{row['Indirizzo']}</span>
                        </div>
                        <div style="background: #28a745; color: white; padding: 8px 15px; 
                                    border-radius: 5px; font-weight: bold; font-size: 1.4em;">
                            {row['Prezzo']:.3f}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
            
            st.success(f"Trovati {len(df)} distributori.")
        else:
            st.error(f"⚠️ Impossibile recuperare i dati: {status}")
            st.info("Prova a cercare una città più grande o controlla se il nome è corretto.")

st.markdown("---")
st.caption("Dati estratti a scopo dimostrativo. Verifica sempre i prezzi al distributore.")
