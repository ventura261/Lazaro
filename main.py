# importar as bibliotecas
import streamlit as st
import pandas as pd
from binance.client import Client
from datetime import datetime, timedelta
import time

# inicialização da Binance (sem autenticação para dados públicos)
client = Client()

# Configuração da página
st.set_page_config(page_title="📈 Dashboard Cripto Binance", layout="wide")

# Estilo CSS com imagem de fundo
st.markdown(
    """
    <style>
    .stApp {
        background-image: url("fundo_cripto.jpg");
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
    }
    .block-container {
        background-color: rgba(255, 255, 255, 0.85);
        padding: 2rem;
        border-radius: 1rem;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# Função para obter o preço atual
@st.cache_data(ttl=60)
def obter_preco_atual(pares):
    precos = {}
    for par in pares:
        try:
            ticker = client.get_symbol_ticker(symbol=par)
            precos[par] = float(ticker['price'])
        except:
            precos[par] = None
    return precos

# Função para carregar dados históricos
@st.cache_data
def carregar_dados(pares, intervalo='1d', limite=1000):
    df_completo = pd.DataFrame()
    for par in pares:
        try:
            klines = client.get_klines(symbol=par, interval=intervalo, limit=limite)
            df = pd.DataFrame(klines, columns=[
                "timestamp", "Open", "High", "Low", "Close", "Volume",
                "Close time", "Quote asset volume", "Number of trades",
                "Taker buy base asset volume", "Taker buy quote asset volume", "Ignore"
            ])
            df["timestamp"] = pd.to_datetime(df["timestamp"], unit='ms')
            df.set_index("timestamp", inplace=True)
            df = df[["Close"]].astype(float)
            df.rename(columns={"Close": par}, inplace=True)
            df_completo = pd.concat([df_completo, df], axis=1)
            time.sleep(0.2)  # evitar rate limit
        except:
            continue
    return df_completo

# Lista de criptos
criptos = [
    "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT",
    "XRPUSDT", "ADAUSDT", "AVAXUSDT", "DOGEUSDT"
]

# Cabeçalho
st.title("📊 Dashboard de Criptomoedas (Binance)")
st.markdown("Acompanhe o desempenho histórico e atual de criptomoedas populares.")
st.divider()

# Preços atuais
st.subheader("💰 Preços em Tempo Quase-Real")
precos_atuais = obter_preco_atual(criptos[:6])
colunas = st.columns(3)

for i, (par, preco) in enumerate(precos_atuais.items()):
    with colunas[i % 3]:
        st.metric(label=f"**{par}**", value=f"US$ {preco:.2f}" if preco else "N/D")

st.divider()

# Filtros
st.sidebar.header("⚙️ Filtros")
dados = carregar_dados(criptos)

if dados.empty:
    st.error("❌ Nenhum dado foi carregado. Verifique sua conexão ou se os pares estão corretos.")
    st.stop()

lista_opcoes = dados.columns.tolist()
selecionadas = st.sidebar.multiselect("Escolha as criptomoedas", lista_opcoes, default=lista_opcoes[:3])

if not selecionadas:
    st.warning("Selecione pelo menos uma criptomoeda para visualizar.")
    st.stop()

dados = dados[selecionadas]
if len(selecionadas) == 1:
    dados = dados.rename(columns={selecionadas[0]: "Close"})

# Validação de datas
data_inicial = dados.index.min()
data_final = dados.index.max()

# Slider de data
intervalo = st.sidebar.slider(
    "📅 Intervalo de datas",
    min_value=data_inicial.to_pydatetime(),
    max_value=data_final.to_pydatetime(),
    value=(data_inicial.to_pydatetime(), data_final.to_pydatetime()),
    step=timedelta(days=1)
)

# Filtra dados
dados_filtrados = dados.loc[intervalo[0]:intervalo[1]]

# Gráfico de evolução
st.subheader("📈 Evolução dos Preços")
if dados_filtrados.dropna(how="all").empty:
    st.warning("🔍 Nenhum dado encontrado para o período selecionado.")
else:
    st.line_chart(dados_filtrados.dropna(how="all"), use_container_width=True)

    # Performance individual
    st.subheader("📊 Performance Individual")
    precos_iniciais = dados_filtrados.iloc[0]
    precos_finais = dados_filtrados.iloc[-1]
    retornos = precos_finais / precos_iniciais - 1
    retornos = retornos.replace([float('inf'), -float('inf')], 0).fillna(0)

    texto_performance = ""
    for par, retorno in retornos.items():
        cor = ":green" if retorno > 0 else ":red" if retorno < 0 else ""
        texto_performance += f"\n{par}: {cor}[{retorno:.1%}]"
    st.markdown(texto_performance)

    # Performance da carteira
    st.subheader("💼 Performance da Carteira")
    total_inicial = 1000 * len(retornos)
    total_final = (retornos + 1) * 1000
    retorno_carteira = total_final.sum() / total_inicial - 1
    cor_total = ":green" if retorno_carteira > 0 else ":red" if retorno_carteira < 0 else ""
    st.markdown(f"**Retorno total:** {cor_total}[{retorno_carteira:.1%}]")

    # Evolução da carteira
    norm = dados_filtrados.divide(dados_filtrados.iloc[0])
    norm = norm.replace([float("inf"), -float("inf")], 0).fillna(0)
    valores_carteira = norm.multiply(1000).sum(axis=1)

    st.subheader("📉 Evolução da Carteira")
    if valores_carteira.dropna().empty:
        st.warning("⚠️ Não há dados suficientes para calcular a evolução da carteira.")
    else:
        st.area_chart(valores_carteira, use_container_width=True)
