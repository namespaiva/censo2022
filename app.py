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
    demog_resp = supabase.table("demografia_setor").select("*").execute()

    dfpop = pd.DataFrame(pop_resp.data)
    dflogs = pd.DataFrame(logs_resp.data)
    dfdemog = pd.DataFrame(demog_resp.data)

    with open("dados/setores_santos.geojson", "r", encoding="utf-8") as f:
        geojson_setores = json.load(f)
    return dfpop, dflogs, dfdemog, geojson_setores

dfpop, dflogs, dfdemog, geojson_setores = load_data()

feats = geojson_setores["features"]
dfsetores = pd.json_normalize(feats)
dfsetores.rename(columns={"properties.CD_SETOR": "cd_setor",
                          "properties.NM_BAIRRO": "bairro",
                          "properties.SITUACAO": "situacao",
                          "properties.NM_NU": "nucleo_urbano",
                          "properties.NM_FCU": "favela_comunidade",
                          "properties.NM_AGLOM": "aglomerado"}, inplace=True)
dfsetores["cd_setor"] = dfsetores["cd_setor"].astype(int)
dfsetores["bairro"] = dfsetores["bairro"].fillna("Não informado")
dfbairro = dfsetores[["cd_setor", "bairro"]].copy()
dfpop = dfpop.merge(dfbairro, how="left", left_on="cd_setor", right_on="cd_setor")

# Alterando o nome da coluna para melhor legibilidade no mapa do Plotly.
dfpop.rename(columns={"cd_setor": "Código do Setor", 
                      "total_pessoas": "Total de Pessoas"}, inplace=True)

df_filtered = dfpop.copy()

c1 = st.container()
c2 = st.container()

colData, colMap = st.columns([1, 2])
selected_data = None

# Realiza filtragem no dataframe com base na seleção do Multiselect, apenas se valores forem selecionados.
def filter(selecao, filtro):
    global df_filtered

    if selecao is not None and selecao != []:
        if df_filtered is None:
            df_filtered = dfpop.copy()
        if filtro == "bairros":
            df_selected_bairros = dfsetores[dfsetores["bairro"].isin(selecao)]
            df_filtered = dfpop[dfpop["Código do Setor"].isin(df_selected_bairros["cd_setor"])]

        if filtro == "logradouros":
            df_selected_logs = dflogs[dflogs["logradouro_completo"].isin(selecao)]
            df_filtered = df_filtered[df_filtered["Código do Setor"].isin(df_selected_logs["cd_setor"])]

    if df_filtered.empty:
        st.warning("Nenhum setor encontrado para um ou mais logradouros ou bairros selecionados. " \
        "Isso pode ser pois esse logradouro passa dentro de um setor, e não nas suas arestas." \
        "Ou então o bairro não possui setores na base de dados.")
        df_filtered = dfpop.copy()

with c1:
    selected_bairros = st.multiselect(
        "Selecione o(s) bairro(s)",
        options=sorted(list(dfsetores["bairro"].unique())),
        placeholder="Digite o nome do bairro"
    )
    filter(selected_bairros, "bairros")
    
    selected_logs = st.multiselect(
        "Selecione o(s) logradouro(s)",
        options=sorted(list(dflogs["logradouro_completo"][dflogs["cd_setor"].isin(df_filtered["Código do Setor"])].unique())),
        placeholder="Digite o nome do logradouro"
    )
    filter(selected_logs, "logradouros")
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
            st.markdown('''
                <div style="padding:10px;border-radius:5px;">
                    <strong style="color:#ff4b4b">Nenhum setor selecionado.</strong>
                    <p style="text-align: justify">Selecione um ou mais setores usando as ferramentas no canto superior direito do mapa para ver as estatísticas.</p>
                </div>
            ''', unsafe_allow_html=True)
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
                        with st.expander("Demografia"):
                            dfdemog_setor = dfdemog[dfdemog["cd_setor"] == int(row["Código do Setor"])]
                            with st.expander("Por Idade"):
                                st.write("Habitantes de 0 a 4 anos: ", dfdemog_setor["0_a_4_anos"].values[0])
                                st.write("Habitantes de 5 a 9 anos: ", dfdemog_setor["5_a_9_anos"].values[0])
                                st.write("Habitantes de 10 a 14 anos: ", dfdemog_setor["10_a_14_anos"].values[0])
                                st.write("Habitantes de 15 a 19 anos: ", dfdemog_setor["15_a_19_anos"].values[0])
                                st.write("Habitantes de 20 a 24 anos: ", dfdemog_setor["20_a_24_anos"].values[0])
                                st.write("Habitantes de 25 a 29 anos: ", dfdemog_setor["25_a_29_anos"].values[0])
                                st.write("Habitantes de 30 a 39 anos: ", dfdemog_setor["30_a_39_anos"].values[0])
                                st.write("Habitantes de 40 a 49 anos: ", dfdemog_setor["40_a_49_anos"].values[0])
                                st.write("Habitantes de 50 a 59 anos: ", dfdemog_setor["50_a_59_anos"].values[0])
                                st.write("Habitantes de 60 a 69 anos: ", dfdemog_setor["60_a_69_anos"].values[0])
                                st.write("Habitantes de 70 anos ou mais: ", dfdemog_setor["70_anos_ou_mais"].values[0])
                            with st.expander("Por Sexo e Idade"):
                                st.write("Total de Habitantes do Sexo Masculino: ", dfdemog_setor["sexo_masculino"].values[0])
                                st.write("Total de Habitantes do Sexo Feminino: ", dfdemog_setor["sexo_feminino"].values[0])
                                with st.expander("Detalhes - Masculino"):
                                    st.write("Homens de 0 a 4 anos: ", dfdemog_setor["sexo_masculino_0_a_4_anos"].values[0])
                                    st.write("Homens de 5 a 9 anos: ", dfdemog_setor["sexo_masculino_5_a_9_anos"].values[0])
                                    st.write("Homens de 10 a 14 anos: ", dfdemog_setor["sexo_masculino_10_a_14_anos"].values[0])
                                    st.write("Homens de 15 a 19 anos: ", dfdemog_setor["sexo_masculino_15_a_19_anos"].values[0])
                                    st.write("Homens de 20 a 24 anos: ", dfdemog_setor["sexo_masculino_20_a_24_anos"].values[0])
                                    st.write("Homens de 25 a 29 anos: ", dfdemog_setor["sexo_masculino_25_a_29_anos"].values[0])
                                    st.write("Homens de 30 a 39 anos: ", dfdemog_setor["sexo_masculino_30_a_39_anos"].values[0])
                                    st.write("Homens de 40 a 49 anos: ", dfdemog_setor["sexo_masculino_40_a_49_anos"].values[0])
                                    st.write("Homens de 50 a 59 anos: ", dfdemog_setor["sexo_masculino_50_a_59_anos"].values[0])
                                    st.write("Homens de 60 a 69 anos: ", dfdemog_setor["sexo_masculino_60_a_69_anos"].values[0])
                                    st.write("Homens de 70 anos ou mais: ", dfdemog_setor["sexo_masculino_70_anos_ou_mais"].values[0])
                                with st.expander("Detalhes - Feminino"):
                                    st.write("Mulheres de 0 a 4 anos: ", dfdemog_setor["sexo_feminino_0_a_4_anos"].values[0])
                                    st.write("Mulheres de 5 a 9 anos: ", dfdemog_setor["sexo_feminino_5_a_9_anos"].values[0])
                                    st.write("Mulheres de 10 a 14 anos: ", dfdemog_setor["sexo_feminino_10_a_14_anos"].values[0])
                                    st.write("Mulheres de 15 a 19 anos: ", dfdemog_setor["sexo_feminino_15_a_19_anos"].values[0])
                                    st.write("Mulheres de 20 a 24 anos: ", dfdemog_setor["sexo_feminino_20_a_24_anos"].values[0])
                                    st.write("Mulheres de 25 a 29 anos: ", dfdemog_setor["sexo_feminino_25_a_29_anos"].values[0])
                                    st.write("Mulheres de 30 a 39 anos: ", dfdemog_setor["sexo_feminino_30_a_39_anos"].values[0])
                                    st.write("Mulheres de 40 a 49 anos: ", dfdemog_setor["sexo_feminino_40_a_49_anos"].values[0])
                                    st.write("Mulheres de 50 a 59 anos: ", dfdemog_setor["sexo_feminino_50_a_59_anos"].values[0])
                                    st.write("Mulheres de 60 a 69 anos: ", dfdemog_setor["sexo_feminino_60_a_69_anos"].values[0])
                                    st.write("Mulheres de 70 anos ou mais: ", dfdemog_setor["sexo_feminino_70_anos_ou_mais"].values[0])
                        with st.expander(f"Logradouro(s)"):
                            for log in dflogs[dflogs["cd_setor"] == int(row["Código do Setor"])]["logradouro_completo"].unique().tolist():
                                st.markdown(f":green[{log}]")
                        st.markdown(f"Bairro: :green[{setor['bairro'].values[0]}]")
                        if setor["nucleo_urbano"].values[0] is not None:
                            st.markdown(f"Núcleo Urbano: :green[{setor['nucleo_urbano'].values[0]}]")
                        if setor["favela_comunidade"].values[0] is not None:
                            st.markdown(f"Favela/Comunidade: :green[{setor['favela_comunidade'].values[0]}]")
                        if setor["aglomerado"].values[0] is not None:
                            st.markdown(f"Aglomerado: :green[{setor['aglomerado'].values[0]}]")
                        # Comentado pois todos os setores estão como "Urbana"
                        #st.markdown(f"Situação: :green[{setor['situacao'].values[0]}]")
                        st.write("Total de Pessoas:", int(row["Total de Pessoas"]))
                        st.write("Total de Domicílios:", int(row["total_domicilios"]))
                        st.write("Total de Domicílios Particulares:", int(row["total_domicilios_particulares"]))
                        st.write("Total de Domicílios Particulares Ocupados:", int(row["total_dom_part_ocupados"]))
                        st.write("Total de Domicílios Coletivos:", int(row["total_domicilios_coletivos"]))
                        st.write("Média de Moradores em Domicílios Particulares Ocupados:", row["media_moradores_dom_part_ocupados"])
                        st.write("Percentual de Domicílios Particulares Ocupados Inputados:", round(row["pc_dom_part_ocupados_inputados"] * 100, 2), "%")
                        st.write("Área Domiciliada", round(row["area_domiciliada_km2"]), "km²")
                        try:
                            st.write("Densidade Demográfica Domiciliada", round(row["densidade_dem_domiciliada"]), "hab/km²")
                            st.write("Densidade Demográfica do Setor", round(row["densidade_dem_setor"]), "hab/km²")
                        except KeyError:
                            st.write("Densidade Demográfica não disponível")


st.divider()
st.write("""
         Fonte dos dados: IBGE - Censo Demográfico 2022  
         Disponível em: https://censo2022.ibge.gov.br/apps/pgi/#/mapa/
         """)
st.write("2025 Desenvolvido no Centro de Pesquisas em Mobilidade Urbana (CPMU) - CET Santos")