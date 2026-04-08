import streamlit as st
import pandas as pd
import requests
from io import StringIO
import folium
from streamlit_folium import st_folium

st.set_page_config(page_title="Prezzi Benzina", layout="wide")

@st.cache_data(ttl=600)
def load_data():
    h = {'User-Agent': 'Mozilla/5.0'}
    try:
        res_a = requests.get("https://www.mimit.gov.it/images/exportOP/anagrafica_impianti_attivi.csv", headers=h, timeout=20)
        res_p = requests.get("https://www.mimit.gov.it/images/exportOP/prezzi_praticati_e_sociali.csv", headers=h, timeout=20)
        
        def safe_read(text):
            lines = text.splitlines()
            start = 0
            for i, line in enumerate(lines[:20]):
                if 'idImpianto' in line:
                    start = i
                    break
            df = pd.read_csv(StringIO("\n".join(lines[start:])), sep=';', on_bad_lines='skip', engine='python')
            df.columns = [str(c).strip() for c in df.columns]
            return df

        return safe_read(res_a.text), safe_read(res_p.text)
    except Exception as e:
        return None, None

st.title("⛽ Prezzi Carburante Online")

df_a, df_p = load_data()

if df_a is not None and df_p is not None:
    # Trova la colonna provincia in modo super-sicuro
    cols = list(df_a.columns)
    col_prov = next((c for c in cols if 'prov' in c.lower()), None)
    
    if col_prov:
        prov_input = st.sidebar.text_input("Provincia (Sigla)", "CL").upper().strip()
        carb_input = st.sidebar.selectbox("Tipo", ["Benzina", "Gasolio", "GPL"])
        
        # Filtraggio
        df_a_f = df_a[df_a[col_prov].astype(str).str.contains(prov_input, na=False)].copy()
        
        if not df_a_f.empty:
            df_m = pd.merge(df_a_f, df_p, on='idImpianto')
            df = df_m[df_m['descCarburante'].astype(str).str.contains(carb_input, case=False, na=False)].copy()
            
            if not df.empty:
                df['prezzo'] = pd.to_numeric(df['prezzo'], errors='coerce')
                df['Latitudine'] = pd.to_numeric(df['Latitudine'], errors='coerce')
                df['Longitudine'] = pd.to_numeric(df['Longitudine'], errors='coerce')
                df = df.dropna(subset=['Latitudine', 'Longitudine', 'prezzo']).sort_values('prezzo')

                c1, c2 = st.columns([1, 2])
                with c1:
                    st.write(f"### Economici a {prov_input}")
                    for _, r in df.head(10).iterrows():
                        st.info(f"**{r['prezzo']:.3f}€** - {r['Bandiera']}\n\n{r['Indirizzo']}")
                with c2:
                    m = folium.Map(location=[df['Latitudine'].mean(), df['Longitudine'].mean()], zoom_start=11)
                    for _, r in df.head(30).iterrows():
                        folium.Marker([r['Latitudine'], r['Longitudine']], popup=f"{r['prezzo']}€").add_to(m)
                    st_folium(m, width=700, height=500)
            else: st.warning("Nessun dato per questo carburante.")
        else: st.warning("Provincia non trovata.")
    else: st.error(f"Errore: Colonne non trovate. Colonne attuali: {cols}")
else:
    st.warning("Scaricamento dati... ricarica la pagina tra 10 secondi.")
