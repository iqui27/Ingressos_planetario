import firebase_admin
from firebase_admin import credentials, firestore
import os
import streamlit as st
import pandas as pd
import smtplib
import qrcode
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from io import BytesIO
import traceback
import sys


# Caminho para o arquivo de credenciais
cred_path = 'Planetario IAM Admin.json'

def initialize_firebase_from_json():
    try:
        # Cria o objeto de credenciais
        cred = credentials.Certificate(cred_path)
        
        # Inicializa o app do Firebase
        firebase_admin.initialize_app(cred)
        
        st.success("Firebase inicializado com sucesso a partir do JSON!")
        return True
    except Exception as e:
        st.error(f"Erro ao inicializar Firebase a partir do JSON: {str(e)}")
        return False

def initialize_firebase_from_env():
    # Verificar se todas as variáveis de ambiente estão definidas
    required_vars = [
        "type", "project_id", "private_key_id", "private_key", "client_email",
        "client_id", "auth_uri", "token_uri", "auth_provider_x509_cert_url",
        "client_x509_cert_url", "universe_domain"
    ]

    missing_vars = [var for var in required_vars if os.environ.get(var) is None]

    if missing_vars:
        st.error(f"As seguintes variáveis de ambiente estão faltando: {', '.join(missing_vars)}")
        return False
    else:
        st.write("Todas as variáveis de ambiente necessárias estão presentes.")
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

            st.write("Credenciais do Firebase carregadas com sucesso.")
            # Cria o objeto de credenciais
            cred = credentials.Certificate(cred_dict)
            
            # Inicializa o app do Firebase
            firebase_admin.initialize_app(cred)
            
            st.success("Firebase inicializado com sucesso a partir das variáveis de ambiente!")
            return True
        except Exception as e:
            st.error(f"Erro ao inicializar Firebase a partir das variáveis de ambiente: {str(e)}")
            return False

def records_to_dataframe(records):
    data = [doc.to_dict() for doc in records]
    df = pd.DataFrame(data)
    if 'Dia da Visita' in df.columns:
        df['Dia da Visita'] = pd.to_datetime(df['Dia da Visita']).dt.date
    return df

def verificar_capacidade(db,sessao, data):
    docs = db.collection('Ingressos').where('sessao', '==', sessao).where('data', '==', data).stream()
    total_ingressos = sum(doc.to_dict()['qtd'] for doc in docs)
    return 80 - total_ingressos

def adicionar_ingresso(db,sessao, data, qtd, nome):
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

def carregar_dados(db):
    docs = db.collection('Visitas').stream()
    df = records_to_dataframe(docs)
    df.fillna('', inplace=True)
    if 'Dia da Visita' not in df.columns:
        st.warning("'Dia da Visita' não está presente nos dados carregados.")
        df['Dia da Visita'] = pd.NaT
    return df

def verificar_existencia_documento(db,sessao_id):
    doc_ref = db.collection('sessoes').document(sessao_id)
    doc = doc_ref.get()
    return doc.exists

def atualizar_nome_filme(db,sessao_id, nome_filme):
    db.collection('sessoes').document(sessao_id).update({'nome_filme': nome_filme})

def carregar_ingressos(db, sessao, data):
    docs = db.collection('Ingressos').where('sessao', '==', sessao).where('data', '==', data).stream()
    return [doc.to_dict() for doc in docs]

def carregar_sessoes(db, data):
    docs = db.collection('sessoes').where('data', '==', data).stream()
    sessoes = []
    for doc in docs:
        sessao = doc.to_dict()
        sessao['id'] = doc.id
        sessoes.append(sessao)
    return sessoes

def atualizar_status_sessao(db,sessao_id, bloqueada):
    try:
        db.collection('sessoes').document(sessao_id).update({'bloqueada': bloqueada})
        st.success("Status da sessão atualizado com sucesso!")
    except Exception as e:
        st.error(f"Erro ao atualizar status da sessão: {e}")

def carregar_sessoes_disponiveis(db, data, tipo_visita):
    dias_da_semana = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]
    horarios_visitantes_semana = ["18:00"]
    horarios_visitantes_fim_semana = ["11:00", "14:30", "16:00", "17:00", "18:00"]
    horarios_escolas_semana = ["08:15", "09:30", "14:00", "15:15"]
    
    dia_da_semana = dias_da_semana[data.weekday()]
    if tipo_visita == "Normal":
        horarios_sessoes = horarios_visitantes_semana if dia_da_semana in ["Terça", "Quarta", "Quinta", "Sexta"] else horarios_visitantes_fim_semana
    else:
        horarios_sessoes = horarios_escolas_semana if dia_da_semana in ["Terça", "Quarta", "Quinta", "Sexta"] else []

    sessoes = carregar_sessoes(db,data.isoformat())
    sessoes_disponiveis = [sessao for sessao in sessoes if not sessao.get('bloqueada', False) and sessao['sessao'] in horarios_sessoes]
    return sessoes_disponiveis

def adicionar_sessao(db, horario, data, nome_filme=None):
    try:
        sessao_ref = db.collection('sessoes').document()
        sessao_id = sessao_ref.id
        sessao_ref.set({
            'id': sessao_id,
            'sessao': horario,
            'data': data,
            'nome_filme': nome_filme,
            'bloqueada': False,
            'capacidade_restante': 80
        })
        st.success(f"Sessão {horario} adicionada com sucesso!")
    except Exception as e:
        st.error(f"Erro ao adicionar sessão: {e}")

def gerar_qr_code(visitante_id):
    # Cria a URL completa para marcar presença
    base_url = "https://ingressosplanetario-production.up.railway.app"
    presenca_url = f"{base_url}/marcar_presenca?id={visitante_id}"
    
    # Gera o QR code
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(presenca_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Converte a imagem para bytes
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    img_bytes = buffered.getvalue()
    
    return img_bytes

def enviar_email(email_destino, subject, body, qr_code):
    sender_email = "planetariodebrasilia@gmail.com"
    sender_password = "cmjr hfxv wogp dxav"

    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = email_destino
    msg['Subject'] = subject

    msg.attach(MIMEText(body, 'plain'))

    # Anexar o QR code ao email
    image = MIMEImage(qr_code, name="qrcode.png")
    msg.attach(image)

    try:
        st.write(f"Tentando enviar e-mail para {email_destino}")
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, email_destino, msg.as_string())
        st.success(f"Email enviado com sucesso para {email_destino}")
    except smtplib.SMTPAuthenticationError as e:
        error_code = e.smtp_code
        error_message = e.smtp_error
        st.error(f"Erro de autenticação. Código: {error_code}, Mensagem: {error_message}")
    except smtplib.SMTPException as e:
        st.error(f"Erro SMTP ao enviar e-mail: {str(e)}")
        st.error(f"Tipo de erro: {type(e).__name__}")
        st.error(f"Argumentos do erro: {e.args}")
    except Exception as e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        st.error(f"Erro inesperado ao enviar e-mail: {str(e)}")
        st.error(f"Tipo de erro: {exc_type.__name__}")
        st.error(f"Argumentos do erro: {exc_value.args}")
        st.error("Traceback completo:")
        st.error(traceback.format_exc())
    
    return False  # Retorna False se o email não foi enviado com sucesso

def adicionar_entrada(db, entrada):
    try:
        st.write("Iniciando adição de entrada...")
        # Adiciona a entrada e obtém a referência do documento
        doc_ref = db.collection('Visitas').add(entrada)
        
        # Obtém o ID do documento
        visitante_id = doc_ref[1].id
        
        # Gera o QR code
        qr_code = gerar_qr_code(visitante_id)
        st.write("QR code gerado")
        
        # Prepara o corpo do email
        body = f"""
        Obrigado por se registrar para a visita.

        Aqui estão os detalhes da sua visita:
        Nome: {entrada['Nome']}
        Idade: {entrada['Idade']}
        Gênero: {entrada['Gênero']}
        Etnia: {entrada['Etnia']}
        Email: {entrada['Email']}
        Cidade: {entrada['Cidade']}
        Estado: {entrada['Estado']}
        País: {entrada['País']}
        Dia da Visita: {entrada['Dia da Visita']}

        Anexado está o QR code para validação. Use este QR code para registrar sua presença na recepção.
        """
        
        st.write("Preparando para enviar e-mail...")
        # Envia o email
        email_enviado = enviar_email(entrada['Email'], 'Confirmação de Visita', body, qr_code)
        
        if email_enviado:
            st.success("Entrada adicionada com sucesso e email enviado!")
        else:
            st.warning("Entrada adicionada com sucesso, mas houve um problema ao enviar o email.")
        
        return visitante_id
    except Exception as e:
        st.error(f"Erro ao adicionar entrada: {e}")
        st.error(traceback.format_exc())
        return None

def deletar_sessao(db, sessao_id):
    try:
        db.collection('sessoes').document(sessao_id).delete()
        st.success("Sessão apagada com sucesso!")
    except Exception as e:
        st.error(f"Erro ao apagar sessão: {e}")

def marcar_presenca(db, visitante_id):
    try:
        # Referência para o documento do visitante
        visitante_ref = db.collection('Visitas').document(visitante_id)
        
        visitante_ref.update({'Presenca': True})
        
        return True, "Presença marcada com sucesso!"
    except Exception as e:
        return False, f"Erro ao marcar presença: {str(e)}"
