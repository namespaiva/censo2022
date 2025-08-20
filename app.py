import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json 
from supabase import create_client, Client

st.set_page_config(page_title="Dados do Censo 2022 do IBGE", page_icon="🌎", layout='wide')

# Só é usado para acessar o banco local do Postgres (caso a intenção seja rodar localmente)
# @st.cache_resource()
# def get_connection():
#     try:
#         conn = st.connection("postgresql", type="sql", ttl=600)
#         return conn
#     except Exception as e:
#         st.error(f"Erro ao conectar ao banco de dados: {e}")

# conn = get_connection()

@st.cache_data()
def load_data():
    # Conexão via Postgres local
    # df = conn.query("SELECT * FROM populacao")
    # dflogs = conn.query("SELECT * FROM logradouro_setor")

    # Conexão via Supabase
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(url, key)

    pop_resp = supabase.table("populacao").select("*").execute()
    logs_resp = supabase.table("logradouro_setor").select("*").execute()

    dfpop = pd.DataFrame(pop_resp.data)
    dflogs = pd.DataFrame(logs_resp.data)

    with open("dados/setores_santos.geojson", "r", encoding="utf-8") as f:
        geojson_setores = json.load(f)
    return dfpop, dflogs, geojson_setores

dfpop, dflogs, geojson_setores = load_data()

feats = geojson_setores["features"]
dfsetores = pd.json_normalize(feats)
dfsetores.rename(columns={"properties.CD_SETOR": "cd_setor",
                          "properties.NM_BAIRRO": "bairro",
                          "properties.SITUACAO": "situacao",
                          "properties.NM_NU": "nucleo_urbano",
                          "properties.NM_FCU": "favela_comunidade",
                          "properties.NM_AGLOM": "aglomerado"}, inplace=True)
dfsetores["cd_setor"] = dfsetores["cd_setor"].astype(int)

# Alterando o nome da coluna para melhor legibilidade no mapa do Plotly.
dfpop.rename(columns={"cd_setor": "Código do Setor", 
                      "total_pessoas": "Total de Pessoas"}, inplace=True)

# Debug do json
# st.json(geojson_setores)

# Debug do dataframe
#st.dataframe(df)

c1 = st.container()
c2 = st.container()

colData, colMap = st.columns([1, 3])
selected_data = None

# Realiza filtragem no dataframe com base na seleção do Multiselect, apenas se valores forem selecionados.
def filter(filtro):
    global df_filtered
    df_filtered = dfpop.copy()
    if filtro is not None and filtro != []:
        df_selected_logs = dflogs[dflogs["logradouro_completo"].isin(filtro)]
        df_filtered = dfpop[dfpop["cd_setor"].isin(df_selected_logs["cd_setor"])]
    if df_filtered.empty:
        st.warning("Nenhum setor encontrado para um ou mais logradouros selecionados. " \
        "Isso pode ser pois esse logradouro passa dentro de um setor, e não nas suas arestas.")
        df_filtered = dfpop.copy()

with c1:
    selected_logs = st.multiselect(
        "Selecione o(s) logradouro(s)",
        options=sorted(list(dflogs["logradouro_completo"].unique())),
        placeholder="Digite o nome do logradouro"
    )
    filter(selected_logs)
    st.divider()


with c2:
    with colMap:
        fig = px.choropleth_map(
            df_filtered,
            geojson=geojson_setores,
            locations="Código do Setor",
            featureidkey="properties.CD_SETOR",
            color_continuous_scale="Reds",
            # Fixando os valores minimos e máximos com valores do banco. 
            # Isso evita que as cores mudem conforme os setores são filtrados, mantendo a proporção geral.
            range_color=[0, 1810],
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
            st.markdown(''':red-background[Nenhum setor selecionado.]  
                        Selecione um ou mais setores no mapa para ver as estatísticas.''')
        else:
            # debug do JSON de seleção
            #st.write("Setores selecionados:", selected_data)
            # debug dos setores selecionados
            #st.write("Códigos dos setores selecionados:", setor_selected) 
            # debug do dataframe filtrado
            #st.dataframe(df_selected)
            
            setor_selected = [int(i["properties"]["CD_SETOR"]) for i in selected_data["selection"]["points"]]

            df_selected_setor = dfpop[dfpop["Código do Setor"].isin(setor_selected)]

            with st.expander("Estatísticas agregadas dos setores selecionados"):
                st.write("Total de Pessoas nos setores selecionados:", df_selected_setor["Total de Pessoas"].sum())
                st.write("Total de Domicílios nos setores selecionados:", df_selected_setor["total_domicilios"].sum())
                st.write("Total de Domicílios Particulares:", df_selected_setor["total_domicilios_particulares"].sum())
                st.write("Total de Domicílios Particulares Ocupados:", df_selected_setor["total_dom_part_ocupados"].sum())
                st.write("Total de Domicílios Coletivos:", df_selected_setor["total_domicilios_coletivos"].sum())
                st.write("Média de Moradores em Domicílios Particulares Ocupados:", df_selected_setor["media_moradores_dom_part_ocupados"].mean().round(2))
                st.write("Média do Percent. Domicílios Particulares Ocupados", (df_selected_setor["pc_dom_part_ocupados_inputados"].mean() * 100).round(2), "%")

            with st.expander("Setores individuais"):
                for index, row in df_selected_setor.iterrows():
                    with st.expander(f"Estatísticas do Setor {int(row['Código do Setor'])}"):
                        setor = dfsetores[dfsetores["cd_setor"] == int(row["Código do Setor"])]
                        st.markdown(f"Bairro: :green[{setor['bairro'].values[0]}]")
                        if setor["nucleo_urbano"].values[0] is not None:
                            st.markdown(f"Núcleo Urbano: :green[{setor['nucleo_urbano'].values[0]}]")
                        if setor["favela_comunidade"].values[0] is not None:
                            st.markdown(f"Favela/Comunidade: :green[{setor['favela_comunidade'].values[0]}]")
                        if setor["aglomerado"].values[0] is not None:
                            st.markdown(f"Aglomerado: :green[{setor['aglomerado'].values[0]}]")
                        st.markdown(f"Situação: :green[{setor['situacao'].values[0]}]")
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