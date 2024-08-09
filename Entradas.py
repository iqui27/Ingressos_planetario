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

# Importar funções do módulo
from firebase_utils import initialize_firebase_from_json, initialize_firebase_from_env, adicionar_entrada

# Caminho para o arquivo de credenciais
cred_path = 'Planetario IAM Admin.json'

def enviar_email(email_destino, subject, body, qr_img):
    sender_email = "planetariodebrasilia@gmail.com"
    sender_password = "cmjr hfxv wogp dxav"

    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = email_destino
    msg['Subject'] = subject

    msg.attach(MIMEText(body, 'plain'))

    # Anexar a imagem do QR code
    img_byte_arr = BytesIO()
    qr_img.save(img_byte_arr, format='PNG')
    img_byte_arr.seek(0)
    img = MIMEImage(img_byte_arr.read(), name="qrcode.png")
    msg.attach(img)

    try:
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, email_destino, msg.as_string())
            st.success(f"Email enviado com sucesso para {email_destino}")
    except Exception as e:
        st.error(f"Erro ao enviar email: {str(e)}")

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

# Função para marcar presença
def marcar_presenca(nome):
    visitante_ref = db.collection('Visitas').document(nome)
    if visitante_ref.get().exists:
        visitante_ref.update({'Presenca': True})
        return f"Presença marcada para {nome}"
    else:
        return f"Visitante {nome} não encontrado"

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
    
    nome_visitante = st.text_input(f"Nome{' do Visitante ' + str(i+1) if i > 0 else ''} (Nome completo, pelo menos dois nomes)*", key=f"nome_visitante_{i}")
    idade = st.number_input(f"Idade{' do Visitante ' + str(i+1) if i > 0 else ''}*", min_value=0, max_value=120, value=18, key=f"idade_{i}")
    etnia = st.selectbox(f"Etnia{' do Visitante ' + str(i+1) if i > 0 else ''}*", ["Branco", "Preto", "Pardo", "Amarelo", "Indígena", "Outro"], key=f"etnia_{i}")
    email = st.text_input(f"Email{' do Visitante ' + str(i+1) if i > 0 else ''}*", key=f"email_{i}")
    cidade = st.text_input(f"Cidade{' do Visitante ' + str(i+1) if i > 0 else ''}*", key=f"cidade_{i}")
    estado = st.selectbox(f"Estado{' do Visitante ' + str(i+1) if i > 0 else ''}*", estados_brasil, key=f"estado_{i}")
    pais = st.text_input(f"País{' do Visitante ' + str(i+1) if i > 0 else ''}*", key=f"pais_{i}")
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
                "Etnia": visitante["Etnia"],
                "Email": visitante["Email"],
                "Cidade": visitante["Cidade"],
                "Estado": visitante["Estado"],
                "País": visitante["País"],
                "Dia da Visita": data_visita.isoformat(),
                "Tipo de Visita": "Normal"
            }
            adicionar_entrada(db, nova_entrada)
            
            # Gerar QR code com URL
            url = f"https://iqui27-planetario-ingressos-planets-c3ddya.streamlit.app/?nome={visitante['Nome']}"
            qr_img = qrcode.make(url)
            
            # Corpo do email
            body = f"""
            Obrigado por se registrar para a visita.

            Aqui estão os detalhes da sua visita:
            Nome: {visitante['Nome']}
            Idade: {visitante['Idade']}
            Etnia: {visitante['Etnia']}
            Email: {visitante['Email']}
            Cidade: {visitante['Cidade']}
            Estado: {visitante['Estado']}
            País: {visitante['País']}
            Dia da Visita: {data_visita.isoformat()}

            Anexado está o QR code para validação. Use este QR code para registrar sua presença na recepção.
            """
            
            # Enviar email com QR code
            enviar_email(visitante['Email'], 'Confirmação de Visita', body, qr_img)
        
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