import streamlit as st
import pandas as pd
import requests
from io import StringIO
import folium
from streamlit_folium import st_folium

st.set_page_config(page_title="Prezzi Benzina Live", layout="wide")

@st.cache_data(ttl=3600)
def load_data():
    h = {'User-Agent': 'Mozilla/5.0'}
    res_a = requests.get("https://www.mimit.gov.it/images/exportOP/anagrafica_impianti_attivi.csv", headers=h)
    res_p = requests.get("https://www.mimit.gov.it/images/exportOP/prezzi_praticati_e_sociali.csv", headers=h)
    df_a = pd.read_csv(StringIO(res_a.text), sep=';', skiprows=1)
    df_p = pd.read_csv(StringIO(res_p.text), sep=';', skiprows=1)
    return df_a, df_p

st.title("⛽ Confronto Prezzi Carburante")
prov = st.sidebar.text_input("Provincia (es: CL, MI, RM)", "CL").upper()
carb = st.sidebar.selectbox("Carburante", ["Benzina", "Gasolio", "GPL", "Metano"])

df_a, df_p = load_data()
df_m = pd.merge(df_a[df_a['Provincia'] == prov], df_p, on='idImpianto')
df = df_m[df_m['descCarburante'].str.contains(carb, case=False)].copy()
df['prezzo'] = pd.to_numeric(df['prezzo'], errors='coerce')
df = df.dropna(subset=['Latitudine', 'Longitudine', 'prezzo']).sort_values('prezzo')

col1, col2 = st.columns([1, 2])
with col1:
    for _, r in df.head(15).iterrows():
        st.success(f"**{r['prezzo']:.3f}€** - {r['Bandiera']}\n\n{r['Indirizzo']}")

with col2:
    m = folium.Map(location=[df['Latitudine'].mean(), df['Longitudine'].mean()], zoom_start=12)
    for _, r in df.iterrows():
        folium.Marker([r['Latitudine'], r['Longitudine']], popup=f"{r['prezzo']}€").add_to(m)
    st_folium(m, width=700, height=500)