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
    qtd_alunos = st.number_input("Quantidade de Alunos*", min_value=1, value=1, key="qtd_alunos")
elif tipo_visita == "Normal":
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
elif tipo_visita == "Instituição":
    nome_instituicao = st.text_input("Nome da Instituição*", key="nome_instituicao")
    nome_responsavel = st.text_input("Responsável*", key="nome_responsavel_instituicao")
    email = st.text_input("Email do Responsável*", key="email_instituicao")
    qtd_visitantes = st.number_input("Quantidade de Visitantes*", min_value=1, value=1, key="qtd_visitantes_instituicao")

if tipo_visita != "Normal":
    cidade = st.text_input("Cidade*", key="cidade")
    estado = st.selectbox("Estado*", estados_brasil, key="estado")
    pais = st.text_input("País*", key="pais")

data_visita = st.date_input("Data da Visita*", min_value=datetime.now().date(), key="data_visita")
if isinstance(data_visita, datetime):
    data_visita = data_visita.date()

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
        "Data da Visita": data_visita,
        "Visita na Cúpula": visita_cupula
    }
    
    if tipo_visita == "Escola":
        campos_obrigatorios.update({
            "Nome da Escola": nome_escola,
            "Série Escolar": serie_escolar,
            "Ensino": tipo_ensino,
            "Tipo de Escola": tipo_escola,
            "Nome do Responsável": nome_responsavel,
            "Email do Responsável": email,
            "Quantidade de Alunos": qtd_alunos,
            "Cidade": cidade,
            "Estado": estado,
            "País": pais
        })
    elif tipo_visita == "Normal":
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
    elif tipo_visita == "Instituição":
        campos_obrigatorios.update({
            "Nome da Instituição": nome_instituicao,
            "Responsável": nome_responsavel,
            "Email do Responsável": email,
            "Quantidade de Visitantes": qtd_visitantes,
            "Cidade": cidade,
            "Estado": estado,
            "País": pais
        })
    
    if visita_cupula == "Sim":
        campos_obrigatorios["Horário da Sessão"] = sessao_selecionada

    campos_vazios = [campo for campo, valor in campos_obrigatorios.items() if not valor]
    
    if campos_vazios:
        st.error(f"Por favor, preencha os seguintes campos obrigatórios: {', '.join(campos_vazios)}")
    else:
        if tipo_visita == "Escola":
            nova_entrada = {
                "Nome da Escola": nome_escola,
                "Série Escolar": serie_escolar,
                "Ensino": tipo_ensino,
                "Tipo": tipo_escola,
                "Nome do Responsável": nome_responsavel,
                "Email do Responsável": email,
                "Quantidade de Alunos": qtd_alunos,
                "Cidade": cidade,
                "Estado": estado,
                "País": pais,
                "Dia da Visita": data_visita.isoformat(),
                "Cúpula": visita_cupula,
                "Tipo de Visita": tipo_visita
            }
            qtd_total = qtd_alunos
        elif tipo_visita == "Normal":
            nova_entrada = {
                "Visitantes": visitantes,
                "Dia da Visita": data_visita.isoformat(),
                "Cúpula": visita_cupula,
                "Tipo de Visita": tipo_visita
            }
            qtd_total = len(visitantes)
        else:  # Instituição
            nova_entrada = {
                "Nome da Instituição": nome_instituicao,
                "Responsável": nome_responsavel,
                "Email do Responsável": email,
                "Quantidade de Visitantes": qtd_visitantes,
                "Cidade": cidade,
                "Estado": estado,
                "País": pais,
                "Dia da Visita": data_visita.isoformat(),
                "Cúpula": visita_cupula,
                "Tipo de Visita": tipo_visita
            }
            qtd_total = qtd_visitantes
        
        if visita_cupula == "Sim" and sessao_selecionada:
            capacidade_restante = verificar_capacidade(db, sessao_selecionada, data_visita.isoformat())
            if qtd_total <= capacidade_restante:
                adicionar_entrada(db, nova_entrada)
                adicionar_ingresso(db, sessao_selecionada, data_visita.isoformat(), qtd_total, nome_escola or nome_instituicao or visitantes[0]["Nome"])
                st.success("Entrada adicionada com sucesso!")
                st.experimental_rerun()
            else:
                st.error(f"A capacidade da sessão {sessao_selecionada} é insuficiente. Restam {capacidade_restante} ingressos.")
        else:
            adicionar_entrada(db, nova_entrada)
            st.success("Entrada adicionada com sucesso!")
            st.experimental_rerun()
