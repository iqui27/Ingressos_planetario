import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, date
import calendar
import firebase_admin
from firebase_admin import credentials, firestore
import os
import smtplib
import qrcode
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from io import BytesIO

# Adicione esta linha no início do seu script, logo após a importação do streamlit
st.set_page_config(initial_sidebar_state="collapsed")

# Importar funções do módulo
from firebase_utils import initialize_firebase_from_json, initialize_firebase_from_env, adicionar_entrada, adicionar_entrada

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
email_principal = ""
for i in range(qtd_visitantes):
    if i == 0:
        st.markdown("**Informações do Visitante**")
    else:
        st.markdown(f"**Informações do Visitante {i+1}**")
    
    nome_visitante = st.text_input(f"Nome{' do Visitante ' + str(i+1) if i > 0 else ''} (Nome completo, pelo menos dois nomes)*", key=f"nome_visitante_{i}")
    idade = st.number_input(f"Idade{' do Visitante ' + str(i+1) if i > 0 else ''}*", min_value=0, max_value=120, value=18, key=f"idade_{i}")
    genero = st.selectbox(f"Gênero{' do Visitante ' + str(i+1) if i > 0 else ''}*", ["Masculino", "Feminino", "Não-binário", "Prefiro não informar"], key=f"genero_{i}")
    etnia = st.selectbox(f"Etnia{' do Visitante ' + str(i+1) if i > 0 else ''}*", ["Branco", "Preto", "Pardo", "Amarelo", "Indígena", "Outro"], key=f"etnia_{i}")
    
    if i == 0:
        email_principal = st.text_input(f"Email{' do Visitante ' + str(i+1) if i > 0 else ''}*", key=f"email_{i}")
    else:
        usar_email_principal = st.checkbox(f"Usar o mesmo email do visitante principal para o Visitante {i+1}", key=f"usar_email_principal_{i}")
        if usar_email_principal:
            email = email_principal
        else:
            email = st.text_input(f"Email{' do Visitante ' + str(i+1) if i > 0 else ''}*", key=f"email_{i}")
    
    cidade = st.text_input(f"Cidade{' do Visitante ' + str(i+1) if i > 0 else ''}*", key=f"cidade_{i}")
    estado = st.selectbox(f"Estado{' do Visitante ' + str(i+1) if i > 0 else ''}*", estados_brasil, key=f"estado_{i}")
    pais = st.text_input(f"País{' do Visitante ' + str(i+1) if i > 0 else ''}*", key=f"pais_{i}")
    visitantes.append({
        "Nome": nome_visitante,
        "Idade": idade,
        "Gênero": genero,
        "Etnia": etnia,
        "Email": email if i > 0 else email_principal,
        "Cidade": cidade,
        "Estado": estado,
        "País": pais,
        "Presenca": False
    })

data_visita = st.date_input("Data da Visita*", min_value=datetime.now().date(), key="data_visita")

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
            f"{prefix}Gênero": visitante["Gênero"],
            f"{prefix}Etnia": visitante["Etnia"],
            f"{prefix}Email": visitante["Email"],
            f"{prefix}Cidade": visitante["Cidade"],
            f"{prefix}Estado": visitante["Estado"],
            f"{prefix}País": visitante["País"]
        })

    campos_vazios = [campo for campo, valor in campos_obrigatorios.items() if not valor]
    
    nomes_invalidos = [visitante["Nome"] for visitante in visitantes if len(visitante["Nome"].strip().split()) < 2]
    
    if campos_vazios:
        st.error(f"Por favor, preencha os seguintes campos obrigatórios: {', '.join(campos_vazios)}")
    elif nomes_invalidos:
        st.error(f"Por favor, insira nomes completos para os seguintes visitantes: {', '.join(nomes_invalidos)}")
    else:
        for visitante in visitantes:
            nova_entrada = {
                "Nome": visitante["Nome"],
                "Idade": visitante["Idade"],
                "Gênero": visitante["Gênero"],
                "Etnia": visitante["Etnia"],
                "Email": visitante["Email"],
                "Cidade": visitante["Cidade"],
                "Estado": visitante["Estado"],
                "País": visitante["País"],
                "Dia da Visita": data_visita.isoformat(),
                "Tipo de Visita": "Normal",
                "Presenca": False
            }
            visitante_id = adicionar_entrada(db, nova_entrada)
            
            if visitante_id:
                st.success(f"Entrada adicionada e email enviado para {visitante['Nome']}")
            else:
                st.error(f"Falha ao adicionar entrada para {visitante['Nome']}")
        # Exibir tela de agradecimento
        st.markdown("""
            <style>
            .thank-you {
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: black;
                color: white;
                display: flex;
                justify-content: center;
                
                align-items: center;
                font-size: 2em;
                z-index: 9999;
                text-align: center;
            }
            </style>
            <div class="thank-you">
                Obrigado pela sua visita!<br>
                Você receberá um email que deverá ser apresentado na recepção.
            </div>
            """, unsafe_allow_html=True)
        
        st.stop()