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
    h = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    try:
        # Download dei file
        res_a = requests.get("https://www.mimit.gov.it/images/exportOP/anagrafica_impianti_attivi.csv", headers=h, timeout=20)
        res_p = requests.get("https://www.mimit.gov.it/images/exportOP/prezzi_praticati_e_sociali.csv", headers=h, timeout=20)
        
        # NOTA: skiprows rimosso perché il Ministero ha cambiato il file
        df_a = pd.read_csv(StringIO(res_a.text), sep=';', on_bad_lines='skip', engine='python')
        df_p = pd.read_csv(StringIO(res_p.text), sep=';', on_bad_lines='skip', engine='python')
        
        # Pulizia nomi colonne (rimuove spazi invisibili)
        df_a.columns = df_a.columns.str.strip()
        df_p.columns = df_p.columns.str.strip()
        
        return df_a, df_p
    except Exception as e:
        st.error(f"Errore tecnico: {e}")
        return None, None

st.title("⛽ Monitor Prezzi Carburante")

df_a, df_p = load_data()

if df_a is not None and df_p is not None:
    # Sidebar
    prov = st.sidebar.text_input("Provincia (es: CL, RM, MI)", "CL").upper().strip()
    carb = st.sidebar.selectbox("Carburante", ["Benzina", "Gasolio", "GPL", "Metano"])
    
    # Filtraggio
    df_a_filtrato = df_a[df_a['Provincia'] == prov].copy()
    
    if not df_a_filtrato.empty:
        # Unione con i prezzi
        df_m = pd.merge(df_a_filtrato, df_p, on='idImpianto')
        
        # Filtro tipo carburante
        df = df_m[df_m['descCarburante'].str.contains(carb, case=False)].copy()
        
        if not df.empty:
            df['prezzo'] = pd.to_numeric(df['prezzo'], errors='coerce')
            df['Latitudine'] = pd.to_numeric(df['Latitudine'], errors='coerce')
            df['Longitudine'] = pd.to_numeric(df['Longitudine'], errors='coerce')
            df = df.dropna(subset=['Latitudine', 'Longitudine', 'prezzo']).sort_values('prezzo')

            col1, col2 = st.columns([1, 2])
            
            with col1:
                st.subheader(f"Top 10 Economici - {prov}")
                for _, r in df.head(10).iterrows():
                    st.markdown(f"""
                    <div style="background-color:#f0f2f6; border-left: 5px solid #28a745; padding:10px; border-radius:5px; margin-bottom:10px;">
                        <b style="font-size:1.2em; color:#28a745;">{r['prezzo']:.3f} €/L</b><br>
                        <b>{r['Bandiera']}</b><br>
                        <small>{r['Indirizzo']}, {r['Comune']}</small>
                    </div>
                    """, unsafe_allow_html=True)

            with col2:
                st.subheader("Mappa Distributori")
                centro_lat = df['Latitudine'].mean()
                centro_lon = df['Longitudine'].mean()
                m = folium.Map(location=[centro_lat, centro_lon], zoom_start=11)
                
                for _, r in df.iterrows():
                    folium.Marker(
                        [r['Latitudine'], r['Longitudine']], 
                        popup=f"{r['Bandiera']}: {r['prezzo']}€",
                        tooltip=f"{r['prezzo']}€"
                    ).add_to(m)
                st_folium(m, width=700, height=600, returned_objects=[])
        else:
            st.warning("Nessun prezzo trovato per questo carburante in questa provincia.")
    else:
        st.warning(f"Nessun impianto trovato nella provincia '{prov}'. Assicurati di usare la sigla (es. CL per Caltanissetta, RM per Roma).")
else:
    st.info("Caricamento database ministeriale in corso...")
