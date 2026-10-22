import json
from pathlib import Path
import streamlit as st

st.set_page_config(page_title="Assistant Aroéven | Directeurs 2026", page_icon="🧭", layout="centered")

st.markdown("""<style>
.block-container {max-width: 820px; padding-top: 2rem;}
.stButton > button {text-align:left; border-radius:12px; min-height:3.1rem; white-space:normal;}
.hero {padding:1.2rem 1.4rem; border-radius:16px; background:#0b5363; color:white; margin-bottom:1rem;}
.hero h1 {color:white; margin:0; font-size:1.7rem;}
.hero p {margin:.5rem 0 0; color:#e5f5f5;}
</style>""", unsafe_allow_html=True)

@st.cache_data
def charger_faq():
    return json.loads((Path(__file__).parent / "faq.json").read_text(encoding="utf-8"))

faq = charger_faq()
for cle in ("source", "rubrique", "question"):
    if cle not in st.session_state:
        st.session_state[cle] = None

def retour_accueil():
    st.session_state.update(source=None, rubrique=None, question=None)

def changer_source(valeur):
    st.session_state.update(source=valeur, rubrique=None, question=None)

def changer_rubrique(valeur):
    st.session_state.update(rubrique=valeur, question=None)

def changer_question(valeur):
    st.session_state.question = valeur

st.markdown('<div class="hero"><h1>🧭 Assistant des directeurs Aroéven</h1><p>Vos réponses 2026, en quelques clics • Sans IA • Sans saisie</p></div>', unsafe_allow_html=True)

if st.session_state.source is not None:
    st.button("🏠 Accueil", on_click=retour_accueil)

if st.session_state.source is None:
    st.subheader("Choisissez votre espace")
    for libelle, emoji in [("Nouveaux directeurs", "🌱"), ("Procédures directeurs", "📋")]:
        nb=sum(x["source"]==libelle for x in faq)
        st.button(f"{emoji} {libelle}  ·  {nb} questions", key=f"src-{libelle}", use_container_width=True, on_click=changer_source,args=(libelle,))

elif st.session_state.rubrique is None:
    st.caption(f"Espace : {st.session_state.source}")
    st.subheader("Choisissez une rubrique")
    rubriques=list(dict.fromkeys(x["rubrique"] for x in faq if x["source"]==st.session_state.source))
    for i,rubrique in enumerate(rubriques):
        nb=sum(x["source"]==st.session_state.source and x["rubrique"]==rubrique for x in faq)
        st.button(f"📁 {rubrique}  ·  {nb} questions", key=f"rub-{i}", use_container_width=True,on_click=changer_rubrique,args=(rubrique,))

else:
    st.caption(f"{st.session_state.source}  ›  {st.session_state.rubrique}")
    st.button("← Toutes les rubriques", on_click=changer_rubrique,args=(None,))
    questions=[x for x in faq if x["source"]==st.session_state.source and x["rubrique"]==st.session_state.rubrique]
    st.subheader("Choisissez une question")
    for i,item in enumerate(questions):
        st.button("💬 " + item["question"], key=f"q-{i}",use_container_width=True,on_click=changer_question,args=(i,))
    if st.session_state.question is not None:
        choix=st.session_state.question
        if 0<=choix<len(questions):
            item=questions[choix]
            st.divider()
            st.markdown("#### 💬 " + item["question"])
            st.info(item["reponse"])
            st.caption("Source : " + item["source"] + " (document fourni). Vérifier les consignes auprès de l'Aroéven, notamment en matière de réglementation ou de sécurité.")

st.divider()
st.caption("Aroéven Hauts-de-France • Assistant à navigation guidée • Informations issues des 2 FAQ 2026 • Aucun service d'IA ni base de données externe")
