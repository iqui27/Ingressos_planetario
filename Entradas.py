import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, date
import calendar
import firebase_admin
from firebase_admin import credentials, firestore
import os

# Verifica se o app já foi inicializado
if not firebase_admin._apps:
    try:
        # Cria um dicionário com as credenciais do Firebase usando variáveis de ambiente
        cred_dict = {
            "type": os.environ.get("type"),
            "project_id": os.environ.get("project_id"),
            "private_key_id": os.environ.get("private_key_id"),
            "private_key": os.environ.get("private_key").replace("\\n", "\n"),  # Substitui \\n por \n
            "client_email": os.environ.get("client_email"),
            "client_id": os.environ.get("client_id"),
            "auth_uri": os.environ.get("auth_uri"),
            "token_uri": os.environ.get("token_uri"),
            "auth_provider_x509_cert_url": os.environ.get("auth_provider_x509_cert_url"),
            "client_x509_cert_url": os.environ.get("client_x509_cert_url"),
            "universe_domain": os.environ.get("universe_domain")
        }
        
        # Cria o objeto de credenciais
        cred = credentials.Certificate(cred_dict)
        
        # Inicializa o app do Firebase
        firebase_admin.initialize_app(cred)
        
        st.success("Firebase inicializado com sucesso!")
    except Exception as e:
        st.error(f"Erro ao inicializar Firebase: {str(e)}")
else:
    st.info("Firebase já está inicializado.")

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
        capacidade_restante = verificar_capacidade(sessao, data)
        if qtd <= capacidade_restante:
            db.collection('Ingressos').add({
                'sessao': sessao,
                'data': data,
                'qtd': qtd,
                'nome': nome
            })
            st.success("Ingresso adicionado com sucesso!")
        else:
            st.error(f"A capacidade da sessão {sessao} é insuficiente. Restam {capacidade_restante} ingressos.")
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

# Formulário de Visitação
st.header("Formulario de Visitação")

tipo_visita = st.radio("Tipo de Visita", ["Escola", "Normal", "Instituição"])

# Inicializar variáveis comuns
nome_escola, serie_escolar, tipo_ensino, tipo_escola = "", "", "", ""
nome_visitante, cidade, estado, pais = "", "", "", ""
nome_instituicao, nome_responsavel = "", ""
idade, etnia = "", ""

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
    idade = st.number_input("Idade", min_value=0, max_value=120, value=18)
    etnia = st.selectbox("Etnia", ["Branco", "Preto", "Pardo", "Amarelo", "Indígena", "Outro"])
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
        "Idade": idade if tipo_visita == "Normal" else "",
        "Etnia": etnia if tipo_visita == "Normal" else "",
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
    
    entrada_adicionada = False
    if visita_cupula == "Sim" and sessao_selecionada:
        capacidade_restante = verificar_capacidade(sessao_selecionada, data_visita.isoformat())
        if qtd_visitantes <= capacidade_restante:
            adicionar_entrada(nova_entrada)
            adicionar_ingresso(sessao_selecionada, data_visita.isoformat(), qtd_visitantes, nome)
            entrada_adicionada = True
        else:
            st.error(f"A capacidade da sessão {sessao_selecionada} é insuficiente. Restam {capacidade_restante} ingressos.")
    else:
        adicionar_entrada(nova_entrada)
        entrada_adicionada = True
    
    if entrada_adicionada:
        st.markdown(
            """
            <style>
            .stApp {
                background-color: black;
            }
            </style>
            """,
            unsafe_allow_html=True
        )
        st.markdown(
            """
            <div style="display: flex; justify-content: center; align-items: center; height: 100vh;">
                <h1 style="color: white; text-align: center;">Obrigado por enviar seus dados!</h1>
            </div>
            """,
            unsafe_allow_html=True
        )
        st.balloons()