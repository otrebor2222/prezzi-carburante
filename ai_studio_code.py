import streamlit as st
import pandas as pd
import requests
from io import StringIO
import folium
from streamlit_folium import st_folium

st.set_page_config(page_title="Prezzi Benzina", layout="wide")

@st.cache_data(ttl=900)
def load_data():
    # Header avanzati per ingannare il firewall del Ministero
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7',
        'Referer': 'https://www.mimit.gov.it/',
        'Connection': 'keep-alive'
    }
    
    urls = {
    'anagrafica': "http://www.mimit.gov.it/images/exportOP/anagrafica_impianti_attivi.csv",
    'prezzi': "http://www.mimit.gov.it/images/exportOP/prezzi_praticati_e_sociali.csv"
}
    }

    try:
        data = {}
        for key, url in urls.items():
            response = requests.get(url, headers=headers, timeout=30)
            
            # Se riceviamo HTML invece di CSV, il sito ci sta bloccando
            if response.text.strip().startswith('<!DOCTYPE'):
                st.error(f"Il sito del Ministero ha bloccato la richiesta (Errore: Ricevuto HTML invece di CSV).")
                st.info("Consiglio: Riprova tra qualche minuto o ricarica la pagina.")
                return None, None
            
            # Trova la riga corretta dell'intestazione
            lines = response.text.splitlines()
            start = 0
            for i, line in enumerate(lines[:20]):
                if 'idImpianto' in line:
                    start = i
                    break
            
            df = pd.read_csv(StringIO("\n".join(lines[start:])), sep=';', on_bad_lines='skip', engine='python')
            df.columns = [str(c).strip() for c in df.columns]
            data[key] = df
            
        return data['anagrafica'], data['prezzi']
    except Exception as e:
        st.error(f"Errore di connessione: {e}")
        return None, None

st.title("⛽ Prezzi Carburante Italia")

df_a, df_p = load_data()

if df_a is not None and df_p is not None:
    # Cerca colonna provincia
    col_prov = next((c for c in df_a.columns if 'prov' in c.lower()), None)
    
    if col_prov:
        prov_in = st.sidebar.text_input("Provincia (es: CL, RM, MI)", "CL").upper().strip()
        carb_in = st.sidebar.selectbox("Carburante", ["Benzina", "Gasolio", "GPL"])
        
        # Filtro Provincia
        df_a_f = df_a[df_a[col_prov].astype(str).str.contains(prov_in, na=False)].copy()
        
        if not df_a_f.empty:
            df_merged = pd.merge(df_a_f, df_p, on='idImpianto')
            df = df_merged[df_merged['descCarburante'].astype(str).str.contains(carb_in, case=False, na=False)].copy()
            
            if not df.empty:
                df['prezzo'] = pd.to_numeric(df['prezzo'], errors='coerce')
                df['Latitudine'] = pd.to_numeric(df['Latitudine'], errors='coerce')
                df['Longitudine'] = pd.to_numeric(df['Longitudine'], errors='coerce')
                df = df.dropna(subset=['Latitudine', 'Longitudine', 'prezzo']).sort_values('prezzo')

                # Layout
                c1, c2 = st.columns([1, 2])
                with c1:
                    st.write(f"### 🏆 Più economici ({prov_in})")
                    for _, r in df.head(10).iterrows():
                        st.success(f"**{r['prezzo']:.3f}€**\n\n{r['Bandiera']} - {r['Indirizzo']}")
                with c2:
                    st.write("### 📍 Mappa")
                    m = folium.Map(location=[df['Latitudine'].mean(), df['Longitudine'].mean()], zoom_start=11)
                    for _, r in df.head(40).iterrows():
                        folium.Marker([r['Latitudine'], r['Longitudine']], popup=f"{r['prezzo']}€").add_to(m)
                    st_folium(m, width=700, height=500, returned_objects=[])
            else: st.warning("Nessun prezzo trovato.")
        else: st.warning(f"Nessun impianto a {prov_in}")
    else: st.error("Database ministeriale non leggibile al momento.")
else:
    st.info("Connessione ai server ministeriali... per favore attendi.")
