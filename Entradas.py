import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, date
import calendar
import firebase_admin 
from firebase_admin import firestore
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
import qrcode
from io import BytesIO

# Configuração da página
st.set_page_config(
    page_title="Planetário De Brasília - Agendamento",
    page_icon="🔭",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# No início do arquivo, após as importações
# Dicionário com as traduções
TRANSLATIONS = {
    'pt': {
        'title': "Agendamento de Visita Planetário de Brasília",
        'important_info': "Informações Importantes",
        'info_bullets': [
            "As visitas são gratuitas",
            "Apresente o QR Code recebido por email na entrada",
            "Chegue com 15 minutos de antecedência",
            "Não é permitida a entrada após o início da sessão"
        ],
        'visit_date': "Data da Visita*",
        'visitors_number': "Número de Visitantes*",
        'main_visitor': "Dados do Visitante Principal",
        'visitor': "Dados do Visitante",
        'full_name': "Nome Completo*",
        'email': "Email*",
        'city': "Cidade*",
        'age': "Idade*",
        'state': "Estado*",
        'country': "País*",
        'gender': "Gênero*",
        'ethnicity': "Etnia*",
        'confirm_button': "Confirmar Agendamento",
        'same_email': "Mesmo email do visitante principal",
        'footer': "© 2024 Planetário De Brasília - Todos os direitos reservados"
    },
    'en': {
        'title': "Visit Scheduling",
        'important_info': "Important Information",
        'info_bullets': [
            "Visits are free",
            "Present the QR Code received by email at the entrance",
            "Arrive 15 minutes before",
            "Entry is not allowed after the session starts"
        ],
        'visit_date': "Visit Date*",
        'visitors_number': "Number of Visitors*",
        'main_visitor': "Main Visitor Information",
        'visitor': "Visitor Information",
        'full_name': "Full Name*",
        'email': "Email*",
        'city': "City*",
        'age': "Age*",
        'state': "State*",
        'country': "Country*",
        'gender': "Gender*",
        'ethnicity': "Ethnicity*",
        'confirm_button': "Confirm Scheduling",
        'same_email': "Same email as main visitor",
        'footer': "© 2024 Brasília Planetarium - All rights reserved"
    },
    'es': {
        'title': "Programación de Visitas",
        'important_info': "Información Importante",
        'info_bullets': [
            "Las visitas son gratuitas",
            "Presente el código QR recibido por correo electrónico en la entrada",
            "Llegue 15 minutos antes",
            "No se permite la entrada después del inicio de la sesión"
        ],
        'visit_date': "Fecha de Visita*",
        'visitors_number': "Número de Visitantes*",
        'main_visitor': "Información del Visitante Principal",
        'visitor': "Información del Visitante",
        'full_name': "Nombre Completo*",
        'email': "Correo Electrónico*",
        'city': "Ciudad*",
        'age': "Edad*",
        'state': "Estado*",
        'country': "País*",
        'gender': "Género*",
        'ethnicity': "Etnia*",
        'confirm_button': "Confirmar Programación",
        'same_email': "Mismo correo que el visitante principal",
        'footer': "© 2024 Planetario de Brasília - Todos los derechos reservados"
    }
}



# Função para obter texto traduzido
def t(key):
    return TRANSLATIONS[language][key]

# Estilo personalizado
st.markdown("""
    <style>
    .main {
        padding: 2rem;
    }
    .stButton>button {
        width: 100%;
        background-color: #2E4053;
        color: white;
        height: 3em;
        border-radius: 10px;
    }
    .stTextInput>div>div>input {
        border-radius: 5px;
    }
    .stSelectbox>div>div>select {
        border-radius: 5px;
    }
    .stNumberInput>div>div>input {
        border-radius: 5px;
    }
    h1 {
        color: #2E4053;
        text-align: center;
        margin-bottom: 2rem;
    }
    .info-box {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 10px;
        margin-bottom: 1rem;
    }
    </style>
""", unsafe_allow_html=True)

# Importar funções do módulo
from firebase_utils import initialize_firebase_from_json, initialize_firebase_from_env, adicionar_entrada, adicionar_entrada

# Configuração do Firebase
if not firebase_admin._apps:
    if os.path.exists('Planetario IAM Admin.json'):
        initialize_firebase_from_json()
    else:
        initialize_firebase_from_env()

try:
    db = firestore.client()
except Exception as e:
    st.error(f"Erro ao conectar ao banco de dados: {str(e)}")

# Dados auxiliares
estados_brasil = ["AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS", 
                 "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC", 
                 "SP", "SE", "TO"]

# Adicione o seletor de idioma no topo, centralizado
_, col_lang, _ = st.columns([4,1,4])
with col_lang:
    language = st.selectbox(
        "🌎 Language / Idioma",
        ['pt', 'en', 'es'],
        format_func=lambda x: {
            'pt': 'Português',
            'en': 'English',
            'es': 'Español'
        }[x],
        key="language_selector"
    )

# Atualizar o código existente para usar as traduções
col1, col2, col3 = st.columns([1,2,1])
with col2:
    st.title(t('title'))

    with st.expander(f"ℹ️ {t('important_info')}", expanded=True):
        st.info("\n".join([f"- {bullet}" for bullet in t('info_bullets')]))

    # Seleção de data e quantidade de visitantes
    col_data, col_qtd = st.columns(2)
    with col_data:
        data_visita = st.date_input(
            t('visit_date'),
            min_value=datetime.now().date(),
            help="Selecione a data desejada para sua visita"
        )
    with col_qtd:
        qtd_visitantes = st.number_input(
            t('visitors_number'),
            min_value=1,
            max_value=10,
            value=1,
            help="Máximo de 10 visitantes por agendamento"
        )

    # Formulário para cada visitante
    for i in range(qtd_visitantes):
        with st.container():
            st.markdown(f"### {t('main_visitor') if i == 0 else f'{t('visitor')} {i+1}'}")
            
            col1, col2 = st.columns(2)
            with col1:
                nome = st.text_input(t('full_name'), key=f"nome_{i}")
                email = st.text_input(
                    t('email'),
                    key=f"email_{i}",
                    disabled=i > 0 and st.checkbox(t('same_email'), key=f"mesmo_email_{i}")
                )
                cidade = st.text_input(t('city'), key=f"cidade_{i}")
            
            with col2:
                idade = st.number_input(t('age'), min_value=0, max_value=120, value=18, key=f"idade_{i}")
                estado = st.selectbox(t('state'), estados_brasil, key=f"estado_{i}")
                pais = st.text_input(t('country'), value="Brasil", key=f"pais_{i}")

            col3, col4 = st.columns(2)
            with col3:
                genero = st.selectbox(
                    t('gender'),
                    ["Masculino", "Feminino", "Não-binário", "Prefiro não informar"],
                    key=f"genero_{i}"
                )
            with col4:
                etnia = st.selectbox(
                    t('ethnicity'),
                    ["Branco", "Preto", "Pardo", "Amarelo", "Indígena", "Outro"],
                    key=f"etnia_{i}"
                )
            st.divider()

    

        # Botão de confirmação
    if st.button(t('confirm_button'), use_container_width=True):
        # Verificar se todos os campos obrigatórios foram preenchidos
        visitantes = []
        campos_vazios = []
        
        for i in range(qtd_visitantes):
            # Obtém os valores dos campos para cada visitante
            nome = st.session_state.get(f"nome_{i}")
            idade = st.session_state.get(f"idade_{i}")
            genero = st.session_state.get(f"genero_{i}")
            etnia = st.session_state.get(f"etnia_{i}")
            email = st.session_state.get(f"email_{i}")
            cidade = st.session_state.get(f"cidade_{i}")
            estado = st.session_state.get(f"estado_{i}")
            pais = st.session_state.get(f"pais_{i}")
            
            # Verifica campos vazios
            prefix = f"Visitante {i+1} - " if i > 0 else ""
            if not nome:
                campos_vazios.append(f"{prefix}Nome")
            if not email and (i == 0 or not st.session_state.get(f"mesmo_email_{i}")):
                campos_vazios.append(f"{prefix}Email")
            if not cidade:
                campos_vazios.append(f"{prefix}Cidade")
            
            # Se estiver usando o email do visitante principal
            if i > 0 and st.session_state.get(f"mesmo_email_{i}"):
                email = st.session_state.get("email_0")
            
            visitante = {
                "Nome": nome,
                "Idade": idade,
                "Gênero": genero,
                "Etnia": etnia,
                "Email": email,
                "Cidade": cidade,
                "Estado": estado,
                "País": pais,
                "Presenca": False
            }
            visitantes.append(visitante)
        
        # Validação de nomes completos
        nomes_invalidos = [v["Nome"] for v in visitantes if v["Nome"] and len(v["Nome"].strip().split()) < 2]
        
        if campos_vazios:
            st.error(f"Por favor, preencha os seguintes campos obrigatórios: {', '.join(campos_vazios)}")
        elif nomes_invalidos:
            st.error("Por favor, insira nomes completos (mínimo dois nomes) para todos os visitantes.")
        else:
            # Adicionar entradas ao banco de dados
            for visitante in visitantes:
                nova_entrada = {
                    **visitante,
                    "Dia da Visita": data_visita.isoformat(),
                    "Tipo de Visita": "Normal"
                }
                
                try:
                    visitante_id = adicionar_entrada(db, nova_entrada)
                    if visitante_id:
                        st.success(f"Agendamento confirmado para {visitante['Nome']}")
                    else:
                        st.error(f"Falha ao confirmar agendamento para {visitante['Nome']}")
                except Exception as e:
                    st.error(f"Erro ao processar agendamento: {str(e)}")
            
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

# Rodapé
st.markdown("""
    <div style='text-align: center; color: gray; padding: 20px;'>
        © 2024 Planetário De Brasília - Todos os direitos reservados
    </div>
""", unsafe_allow_html=True)