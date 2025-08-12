import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json

st.set_page_config(page_title="Dados do IBGE", page_icon="🌎", layout='wide',initial_sidebar_state="collapsed")

@st.cache_resource()
def get_connection():
    try:
        conn = st.connection("postgresql", type="sql")
        return conn
    except Exception as e:
        st.error(f"Erro ao conectar ao banco de dados: {e}")

conn = get_connection()

@st.cache_data()
def load_data():
    df = conn.query("SELECT * FROM populacao")
    with open("dados/setores_santos.geojson", "r", encoding="utf-8") as f:
        geojson_setores = json.load(f)
    return df, geojson_setores
df, geojson_setores = load_data()

df.rename(columns={"total_pessoas": "Total de Pessoas"}, inplace=True)

# debug do json
#st.json(geojson_setores)

# debug do dataframe
#st.dataframe(df)

colData, colMap = st.columns([1, 3])
selected_data = None

with colMap:
    fig = px.choropleth_map(
        df,
        geojson=geojson_setores,
        locations="cd_setor",
        featureidkey="properties.CD_SETOR",
        color_continuous_scale="Reds",
        range_color=[df["Total de Pessoas"].max() + 1, df["Total de Pessoas"].max()],
        color="Total de Pessoas",
        center={"lat": -23.95462, "lon": -46.33725},
        zoom=11.9,
        map_style="carto-positron"
    )
    fig.update_layout(margin={"r":0,"t":0,"l":0,"b":0})
    selected_data = st.plotly_chart(
        fig, 
        on_select='rerun',
        selection_mode=["points", "box", "lasso"],
        use_container_width=True
    )

with colData:
    if selected_data is None or selected_data["selection"]["points"] == []:
        st.write("Nenhum setor selecionado. Selecione um ou mais setores no mapa para ver as estatísticas.")
    else:
        # debug do JSON de seleção
        #st.write("Setores selecionados:", selected_data)
        # debug dos setores selecionados
        #st.write("Códigos dos setores selecionados:", setor_selected) 
        # debug do dataframe filtrado
        #st.dataframe(df_selected)
        
        setor_selected = [int(i["properties"]["CD_SETOR"]) for i in selected_data["selection"]["points"]]

        df_selected = df[df["cd_setor"].isin(setor_selected)]

        with st.expander("Estatísticas agregadas dos setores selecionados"):
            st.write("Total de Pessoas nos setores selecionados:", df_selected["Total de Pessoas"].sum())
            st.write("Total de Domicílios nos setores selecionados:", df_selected["total_domicilios"].sum())
            st.write("Total de Domicílios Particulares:", df_selected["total_domicilios_particulares"].sum())
            st.write("Total de Domicílios Particulares Ocupados:", df_selected["total_dom_part_ocupados"].sum())
            st.write("Total de Domicílios Coletivos:", df_selected["total_domicilios_coletivos"].sum())
            st.write("Média de Moradores em Domicílios Particulares Ocupados:", df_selected["media_moradores_dom_part_ocupados"].mean().round(2))
            st.write("Média do Percent. Domicílios Particulares Ocupados", (df_selected["pc_dom_part_ocupados_inputados"].mean() * 100).round(2), "%")

        with st.expander("Setores individuais"):
            for index, row in df_selected.iterrows():
                with st.expander(f"Estatísticas do Setor {int(row['cd_setor'])}"):
                    st.write("Total de Pessoas:", int(row["Total de Pessoas"]))
                    st.write("Total de Domicílios:", int(row["total_domicilios"]))
                    st.write("Total de Domicílios Particulares:", int(row["total_domicilios_particulares"]))
                    st.write("Total de Domicílios Particulares Ocupados:", int(row["total_dom_part_ocupados"]))
                    st.write("Total de Domicílios Coletivos:", int(row["total_domicilios_coletivos"]))
                    st.write("Média de Moradores em Domicílios Particulares Ocupados:", row["media_moradores_dom_part_ocupados"])
                    st.write("Percentual de Domicílios Particulares Ocupados Inputados:", (row["pc_dom_part_ocupados_inputados"] * 100).round(2), "%")

                    st.write("Área Domiciliada", row["area_domiciliada_km2"].round(2), "km²")
                    st.write("Densidade Demográfica Domiciliada", row["densidade_dem_domiciliada"].round(2), "hab/km²")
                    st.write("Densidade Demográfica do Setor", row["densidade_dem_setor"].round(2), "hab/km²")


st.write("")
st.divider()
st.write("""
         Fonte dos dados: IBGE - Censo Demográfico 2022  
         Disponível em: https://censo2022.ibge.gov.br/apps/pgi/#/mapa/
         """)
st.write("2025 Desenvolvido no Centro de Pesquisas em Mobilidade Urbana (CPMU) - CET Santos")