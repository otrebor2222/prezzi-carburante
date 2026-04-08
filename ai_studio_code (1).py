import streamlit as st
import pandas as pd
import requests
from io import StringIO
import folium
from streamlit_folium import st_folium

# Configurazione iniziale
st.set_page_config(page_title="Prezzi Benzina", layout="wide")

@st.cache_data(ttl=3600)
def load_data():
    # User agent per evitare blocchi dal server ministeriale
    h = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    try:
        # Download Anagrafica
        res_a = requests.get("https://www.mimit.gov.it/images/exportOP/anagrafica_impianti_attivi.csv", headers=h, timeout=15)
        # Download Prezzi
        res_p = requests.get("https://www.mimit.gov.it/images/exportOP/prezzi_praticati_e_sociali.csv", headers=h, timeout=15)
        
        # Lettura robusta: usiamo on_bad_lines='skip' per saltare righe corrotte
        df_a = pd.read_csv(StringIO(res_a.text), sep=';', skiprows=1, on_bad_lines='skip', engine='python')
        df_p = pd.read_csv(StringIO(res_p.text), sep=';', skiprows=1, on_bad_lines='skip', engine='python')
        
        return df_a, df_p
    except Exception as e:
        st.error(f"Errore nel caricamento dati dal Ministero: {e}")
        return None, None

st.title("⛽ Prezzi Carburante in Tempo Reale")

df_a, df_p = load_data()

if df_a is not None and df_p is not None:
    # Sidebar Filtri
    prov = st.sidebar.text_input("Provincia (es: CL, RM, MI, NA)", "CL").upper()
    carb = st.sidebar.selectbox("Carburante", ["Benzina", "Gasolio", "GPL", "Metano"])
    
    # Pulizia e Unione dati
    df_m = pd.merge(df_a[df_a['Provincia'] == prov], df_p, on='idImpianto')
    
    # Filtro carburante (es. Benzina o Gasolio)
    df = df_m[df_m['descCarburante'].str.contains(carb, case=False)].copy()
    
    if not df.empty:
        # Converti prezzi e coordinate in numeri
        df['prezzo'] = pd.to_numeric(df['prezzo'], errors='coerce')
        df['Latitudine'] = pd.to_numeric(df['Latitudine'], errors='coerce')
        df['Longitudine'] = pd.to_numeric(df['Longitudine'], errors='coerce')
        
        df = df.dropna(subset=['Latitudine', 'Longitudine', 'prezzo']).sort_values('prezzo')

        # Layout a due colonne come nello screenshot
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.subheader("Lista Prezzi")
            # Mostra i primi 15 distributori più economici
            for _, r in df.head(15).iterrows():
                with st.container():
                    st.markdown(f"""
                    <div style="background-color:#28a745; color:white; padding:10px; border-radius:5px; margin-bottom:5px;">
                        <h3 style="margin:0;">{r['prezzo']:.3f} €</h3>
                        <small>{r['Bandiera']} - {r['Indirizzo']}</small>
                    </div>
                    """, unsafe_allow_html=True)

        with col2:
            st.subheader("Mappa")
            # Centro mappa sulla provincia selezionata
            m = folium.Map(location=[df['Latitudine'].mean(), df['Longitudine'].mean()], zoom_start=11)
            for _, r in df.iterrows():
                folium.Marker(
                    [r['Latitudine'], r['Longitudine']], 
                    popup=f"{r['Bandiera']}: {r['prezzo']}€",
                    tooltip=f"{r['prezzo']}€"
                ).add_to(m)
            st_folium(m, width=700, height=600, returned_objects=[])
    else:
        st.warning(f"Nessun dato trovato per la provincia di {prov}. Prova a scrivere RM o MI.")
else:
    st.info("Sto scaricando i dati dal Ministero... attendi qualche secondo.")