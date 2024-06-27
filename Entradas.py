import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, date
import calendar
import firebase_admin
from firebase_admin import credentials, firestore
import time

# Load Firebase credentials from Streamlit secrets
firebase_credentials = st.secrets["firebase"]
# Check if the Firebase app is already initialized
if not firebase_admin._apps:
    cred = credentials.Certificate(firebase_credentials)
    firebase_admin.initialize_app(cred)

# Inicializa o Firestore
db = firestore.client()

# Dados auxiliares (estados do Brasil, regiões administrativas, etc.)
estados_brasil = ["AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS", "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO"]

# Função para converter documentos do Firestore em DataFrame
def records_to_dataframe(records):
    data = [doc.to_dict() for doc in records]
    df = pd.DataFrame(data)
    if 'Dia da Visita' in df.columns:
        df['Dia da Visita'] = pd.to_datetime(df['Dia da Visita']).dt.date
    return df

# Função para carregar dados do Firestore
def carregar_dados():
    docs = db.collection('Visitas').stream()
    df = records_to_dataframe(docs)
    df.fillna('', inplace=True)  # Substituir None por strings vazias
    if 'Dia da Visita' not in df.columns:
        st.warning("'Dia da Visita' não está presente nos dados carregados.")
        df['Dia da Visita'] = pd.NaT  # Preencher com NaT se a coluna não existir
    return df

def verificar_capacidade(sessao, data):
    docs = db.collection('Ingressos').where('sessao', '==', sessao).where('data', '==', data).stream()
    total_ingressos = sum(doc.to_dict()['qtd'] for doc in docs)
    return 80 - total_ingressos

# Função para adicionar ingressos
def adicionar_ingresso(sessao, data, qtd, nome):
    try:
        db.collection('Ingressos').add({
            'sessao': sessao,
            'data': data,
            'qtd': qtd,
            'nome': nome
        })
        st.success("Ingresso adicionado com sucesso!")
    except Exception as e:
        st.error(f"Erro ao adicionar ingresso: {e}")

# Função para carregar dados de ingressos por sessão
def carregar_ingressos(sessao, data):
    docs = db.collection('Ingressos').where('sessao', '==', sessao).where('data', '==', data).stream()
    return [doc.to_dict() for doc in docs]

def carregar_sessoes(data):
    docs = db.collection('Sessoes').where('data', '==', data).stream()
    sessoes = []
    for doc in docs:
        sessao = doc.to_dict()
        sessao['id'] = doc.id
        sessoes.append(sessao)
    return sessoes

def atualizar_status_sessao(sessao_id, bloqueada):
    try:
        db.collection('Sessoes').document(sessao_id).update({'bloqueada': bloqueada})
        st.success("Status da sessão atualizado com sucesso!")
    except Exception as e:
        st.error(f"Erro ao atualizar status da sessão: {e}")

def carregar_sessoes_disponiveis(data, tipo_visita):
    dia_da_semana = dias_da_semana[data.weekday()]
    if tipo_visita == "Normal":
        horarios_sessoes = horarios_visitantes_semana if dia_da_semana in ["Terça", "Quarta", "Quinta", "Sexta"] else horarios_visitantes_fim_semana
    else:
        horarios_sessoes = horarios_escolas_semana if dia_da_semana in ["Terça", "Quarta", "Quinta", "Sexta"] else []

    sessoes = carregar_sessoes(data.isoformat())
    sessoes_disponiveis = [sessao for sessao in sessoes if not sessao.get('bloqueada', False) and sessao['sessao'] in horarios_sessoes]
    return sessoes_disponiveis

def adicionar_sessao(sessao, data, capacidade=80):
    try:
        db.collection('Sessoes').add({
            'sessao': sessao,
            'data': data,
            'bloqueada': False,
            'capacidade': capacidade,
            'ingressos': []
        })
        st.success(f"Sessão {sessao} adicionada para {data}!")
    except Exception as e:
        st.error(f"Erro ao adicionar sessão: {e}")

# Dados auxiliares
dias_da_semana = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]

# Horários das sessões
horarios_visitantes_semana = ["18:00"]
horarios_visitantes_fim_semana = ["11:00", "14:30", "16:00", "17:00", "18:00"]
horarios_escolas_semana = ["08:15", "09:30", "14:00", "15:15"]

# Função para adicionar uma nova entrada no Firestore
def adicionar_entrada(entrada):
    try:
        db.collection('Visitas').add(entrada)
        st.success("Entrada adicionada com sucesso!")
    except Exception as e:
        st.error(f"Erro ao adicionar entrada: {e}")
        st.write(e)  # Mensagem de depuração

# Título da aplicação
st.title("Sistema de Entradas do Planetário de Brasília")

# Controle de estado para navegação
if 'page' not in st.session_state:
    st.session_state['page'] = 'form'

def go_to_thank_you_page():
    st.session_state['page'] = 'thank_you'

# Página de agradecimento
def thank_you_page():
    st.header("Obrigado pela Visita!")
    st.write("Sua visita foi registrada com sucesso. Aguardamos você em nosso planetário!")

# Página de formulário
def form_page():
    st.header("Formulário de Visitação")
    
    tipo_visita = st.radio("Tipo de Visita", ["Escola", "Normal", "Instituição"])

    # Inicializar variáveis comuns
    nome_escola, serie_escolar, tipo_ensino, tipo_escola = "", "", "", ""
    nome_visitante, cidade, estado, pais = "", "", "", ""
    nome_instituicao, nome_responsavel = "", ""

    if tipo_visita == "Escola":
        nome_escola = st.text_input("Nome da Escola")
        serie_escolar = st.text_input("Série Escolar")
        tipo_ensino = st.selectbox("Ensino", ["Maternal", "Fundamental I", "Fundamental II", "Médio", "Superior", "Outros"])
        tipo_escola = st.radio("Tipo", ["Privada", "Pública"])
        cidade = st.text_input("Cidade")
        estado = st.selectbox("Estado", estados_brasil)
        pais = st.text_input("País")
    elif tipo_visita == "Normal":
        nome_visitante = st.text_input("Nome do Visitante")
        cidade = st.text_input("Cidade")
        estado = st.selectbox("Estado", estados_brasil)
        pais = st.text_input("País")
    elif tipo_visita == "Instituição":
        nome_instituicao = st.text_input("Nome da Instituição")
        nome_responsavel = st.text_input("Responsável")
        cidade = st.text_input("Cidade")
        estado = st.selectbox("Estado", estados_brasil)
        pais = st.text_input("País")

    data_visita = st.date_input("Data da Visita", min_value=datetime.now().date())
    if isinstance(data_visita, datetime):
        data_visita = data_visita.date()

    qtd_visitantes = st.number_input("Quantidade de Visitantes", min_value=1, value=1)
    visita_cupula = st.radio("Visita na Cúpula?", ["Sim", "Não"])

    sessao_selecionada = None
    if visita_cupula == "Sim":
        sessoes_disponiveis = carregar_sessoes_disponiveis(data_visita, tipo_visita)
        sessao_opcoes = [sessao['sessao'] for sessao in sessoes_disponiveis]
        
        if sessao_opcoes:
            sessao_selecionada = st.selectbox("Selecione o Horário da Sessão", sessao_opcoes)
            capacidade_restante = verificar_capacidade(sessao_selecionada, data_visita.isoformat())
            st.write(f"Capacidade restante para a sessão {sessao_selecionada}: {capacidade_restante} ingressos")
        else:
            st.warning("Não há sessões disponíveis para esta data.")
            sessao_selecionada = None

    if st.button("Adicionar Entrada"):
        nome = nome_escola if tipo_visita == "Escola" else (nome_instituicao if tipo_visita == "Instituição" else nome_visitante)
        
        nova_entrada = {
            "Nome da Escola": nome_escola if tipo_visita == "Escola" else "",
            "Série Escolar": serie_escolar if tipo_visita == "Escola" else "",
            "Ensino": tipo_ensino if tipo_visita == "Escola" else "",
            "Tipo": tipo_escola if tipo_visita == "Escola" else "",
            "Nome": nome_visitante if tipo_visita == "Normal" else "",
            "Cidade": cidade,
            "Estado": estado,
            "País": pais,
            "Nome da Instituição": nome_instituicao if tipo_visita == "Instituição" else "",
            "Responsável": nome_responsavel if tipo_visita == "Instituição" else "",
            "Dia da Visita": data_visita.isoformat(),
            "Quantidade de Visitantes": qtd_visitantes,
            "Cúpula": visita_cupula,
            "Tipo de Visita": tipo_visita
        }
        
        if visita_cupula == "Sim" and sessao_selecionada:
            capacidade_restante = verificar_capacidade(sessao_selecionada, data_visita.isoformat())
            if qtd_visitantes <= capacidade_restante:
                adicionar_entrada(nova_entrada)  # Adicionar a entrada antes da verificação da cúpula
                adicionar_ingresso(sessao_selecionada, data_visita.isoformat(), qtd_visitantes, nome)
                time.sleep(1)
                go_to_thank_you_page()
                st.experimental_rerun()       
            else:
                st.error(f"A capacidade da sessão {sessao_selecionada} é insuficiente. Restam {capacidade_restante} ingressos.")
        else:
            adicionar_entrada(nova_entrada)
            time.sleep(1)
            go_to_thank_you_page()
            st.experimental_rerun()

# Lógica para mostrar a página correta
if st.session_state['page'] == 'form':
    form_page()
elif st.session_state['page'] == 'thank_you':
    thank_you_page()
