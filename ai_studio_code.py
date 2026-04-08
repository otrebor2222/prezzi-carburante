import streamlit as st
import pandas as pd
import requests
from io import StringIO
import folium
from streamlit_folium import st_folium

st.set_page_config(page_title="Prezzi Carburante Italia", layout="wide", page_icon="⛽")

# --- STILE CSS ---
st.markdown("""
    <style>
    .price-box {
        background-color: white; padding: 15px; border-radius: 10px; 
        border-left: 10px solid #28a745; margin-bottom: 10px; 
        box-shadow: 2px 2px 5px rgba(0,0,0,0.1); display: flex; 
        justify-content: space-between; align-items: center;
    }
    .price-value {
        background: #28a745; color: white; padding: 5px 15px; 
        border-radius: 5px; font-weight: bold; font-size: 1.3em;
    }
    </style>
    """, unsafe_allow_html=True)

# --- FUNZIONE DOWNLOAD ---
def download_mimit_data():
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0'}
    try:
        res_a = requests.get("https://www.mimit.gov.it/images/exportOP/anagrafica_impianti_attivi.csv", headers=headers, timeout=10)
        res_p = requests.get("https://www.mimit.gov.it/images/exportOP/prezzi_praticati_e_sociali.csv", headers=headers, timeout=10)
        if res_a.status_code == 200 and res_p.status_code == 200:
            df_a = pd.read_csv(StringIO(res_a.text), sep=';', skiprows=1, on_bad_lines='skip', engine='python')
            df_p = pd.read_csv(StringIO(res_p.text), sep=';', skiprows=1, on_bad_lines='skip', engine='python')
            return df_a, df_p
    except:
        return None, None
    return None, None

# --- SIDEBAR ---
st.sidebar.title("⛽ Menu")
provincia = st.sidebar.text_input("Sigla Provincia", "CL").upper().strip()
carburante = st.sidebar.selectbox("Carburante", ["Benzina", "Gasolio", "GPL", "Metano"])

# --- CARICAMENTO DATI ---
df_a, df_p = download_mimit_data()

# Se il download automatico fallisce (Blocco Server)
if df_a is None:
    st.warning("⚠️ Il Ministero ha bloccato la connessione automatica. Carica i file manualmente per procedere.")
    col_up1, col_up2 = st.columns(2)
    with col_up1:
        up_a = st.file_uploader("Carica file ANAGRAFICA (.csv)", type="csv")
    with col_up2:
        up_p = st.file_uploader("Carica file PREZZI (.csv)", type="csv")
    
    if up_a and up_p:
        df_a = pd.read_csv(up_a, sep=';', skiprows=1, on_bad_lines='skip', engine='python')
        df_p = pd.read_csv(up_p, sep=';', skiprows=1, on_bad_lines='skip', engine='python')

# --- ELABORAZIONE E VISUALIZZAZIONE ---
if df_a is not None and df_p is not None:
    df_a.columns = [c.strip() for c in df_a.columns]
    df_p.columns = [c.strip() for c in df_p.columns]
    
    # Unione dati
    df_merged = pd.merge(df_a[df_a['Provincia'] == provincia], df_p, on='idImpianto')
    df = df_merged[df_merged['descCarburante'].str.contains(carburante, case=False, na=False)].copy()
    
    if not df.empty:
        df['prezzo'] = pd.to_numeric(df['prezzo'], errors='coerce')
        df = df.dropna(subset=['Latitudine', 'Longitudine', 'prezzo']).sort_values('prezzo')

        st.header(f"Prezzi {carburante} in provincia di {provincia}")
        
        col_lista, col_mappa = st.columns([1, 1.5])
        
        with col_lista:
            st.write("### 🏆 Più Economici")
            for _, r in df.head(15).iterrows():
                st.markdown(f"""
                <div class="price-box">
                    <div>
                        <b style="color:#0056b3;">{r['Bandiera']}</b><br>
                        <small>{r['Indirizzo']}, {r['Comune']}</small>
                    </div>
                    <div class="price-value">{r['prezzo']:.3f}</div>
                </div>
                """, unsafe_allow_html=True)
        
        with col_mappa:
            st.write("### 📍 Mappa Stazioni")
            m = folium.Map(location=[df['Latitudine'].mean(), df['Longitudine'].mean()], zoom_start=11)
            for _, r in df.head(50).iterrows():
                folium.Marker(
                    [r['Latitudine'], r['Longitudine']], 
                    popup=f"{r['Bandiera']}: {r['prezzo']}€",
                    tooltip=f"{r['prezzo']}€",
                    icon=folium.Icon(color='green', icon='gas-pump', prefix='fa')
                ).add_to(m)
            st_folium(m, width="100%", height=600)
    else:
        st.error("Nessun dato trovato per questa provincia. Controlla la sigla (es. MI, RM, CL).")

else:
    st.info("Scarica i file dal sito del Ministero e caricali qui per vedere la mappa interattiva.")
    st.link_button("Scarica Anagrafica (CSV)", "https://www.mimit.gov.it/images/exportOP/anagrafica_impianti_attivi.csv")
    st.link_button("Scarica Prezzi (CSV)", "https://www.mimit.gov.it/images/exportOP/prezzi_praticati_e_sociali.csv")
