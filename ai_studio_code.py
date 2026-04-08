import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import folium
from streamlit_folium import st_folium
import re

st.set_page_config(page_title="Prezzi Benzina", layout="wide")

def scrape_komparing(city, fuel_type):
    fuel_map = {
        "Benzina": "prezzo-benzina", 
        "Gasolio": "prezzo-diesel", 
        "GPL": "prezzo-gpl", 
        "Metano": "prezzo-metano"
    }
    
    # Pulizia nome città per l'URL
    city_slug = city.lower().strip().replace(" ", "-")
    url = f"https://www.komparing.com/it/{fuel_map[fuel_type]}/{city_slug}"
    
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code != 200:
            return None
        
        soup = BeautifulSoup(response.text, 'html.parser')
        stations = []

        # Cerchiamo tutte le righe della tabella (metodo più comune sui siti di prezzi)
        rows = soup.find_all('tr')
        
        for row in rows:
            cols = row.find_all('td')
            if len(cols) >= 2:
                try:
                    # Il prezzo di solito è nella seconda o terza colonna
                    text_content = row.get_text("|", strip=True).replace(",", ".")
                    # Cerchiamo un numero tipo 1.849 o 2.012
                    match_price = re.search(r'(\d\.\d{3})', text_content)
                    
                    if match_price:
                        price = float(match_price.group(1))
                        # Il nome/indirizzo è solitamente il primo testo lungo
                        info = cols[0].get_text(" ", strip=True)
                        
                        stations.append({
                            "Prezzo": price,
                            "Info": info,
                            "lat": 0.0, "lon": 0.0 # Placeholder
                        })
                except:
                    continue

        # Se non troviamo nulla in tabella, proviamo i blocchi 'div'
        if not stations:
            items = soup.find_all(['div', 'li'], class_=re.compile(r'item|station|distributore'))
            for item in items:
                text = item.get_text(" ", strip=True).replace(",", ".")
                price_match = re.search(r'(\d\.\d{3})', text)
                if price_match:
                    stations.append({
                        "Prezzo": float(price_match.group(1)),
                        "Info": text[:100], # Prendi i primi 100 caratteri come info
                        "lat": 0.0, "lon": 0.0
                    })
        
        return stations
    except:
        return None

# --- UI APP ---
st.markdown(f"<h1 style='text-align: center;'>⛽ Prezzi {st.sidebar.selectbox('Carburante', ['Gasolio', 'Benzina', 'GPL', 'Metano'], key='fuel_sel')} a {st.sidebar.text_input('Città', 'Caltanissetta', key='city_sel')}</h1>", unsafe_allow_html=True)

data = scrape_komparing(st.session_state.city_sel, st.session_state.fuel_sel)

if data:
    df = pd.DataFrame(data).sort_values('Prezzo')
    
    col_list, col_info = st.columns([1, 1])
    
    with col_list:
        st.subheader("Classifica Prezzi")
        for _, row in df.iterrows():
            # Dividiamo l'info in Indirizzo e Marchio (approssimativo)
            parti = row['Info'].split('|')
            indirizzo = parti[0] if len(parti) > 0 else row['Info']
            
            st.markdown(f"""
            <div style="display: flex; justify-content: space-between; align-items: center; 
                        background: white; padding: 15px; border-radius: 8px; 
                        border-left: 8px solid #28a745; margin-bottom: 12px; 
                        box-shadow: 0 4px 6px rgba(0,0,0,0.1); border: 1px solid #eee;">
                <div style="flex-grow: 1; padding-right: 10px;">
                    <b style="color: #0056b3; font-size: 1em; text-transform: uppercase;">{indirizzo[:50]}</b><br>
                    <span style="color: #555; font-size: 0.85em;">Distributore in zona</span>
                </div>
                <div style="background: #28a745; color: white; padding: 10px 20px; 
                            border-radius: 6px; font-weight: bold; font-size: 1.3em; min-width: 80px; text-align: center;">
                    {row['Prezzo']:.3f}
                </div>
            </div>
            """, unsafe_allow_html=True)
            
    with col_info:
        st.info("💡 Suggerimento: I prezzi mostrati sono i più bassi rilevati oggi per la città selezionata.")
        st.warning("⚠️ Nota: Alcuni siti bloccano l'accesso alle mappe per le app esterne. Se non vedi la mappa, usa la lista per trovare l'indirizzo.")
        
        # Un'immagine di placeholder per rendere l'app più bella
        st.image("https://images.unsplash.com/photo-1545142851-561c2834b6e5?auto=format&fit=crop&w=800&q=60", caption="Cerca il risparmio al distributore")

else:
    st.error("⚠️ Nessun dato trovato. Possibili motivi:")
    st.write("1. Il nome della città è scritto male (es. usa 'Roma' non 'rm').")
    st.write("2. Il sito Komparing sta bloccando la richiesta in questo momento.")
    st.write("3. Non ci sono dati aggiornati per questa combinazione città/carburante.")
