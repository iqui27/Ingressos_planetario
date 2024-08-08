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

st.header("Formulario de Visitação")

# Removido tipo de visita, deixando apenas visitante

qtd_visitantes = st.number_input("Quantidade de Visitantes*", min_value=1, value=1, key="qtd_visitantes")

visitantes = []
for i in range(qtd_visitantes):
    if i == 0:
        st.markdown("**Informações do Visitante**")
    else:
        st.markdown(f"**Informações do Visitante {i+1}**")
    
    nome_visitante = st.text_input(f"Nome{'do Visitante ' + str(i+1) if i > 0 else ''}*", key=f"nome_visitante_{i}")
    idade = st.number_input(f"Idade{'do Visitante ' + str(i+1) if i > 0 else ''}*", min_value=0, max_value=120, value=18, key=f"idade_{i}")
    etnia = st.selectbox(f"Etnia{'do Visitante ' + str(i+1) if i > 0 else ''}*", ["Branco", "Preto", "Pardo", "Amarelo", "Indígena", "Outro"], key=f"etnia_{i}")
    email = st.text_input(f"Email{'do Visitante ' + str(i+1) if i > 0 else ''}*", key=f"email_{i}")
    cidade = st.text_input(f"Cidade{'do Visitante ' + str(i+1) if i > 0 else ''}*", key=f"cidade_{i}")
    estado = st.selectbox(f"Estado{'do Visitante ' + str(i+1) if i > 0 else ''}*", estados_brasil, key=f"estado_{i}")
    pais = st.text_input(f"País{'do Visitante ' + str(i+1) if i > 0 else ''}*", key=f"pais_{i}")
    visitantes.append({
        "Nome": nome_visitante,
        "Idade": idade,
        "Etnia": etnia,
        "Email": email,
        "Cidade": cidade,
        "Estado": estado,
        "País": pais
    })

data_visita = st.date_input("Data da Visita*", min_value=datetime.now().date(), key="data_visita")
if isinstance(data_visita, datetime):
    data_visita = data_visita.date()

if st.button("Adicionar Entrada"):
    # Verificar se todos os campos obrigatórios foram preenchidos
    campos_obrigatorios = {
        "Data da Visita": data_visita,
    }
    
    for i, visitante in enumerate(visitantes):
        prefix = f"Visitante {i+1} - " if i > 0 else ""
        campos_obrigatorios.update({
            f"{prefix}Nome": visitante["Nome"],
            f"{prefix}Idade": visitante["Idade"],
            f"{prefix}Etnia": visitante["Etnia"],
            f"{prefix}Email": visitante["Email"],
            f"{prefix}Cidade": visitante["Cidade"],
            f"{prefix}Estado": visitante["Estado"],
            f"{prefix}País": visitante["País"]
        })

    campos_vazios = [campo for campo, valor in campos_obrigatorios.items() if not valor]
    
    if campos_vazios:
        st.error(f"Por favor, preencha os seguintes campos obrigatórios: {', '.join(campos_vazios)}")
    else:
        nova_entrada = {
            "Visitantes": visitantes,
            "Dia da Visita": data_visita.isoformat(),
            "Tipo de Visita": "Normal"
        }
        qtd_total = len(visitantes)
        
        adicionar_entrada(db, nova_entrada)
        st.success("Entrada adicionada com sucesso!")
        st.experimental_rerun()