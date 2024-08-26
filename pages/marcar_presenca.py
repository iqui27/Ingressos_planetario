import streamlit as st
from firebase_utils import initialize_firebase_from_json, initialize_firebase_from_env, marcar_presenca
import firebase_admin
from firebase_admin import firestore
import os

# Inicializar o Firebase
if not firebase_admin._apps:
    cred_path = 'Planetario IAM Admin.json'
    if os.path.exists(cred_path):
        initialize_firebase_from_json()
    else:
        initialize_firebase_from_env()

# Inicializar o Firestore
db = firestore.client()

# Obter o ID do visitante da URL
visitante_id = st.experimental_get_query_params().get("id", [None])[0]

if visitante_id:
    sucesso, mensagem = marcar_presenca(db, visitante_id)
    if sucesso:
        st.success(mensagem)
    else:
        st.error(mensagem)
else:
    st.error("ID do visitante não fornecido.")