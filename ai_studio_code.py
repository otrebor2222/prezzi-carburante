import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import folium
from streamlit_folium import st_folium
import re

st.set_page_config(page_title="Confronto Prezzi Carburante", layout="wide")

# Funzione per estrarre i dati da Komparing
def scrape_komparing(city, fuel_type):
    fuel_map = {"Benzina": "prezzo-benzina", "Gasolio": "prezzo-diesel", "GPL": "prezzo-gpl", "Metano": "prezzo-metano"}
    city_slug = city.lower().replace(" ", "-")
    url = f"https://www.komparing.com/it/{fuel_map[fuel_type]}/{city_slug}"
    
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    
    try:
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            return None
        
        soup = BeautifulSoup(response.text, 'html.parser')
        stations = []
        
        # Cerchiamo i blocchi dei distributori (basato sulla struttura di Komparing)
        items = soup.find_all('div', class_='list-item') 
        
        for item in items:
            try:
                # Estrazione Prezzo
                price_tag = item.find('div', class_='price')
                price = price_tag.text.strip().replace('€', '').replace(',', '.') if price_tag else "0"
                
                # Estrazione Nome e Indirizzo
                name_tag = item.find('div', class_='name')
                name = name_tag.text.strip() if name_tag else "Distributore"
                
                address_tag = item.find('div', class_='address')
                address = address_tag.text.strip() if address_tag else ""
                
                # Estrazione Coordinate (spesso nei link o attributi)
                lat, lon = 0.0, 0.0
                link = item.find('a', href=True)
                if link:
                    # Cerchiamo coordinate nel link della mappa
                    coord_match = re.search(r'q=([-+]?\d*\.\d+|\d+),([-+]?\d*\.\d+|\d+)', link['href'])
                    if coord_match:
                        lat, lon = float(coord_match.group(1)), float(coord_match.group(2))

                stations.append({
                    "Prezzo": float(price),
                    "Marchio": name,
                    "Indirizzo": address,
                    "lat": lat,
                    "lon": lon
                })
            except:
                continue
        return stations
    except:
        return None

# --- INTERFACCIA APP ---
st.markdown(f"<h1 style='text-align: center;'>⛽ Prezzi Carburante a {st.session_state.get('city_input', 'Caltanissetta')}</h1>", unsafe_allow_html=True)

# Sidebar
st.sidebar.header("Ricerca")
city = st.sidebar.text_input("Città", "Caltanissetta")
fuel = st.sidebar.selectbox("Carburante", ["Benzina", "Gasolio", "GPL", "Metano"])
st.session_state['city_input'] = city

data = scrape_komparing(city, fuel)

if data:
    df = pd.DataFrame(data).sort_values('Prezzo')
    
    # Layout due colonne (come lo screenshot)
    col_list, col_map = st.columns([1, 1.5])
    
    with col_list:
        st.subheader("Lista Prezzi")
        for _, row in df.iterrows():
            # Box colorato per il prezzo
            st.markdown(f"""
            <div style="display: flex; justify-content: space-between; align-items: center; 
                        background: white; padding: 10px; border-radius: 5px; 
                        border-left: 10px solid #28a745; margin-bottom: 10px; 
                        box-shadow: 2px 2px 5px rgba(0,0,0,0.1);">
                <div style="flex-grow: 1;">
                    <b style="color: #0056b3; font-size: 0.9em; text-transform: uppercase;">{row['Indirizzo']}</b><br>
                    <span style="color: #666; font-size: 0.8em;">{row['Marchio']}</span>
                </div>
                <div style="background: #28a745; color: white; padding: 5px 15px; 
                            border-radius: 5px; font-weight: bold; font-size: 1.2em;">
                    {row['Prezzo']:.3f}
                </div>
            </div>
            """, unsafe_allow_html=True)

    with col_map:
        st.subheader("Mappa")
        # Filtriamo le stazioni che hanno le coordinate
        map_df = df[df['lat'] != 0]
        if not map_df.empty:
            m = folium.Map(location=[map_df['lat'].mean(), map_df['lon'].mean()], zoom_start=13)
            for _, r in map_df.iterrows():
                folium.Marker(
                    [r['lat'], r['lon']], 
                    popup=f"{r['Marchio']}: {r['Prezzo']}€",
                    tooltip=f"{r['Prezzo']}€",
                    icon=folium.Icon(color='green', icon='gas-pump', prefix='fa')
                ).add_to(m)
            st_folium(m, width=700, height=600)
        else:
            st.warning("Mappa non disponibile per questa città su questo sito.")

else:
    st.error("Non ho trovato dati per questa città. Prova a scriverla correttamente (es. Roma, Caltanissetta, Milano).")
