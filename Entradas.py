import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, date
import calendar
import firebase_admin
from firebase_admin import credentials, firestore
import os

# Importar funções do módulo
from firebase_utils import initialize_firebase_from_json, initialize_firebase_from_env, verificar_capacidade, adicionar_ingresso, carregar_dados, carregar_sessoes, adicionar_entrada, atualizar_nome_filme, atualizar_status_sessao, carregar_ingressos, adicionar_sessao, carregar_sessoes_disponiveis, verificar_existencia_documento, deletar_sessao


# Caminho para o arquivo de credenciais
cred_path = 'Planetario IAM Admin.json'

# Verifica se o app já foi inicializado
if not firebase_admin._apps:
    st.write("Inicializando Firebase...")
    if os.path.exists(cred_path):
        if not initialize_firebase_from_json():
            initialize_firebase_from_env()
    else:
        initialize_firebase_from_env()
else:
    st.info("Firebase já está inicializado.")

# Inicializa o Firestore
try:
    db = firestore.client()
    st.success("Firestore inicializado com sucesso!")
except Exception as e:
    st.error(f"Erro ao inicializar Firestore: {str(e)}")

# Dados auxiliares (estados do Brasil, etc.)
estados_brasil = ["AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS", "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO"]
dias_da_semana = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]
horarios_visitantes_semana = ["18:00"]
horarios_visitantes_fim_semana = ["11:00", "14:30", "16:00", "17:00", "18:00"]
horarios_escolas_semana = ["08:15", "09:30", "14:00", "15:15"]

# Título da aplicação
st.title("Sistema de Entradas do Planetário de Brasília")

st.header("Formulario de Visitação")

tipo_visita = st.radio("Tipo de Visita", ["Escola", "Normal", "Instituição"])

# Inicializar variáveis comuns
nome_escola, serie_escolar, tipo_ensino, tipo_escola = "", "", "", ""
nome_visitante, cidade, estado, pais = "", "", "", ""
nome_instituicao, nome_responsavel = "", ""
idade, etnia = "", ""
email = ""

if tipo_visita == "Escola":
    nome_escola = st.text_input("Nome da Escola*", key="nome_escola")
    serie_escolar = st.text_input("Série Escolar*", key="serie_escolar")
    tipo_ensino = st.selectbox("Ensino*", ["Maternal", "Fundamental I", "Fundamental II", "Médio", "Superior", "Outros"], key="tipo_ensino")
    tipo_escola = st.radio("Tipo*", ["Privada", "Pública"], key="tipo_escola")
    nome_responsavel = st.text_input("Nome do Responsável*", key="nome_responsavel_escola")
    email = st.text_input("Email do Responsável*", key="email_escola")
elif tipo_visita == "Normal":
    nome_visitante = st.text_input("Nome do Visitante*", key="nome_visitante")
    idade = st.number_input("Idade*", min_value=0, max_value=120, value=18, key="idade")
    etnia = st.selectbox("Etnia*", ["Branco", "Preto", "Pardo", "Amarelo", "Indígena", "Outro"], key="etnia")
    email = st.text_input("Email*", key="email_normal")
elif tipo_visita == "Instituição":
    nome_instituicao = st.text_input("Nome da Instituição*", key="nome_instituicao")
    nome_responsavel = st.text_input("Responsável*", key="nome_responsavel_instituicao")
    email = st.text_input("Email do Responsável*", key="email_instituicao")

cidade = st.text_input("Cidade*", key="cidade")
estado = st.selectbox("Estado*", estados_brasil, key="estado")
pais = st.text_input("País*", key="pais")

data_visita = st.date_input("Data da Visita*", min_value=datetime.now().date(), key="data_visita")
if isinstance(data_visita, datetime):
    data_visita = data_visita.date()

qtd_visitantes = st.number_input("Quantidade de Visitantes*", min_value=1, value=1, key="qtd_visitantes")

# Adicionar campos para visitantes adicionais
visitantes_adicionais = []
if qtd_visitantes > 1:
    st.subheader("Informações dos Visitantes Adicionais")
    for i in range(1, qtd_visitantes):
        st.markdown(f"**Visitante {i+1}**")
        nome_adicional = st.text_input(f"Nome do Visitante {i+1}*", key=f"nome_adicional_{i}")
        idade_adicional = st.number_input(f"Idade do Visitante {i+1}*", min_value=0, max_value=120, value=18, key=f"idade_adicional_{i}")
        etnia_adicional = st.selectbox(f"Etnia do Visitante {i+1}*", ["Branco", "Preto", "Pardo", "Amarelo", "Indígena", "Outro"], key=f"etnia_adicional_{i}")
        email_adicional = st.text_input(f"Email do Visitante {i+1}*", key=f"email_adicional_{i}")
        visitantes_adicionais.append({
            "Nome": nome_adicional,
            "Idade": idade_adicional,
            "Etnia": etnia_adicional,
            "Email": email_adicional
        })

visita_cupula = st.radio("Visita na Cúpula?*", ["Sim", "Não"], key="visita_cupula")

sessao_selecionada = None
if visita_cupula == "Sim":
    sessoes_disponiveis = carregar_sessoes_disponiveis(db, data_visita, tipo_visita)
    sessao_opcoes = [sessao['sessao'] for sessao in sessoes_disponiveis]
    
    if sessao_opcoes:
        sessao_selecionada = st.selectbox("Selecione o Horário da Sessão*", sessao_opcoes, key="sessao_selecionada")
        capacidade_restante = verificar_capacidade(db, sessao_selecionada, data_visita.isoformat())
        st.write(f"Capacidade restante para a sessão {sessao_selecionada}: {capacidade_restante} ingressos")
    else:
        st.warning("Não há sessões disponíveis para esta data.")
        sessao_selecionada = None

if st.button("Adicionar Entrada"):
    # Verificar se todos os campos obrigatórios foram preenchidos
    campos_obrigatorios = {
        "Cidade": cidade,
        "Estado": estado,
        "País": pais,
        "Data da Visita": data_visita,
        "Quantidade de Visitantes": qtd_visitantes,
        "Visita na Cúpula": visita_cupula,
        "Email": email
    }
    
    if tipo_visita == "Escola":
        campos_obrigatorios.update({
            "Nome da Escola": nome_escola,
            "Série Escolar": serie_escolar,
            "Ensino": tipo_ensino,
            "Tipo de Escola": tipo_escola,
            "Nome do Responsável": nome_responsavel
        })
    elif tipo_visita == "Normal":
        campos_obrigatorios.update({
            "Nome do Visitante": nome_visitante,
            "Idade": idade,
            "Etnia": etnia
        })
    elif tipo_visita == "Instituição":
        campos_obrigatorios.update({
            "Nome da Instituição": nome_instituicao,
            "Responsável": nome_responsavel
        })
    
    if visita_cupula == "Sim":
        campos_obrigatorios["Horário da Sessão"] = sessao_selecionada

    campos_vazios = [campo for campo, valor in campos_obrigatorios.items() if not valor]
    
    # Verificar campos dos visitantes adicionais
    for i, visitante in enumerate(visitantes_adicionais):
        if not all(visitante.values()):
            campos_vazios.append(f"Informações do Visitante {i+2}")
    
    if campos_vazios:
        st.error(f"Por favor, preencha os seguintes campos obrigatórios: {', '.join(campos_vazios)}")
    else:
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
            "Responsável": nome_responsavel,
            "Email": email,
            "Dia da Visita": data_visita.isoformat(),
            "Quantidade de Visitantes": qtd_visitantes,
            "Cúpula": visita_cupula,
            "Tipo de Visita": tipo_visita,
            "Visitantes Adicionais": visitantes_adicionais
        }
        
        if visita_cupula == "Sim" and sessao_selecionada:
            capacidade_restante = verificar_capacidade(db, sessao_selecionada, data_visita.isoformat())
            if qtd_visitantes <= capacidade_restante:
                adicionar_entrada(db, nova_entrada)
                adicionar_ingresso(db, sessao_selecionada, data_visita.isoformat(), qtd_visitantes, nome)
                st.success("Entrada adicionada com sucesso!")
                st.experimental_rerun()
            else:
                st.error(f"A capacidade da sessão {sessao_selecionada} é insuficiente. Restam {capacidade_restante} ingressos.")
        else:
            adicionar_entrada(db, nova_entrada)
            st.success("Entrada adicionada com sucesso!")
            st.experimental_rerun()