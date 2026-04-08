import streamlit as st
import pandas as pd
import requests
from io import StringIO
import folium
from streamlit_folium import st_folium

st.set_page_config(page_title="Prezzi Benzina", layout="wide")

@st.cache_data(ttl=3600)
def load_data():
    h = {'User-Agent': 'Mozilla/5.0'}
    try:
        # Download dei file come testo grezzo
        res_a = requests.get("https://www.mimit.gov.it/images/exportOP/anagrafica_impianti_attivi.csv", headers=h, timeout=20)
        res_p = requests.get("https://www.mimit.gov.it/images/exportOP/prezzi_praticati_e_sociali.csv", headers=h, timeout=20)
        
        # Funzione per leggere il CSV saltando le righe sporche iniziali
        def smart_read(text):
            lines = text.splitlines()
            start_row = 0
            # Cerca la riga che contiene 'idImpianto'
            for i, line in enumerate(lines[:10]):
                if 'idImpianto' in line:
                    start_row = i
                    break
            
            df = pd.read_csv(StringIO("\n".join(lines[start_row:])), sep=';', on_bad_lines='skip', engine='python')
            # Pulisce i nomi delle colonne da spazi o caratteri strani
            df.columns = [str(c).strip() for c in df.columns]
            return df

        df_a = smart_read(res_a.text)
        df_p = smart_read(res_p.text)
        
        return df_a, df_p
    except Exception as e:
        st.error(f"Errore tecnico: {e}")
        return None, None

st.title("⛽ Monitor Prezzi Carburante")

df_a, df_p = load_data()

if df_a is not None and df_p is not None:
    # Trova il nome esatto della colonna Provincia (anche se ha spazi o minuscole)
    col_prov = [c for c in df_a.columns if 'Provincia' in c]
    
    if col_prov:
        nome_col_prov = col_prov[0]
        prov = st.sidebar.text_input("Provincia (es: CL, RM, MI)", "CL").upper().strip()
        carb = st.sidebar.selectbox("Carburante", ["Benzina", "Gasolio", "GPL", "Metano"])
        
        # Filtraggio robusto
        df_a_filtrato = df_a[df_a[nome_col_prov].astype(str).str.contains(prov, na=False)].copy()
        
        if not df_a_filtrato.empty:
            df_m = pd.merge(df_a_filtrato, df_p, on='idImpianto')
            df = df_m[df_m['descCarburante'].astype(str).str.contains(carb, case=False, na=False)].copy()
            
            if not df.empty:
                df['prezzo'] = pd.to_numeric(df['prezzo'], errors='coerce')
                df['Latitudine'] = pd.to_numeric(df['Latitudine'], errors='coerce')
                df['Longitudine'] = pd.to_numeric(df['Longitudine'], errors='coerce')
                df = df.dropna(subset=['Latitudine', 'Longitudine', 'prezzo']).sort_values('prezzo')

                col1, col2 = st.columns([1, 2])
                with col1:
                    st.subheader(f"Top 10 Economici - {prov}")
                    for _, r in df.head(10).iterrows():
                        st.success(f"**{r['prezzo']:.3f} €/L**\n\n{r['Bandiera']} - {r['Indirizzo']}")

                with col2:
                    st.subheader("Mappa")
                    m = folium.Map(location=[df['Latitudine'].mean(), df['Longitudine'].mean()], zoom_start=11)
                    for _, r in df.head(50).iterrows(): # Limitiamo a 50 per velocità
                        folium.Marker([r['Latitudine'], r['Longitudine']], popup=f"{r['prezzo']}€").add_to(m)
                    st_folium(m, width=700, height=500, returned_objects=[])
            else:
                st.warning("Nessun prezzo trovato per questo carburante.")
        else:
            st.warning(f"Sigla '{prov}' non trovata. Usa CL, RM, MI...")
    else:
        st.error("Errore: Il file del Ministero non contiene la colonna Provincia. Colonne trovate: " + str(list(df_a.columns)))
else:
    st.info("Download dati in corso...")
