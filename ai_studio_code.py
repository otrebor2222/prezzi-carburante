import streamlit as st
import pandas as pd
import requests
from io import StringIO
import folium
from streamlit_folium import st_folium

st.set_page_config(page_title="Prezzi Benzina", layout="wide")

@st.cache_data(ttl=600) # Aggiorna ogni 10 minuti
def load_data():
    h = {'User-Agent': 'Mozilla/5.0'}
    try:
        res_a = requests.get("https://www.mimit.gov.it/images/exportOP/anagrafica_impianti_attivi.csv", headers=h, timeout=20)
        res_p = requests.get("https://www.mimit.gov.it/images/exportOP/prezzi_praticati_e_sociali.csv", headers=h, timeout=20)
        
        def smart_read(text):
            lines = text.splitlines()
            start_row = 0
            for i, line in enumerate(lines[:15]):
                if 'idImpianto' in line:
                    start_row = i
                    break
            df = pd.read_csv(StringIO("\n".join(lines[start_row:])), sep=';', on_bad_lines='skip', engine='python')
            df.columns = [str(c).strip() for c in df.columns]
            return df

        return smart_read(res_a.text), smart_read(res_p.text)
    except Exception as e:
        st.error(f"Errore download: {e}")
        return None, None

st.title("⛽ Monitor Prezzi Carburante")

df_a, df_p = load_data()

if df_a is not None and df_p is not None:
    # Cerchiamo la colonna Provincia in modo dinamico
    col_prov = [c for c in df_a.columns if 'prov' in c.lower()]
    
    if col_prov:
        nome_col_prov = col_prov[0]
        prov = st.sidebar.text_input("Provincia (es: CL, RM, MI)", "CL").upper().strip()
        carb = st.sidebar.selectbox("Carburante", ["Benzina", "Gasolio", "GPL", "Metano"])
        
        # Filtraggio
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
                    st.subheader(f"Migliori prezzi: {prov}")
                    for _, r in df.head(12).iterrows():
                        st.markdown(f"""
                        <div style="background-color:#28a745; color:white; padding:10px; border-radius:8px; margin-bottom:8px;">
                            <h3 style="margin:0;">{r['prezzo']:.3f} €</h3>
                            <b>{r['Bandiera']}</b><br><small>{r['Indirizzo']}</small>
                        </div>
                        """, unsafe_allow_html=True)

                with col2:
                    m = folium.Map(location=[df['Latitudine'].mean(), df['Longitudine'].mean()], zoom_start=11)
                    for _, r in df.head(50).iterrows():
                        folium.Marker([r['Latitudine'], r['Longitudine']], popup=f"{r['prezzo']}€").add_to(m)
                    st_folium(m, width=700, height=600, returned_objects=[])
            else:
                st.warning("Carburante non trovato.")
        else:
            st.warning("Provincia non trovata.")
    else:
        st.error(f"Errore: Colonne non riconosciute. Trovate: {list(df_a.columns)}")
