# Censo 2022 IBGE - Consulta de Dados Populacionais de Santos

**Descrição:**  
Este projeto é um aplicativo interativo desenvolvido em [Streamlit](https://streamlit.io/) para consulta de dados populacionais dos setores censitários de Santos, conforme o Censo Demográfico de 2022 do IBGE.  
Acesse estatísticas detalhadas por setor, bairro, núcleo urbano, favela/comunidade e aglomerado, além de visualizar mapas temáticos e realizar filtros por logradouros.  
Utilizando a mesma metodologia (ou uma similar), é possível reproduzir essa ferramenta para qualquer cidade do Brasil, basta obter os dados correspondentes do site IBGE (link no final do arquivo)

---

## Funcionalidades

- **Visualização geográfica:**  
  Mapa interativo dos setores censitários de Santos, com cores proporcionais ao total de pessoas por setor.

- **Consulta por logradouro:**  
  Filtre setores pelo(s) logradouro(s) desejado(s) e visualize estatísticas agregadas e individuais.

- **Seleção de Setores**
  A seleção dos setores é feita utilizando as ferramentas visíveis no canto superior direito do mapa.

- **Estatísticas detalhadas:**  
  Para cada setor selecionado, o app exibe:
  - Bairro, núcleo urbano, favela/comunidade, aglomerado e situação
  - Total de pessoas
  - Total de domicílios (particulares, ocupados, coletivos)
  - Média de moradores por domicílio
  - Percentual de domicílios ocupados
  - Área e densidade demográfica

- **Fonte dos dados:**  
  IBGE - Censo Demográfico 2022  
  [https://censo2022.ibge.gov.br/apps/pgi/#/mapa/](https://censo2022.ibge.gov.br/apps/pgi/#/mapa/)

## Estrutura dos dados

- **populacao:** Tabela com dados populacionais por setor censitário.
- **logradouro_setor:** Relação entre logradouros e setores.
- **setores_santos.geojson:** Arquivo GeoJSON com a geometria dos setores censitários.

---

## Desenvolvedores
João Pedro Paiva Cardoso
2025 - Centro de Pesquisas em Mobilidade Urbana (CPMU) - CET Santos
