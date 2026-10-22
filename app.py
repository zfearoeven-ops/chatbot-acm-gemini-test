"""Assistant Aroéven, navigation ludique 100 % par boutons, sans IA."""
import base64
import json
import re
import unicodedata
from pathlib import Path

import streamlit as st

st.set_page_config(page_title="Mon copilote Aroéven", page_icon="🌈", layout="centered")

st.markdown(
    """
<style>
.block-container {max-width:880px;padding-top:1.25rem;padding-bottom:3rem;}
.hero {padding:1.4rem 1.5rem;border-radius:22px;background:linear-gradient(125deg,#0a0a0a,#1c1c1c 26%,#087d7c 72%,#205fb1);color:#fff;margin-bottom:1.1rem;}
.hero-inner {display:flex;align-items:center;gap:1.2rem;flex-wrap:wrap;}
.hero-logo-wrap {background:rgba(255,255,255,.06);padding:.5rem .7rem;border-radius:18px;display:flex;align-items:center;justify-content:center;}
.hero-logo {width:220px;max-width:100%;height:auto;display:block;border-radius:12px;}
.hero-copy {flex:1;min-width:240px;}
.hero h1 {color:#fff;font-size:2rem;line-height:1.25;margin:0;}
.hero p {color:#f1ffff;margin:.55rem 0 0;}
.stButton>button {min-height:3.1rem;white-space:normal;text-align:left;border-radius:15px;font-weight:570;}
.bubble-q {background:#e8f4ff;color:#183b55;padding:.95rem 1.1rem;border-radius:19px 19px 5px 19px;margin:.6rem 0 .75rem 12%;}
.bubble-a {background:#eff8f3;color:#1e3930;padding:1.1rem 1.2rem;border-radius:19px 19px 19px 5px;margin:.6rem 12% .9rem 0;line-height:1.65;overflow-wrap:break-word;}
.small-label {color:#60747e;font-size:.85rem;font-weight:600;margin-bottom:.35rem;}
.permanence {background:#fff8e8;color:#332b1d;border:1px solid #e9cf93;border-left:5px solid #d5a33b;border-radius:16px;padding:1rem 1.25rem;margin:0 0 1.25rem;line-height:1.6;}
.permanence h3 {font-size:1.13rem;color:#332b1d;margin:0 0 .5rem;}
.permanence p {margin:.45rem 0;}
.permanence .telephone {font-weight:700;margin-top:.7rem;}
@media(max-width:600px) {.hero h1 {font-size:1.65rem}.bubble-q {margin-left:3%}.bubble-a {margin-right:3%}.hero-logo {width:170px;}}
</style>
""",
    unsafe_allow_html=True,
)

BASE_DIR = Path(__file__).parent
LOGO_PATH = BASE_DIR / "assets" / "logo_aroeven_hdf.png"


@st.cache_data
def charger_faq():
    return json.loads((BASE_DIR / "faq.json").read_text(encoding="utf-8"))


@st.cache_data
def charger_logo_base64():
    if not LOGO_PATH.exists():
        return None
    return base64.b64encode(LOGO_PATH.read_bytes()).decode("ascii")


faq = charger_faq()
if "historique" not in st.session_state:
    st.session_state.historique = []
if "situation" not in st.session_state:
    st.session_state.situation = None
if "cas" not in st.session_state:
    st.session_state.cas = None
if "page" not in st.session_state:
    st.session_state.page = 0
if "decouverte" not in st.session_state:
    st.session_state.decouverte = 0

STOP = {
    "quelles", "quelle", "quels", "quel", "comment", "quand", "pourquoi", "avec", "dans",
    "pour", "doit", "faire", "sont", "une", "des", "les", "aux", "sur", "est", "que",
    "qui", "son", "ses", "par", "nous", "vous", "peut", "elle", "etre", "avant", "apres",
    "faut", "dont", "leur", "avoir", "plus", "sans", "chez"
}


def mots(texte):
    texte = unicodedata.normalize("NFKD", texte.lower())
    texte = "".join(c for c in texte if not unicodedata.combining(c))
    return {s for s in re.findall(r"[a-z]{3,}", texte) if s not in STOP}


@st.cache_data
def proches(index):
    base = mots(faq[index]["question"] + " " + faq[index]["rubrique"])
    scores = []
    for i, item in enumerate(faq):
        if i == index:
            continue
        cible = mots(item["question"] + " " + item["rubrique"])
        score = len(base & cible) * 2 + int(faq[index]["rubrique"] == item["rubrique"])
        if score:
            scores.append((score, i))
    scores.sort(key=lambda s: (-s[0], s[1]))
    return [i for _, i in scores[:4]]


# Les choix d'une situation conduisent d'abord à des cas concrets, jamais à une réponse directe.
# Les réponses restent exactement celles des FAQ : elles sont associées par leur indice dans faq.json.
SITUATIONS = [
    ("🧳 Je prépare mon séjour", "Planning, projet pédagogique, documents et activités", [
        ("Je démarre la préparation du séjour", 27),
        ("Je veux connaître le rôle de la direction", 5),
        ("Je me demande ce que prend en charge l'Aroéven", 4),
        ("J'organise la réunion de préparation", 28),
        ("Je dois envoyer mon projet pédagogique", 30),
        ("Je vérifie le délai de transmission du projet pédagogique", 7),
        ("Je dois contacter la structure d'accueil", 29),
        ("Je prépare les activités et leurs devis", 38),
        ("Je veux connaître le calendrier général", 6),
        ("Je prépare les démarches avant le départ", 8),
        ("Je dois compléter la fiche de déclaration", 33),
    ]),
    ("🚍 Je prépare un départ ou un retour", "Convoyage, familles et derniers préparatifs", [
        ("Je prépare le convoyage", 31),
        ("Je cherche les horaires et lieux de départ", 42),
        ("J'organise l'accueil le jour du départ", 32),
        ("J'organise les départs et retours", 43),
        ("Je me demande si le tee-shirt est obligatoire", 44),
        ("Je veux vérifier ce qu'il faut prévoir au départ", 9),
    ]),
    ("📁 J'ai une question de documents", "OneDrive, contrôle, contrats et fiches", [
        ("Je cherche les documents du séjour", 11),
        ("Je cherche les dossiers des participants", 34),
        ("Je prépare un éventuel contrôle", 35),
        ("Je constitue le dossier d'un membre de l'équipe", 36),
        ("Je me pose une question sur les contrats et la paie", 37),
    ]),
    ("💳 J'ai un souci de budget", "Cartes de paiement, justificatifs et rémunération", [
        ("Je veux savoir quelle carte utiliser", 39),
        ("Je dois conserver un justificatif de dépense", 40),
        ("J'ai une dépense imprévue ou un dépassement", 41),
        ("Je me pose une question sur les rémunérations", 16),
        ("Je veux comprendre les compléments de rémunération", 17),
    ]),
    ("🚨 Je rencontre une situation préoccupante", "Santé, urgences, sanctions et rapatriement", [
        ("Un jeune consulte un médecin ou est hospitalisé", 47),
        ("Une situation grave survient pendant le séjour", 24),
        ("Un jeune a consommé de l'alcool ou des drogues", 61),
        ("Je dois réagir à un comportement transgressif", 57),
        ("J'envisage un rapatriement disciplinaire", 62),
        ("J'envisage un rapatriement médical", 63),
        ("J'ai une question sur la cigarette", 59),
        ("Je cherche les consignes de mixité", 60),
        ("Je me demande si je dois demander de l'aide", 66),
    ]),
    ("👥 Je gère mon équipe et les jeunes", "Recrutement, vie collective et pédagogie", [
        ("Je veux publier une annonce de recrutement", 13),
        ("Je prépare le contenu d'une annonce", 14),
        ("Je dois composer mon équipe", 15),
        ("Je prépare les règles de vie", 54),
        ("Je réfléchis à ma posture éducative", 55),
        ("Je veux associer les jeunes aux décisions", 56),
        ("Je veux préserver la cohérence de l'équipe", 58),
        ("Je souhaite connaître le public accueilli", 53),
        ("Je cherche les valeurs éducatives de l'Aroéven", 0),
        ("Je cherche les objectifs éducatifs des séjours", 1),
        ("Je me renseigne sur les types de séjours", 3),
        ("Je veux connaître les centres Aroéven", 2),
    ]),
    ("🚐 Je gère le matériel ou le minibus", "Véhicules, dommages et inventaires", [
        ("Je dois récupérer le véhicule ou le matériel", 49),
        ("Je dois savoir qui peut conduire", 50),
        ("Le véhicule a subi un dommage", 51),
        ("Je prépare ou vérifie le matériel pédagogique", 52),
    ]),
    ("📱 Je dois communiquer", "WhatsApp, familles, photos et réseaux sociaux", [
        ("Je contacte l'Aroéven sur le bon canal", 10),
        ("Je veux savoir qui contacte les familles", 45),
        ("Je dois transmettre les photos du séjour", 46),
        ("Je me demande comment gérer les réseaux sociaux", 48),
        ("Je vérifie mes tâches quotidiennes de suivi", 25),
    ]),
    ("📞 J'ai besoin de joindre quelqu'un", "Permanence, siège et interlocuteurs", [
        ("Je dois joindre le siège aux heures de bureau", 64),
        ("Je dois joindre l'astreinte le soir ou le week-end", 65),
        ("Je veux savoir à quoi sert le permanent", 12),
        ("Je souhaite savoir quand demander de l'aide", 66),
        ("Je cherche les coordonnées du siège", 67),
        ("Je cherche les coordonnées de l'association", 26),
        ("Je cherche les missions de Bryan Drion", 18),
        ("Je cherche les missions de Justine Lolivier", 19),
        ("Je cherche les missions de Sébastien Kuczmarski", 20),
        ("Je cherche les missions de Zakary Ferro", 21),
        ("Je cherche les missions d'Émilie Bacquet", 22),
        ("Je cherche les missions d'Anne-Sophie Matthys", 23),
    ]),
]


def selectionner_situation(index):
    st.session_state.situation = index
    st.session_state.cas = None


def selectionner_cas(index):
    st.session_state.cas = index


def accueil():
    st.session_state.situation = None
    st.session_state.cas = None


def revenir_aux_cas():
    st.session_state.cas = None


def surprise():
    st.session_state.decouverte += 1
    idx = (st.session_state.decouverte * 17 + 5) % len(faq)
    for situation_id, (_nom, _desc, cas) in enumerate(SITUATIONS):
        if any(j == idx for _, j in cas):
            st.session_state.situation = situation_id
            st.session_state.cas = idx
            return

logo_b64 = charger_logo_base64()
if logo_b64:
    st.markdown(
        (
            '<div class="hero"><div class="hero-inner">'
            '<div class="hero-logo-wrap">'
            f'<img class="hero-logo" src="data:image/png;base64,{logo_b64}" alt="Logo Aroéven Hauts-de-France">'
            '</div>'
            '<div class="hero-copy"><h1>🌈 Mon copilote Aroéven</h1>'
            '<p>Une question sur ton séjour ? Choisis un bouton et avançons ensemble 💬</p></div>'
            '</div></div>'
        ),
        unsafe_allow_html=True,
    )
else:
    st.markdown(
        '<div class="hero"><h1>🌈 Mon copilote Aroéven</h1><p>Une question sur ton séjour ? Choisis un bouton et avançons ensemble 💬</p></div>',
        unsafe_allow_html=True,
    )

# Rappel visible sur toutes les pages : la permanence reste une ressource essentielle.
st.markdown(
    """
<div class="permanence" role="note" aria-label="Importance de la permanence Aroéven">
  <h3>📞 La permanence Aroéven : le bon réflexe</h3>
  <p>Appelle la permanence lorsqu’une décision, une validation ou un arbitrage Aroéven est nécessaire,
  ou face à une situation préoccupante qui ne peut attendre.</p>
  <p>Hors horaires de bureau, l’astreinte est réservée aux urgences : si personne ne répond,
  laisse obligatoirement un message décrivant la situation. Pour les questions courantes,
  utilise le groupe WhatsApp du séjour.</p>
  <p class="telephone">📞 Siège : 03 20 75 10 85 — de 9 h à 17 h en semaine, hors jours fériés.</p>
  <p>📱 Astreinte : hors horaires du siège. Tous les numéros sont dans votre téléphone professionnel.</p>
</div>
""",
    unsafe_allow_html=True,
)

# Parcours en 3 étapes : situation -> cas précis -> réponse.
if st.session_state.situation is None:
    st.markdown("### 👋 Bonjour ! Qu'est-ce qui se passe pour toi ?")
    st.write("Choisis la situation qui ressemble à la tienne. Je te proposerai ensuite plusieurs cas possibles.")
    for a in range(0, len(SITUATIONS), 2):
        cols = st.columns(2)
        for j in range(a, min(a + 2, len(SITUATIONS))):
            with cols[j - a]:
                nom, description, _ = SITUATIONS[j]
                st.button(nom, key=f"situation-{j}", on_click=selectionner_situation,
                          args=(j,), use_container_width=True)
                st.caption(description)
    st.button("🎲 Fais-moi découvrir un cas !", on_click=surprise, use_container_width=True)
else:
    st.button("🏠 Changer de situation", on_click=accueil, use_container_width=True)
    nom, description, cas = SITUATIONS[st.session_state.situation]
    st.markdown(f"### {nom}")
    if st.session_state.cas is None:
        st.write("**Quel cas correspond le mieux à ta situation ?**")
        st.caption("Clique sur un cas pour voir la réponse correspondante.")
        for pos, (titre, index) in enumerate(cas):
            st.button("👉 " + titre, key=f"cas-{st.session_state.situation}-{pos}",
                      on_click=selectionner_cas, args=(index,), use_container_width=True)
    else:
        st.button("⬅️ Voir les autres cas possibles", on_click=revenir_aux_cas,
                  use_container_width=True)
        i = st.session_state.cas
        item = faq[i]
        titre_cas = next((titre for titre, j in cas if j == i), item["question"])
        st.markdown('<div class="small-label">💬 Ta situation</div>', unsafe_allow_html=True)
        st.markdown('<div class="bubble-q">' + __import__('html').escape(titre_cas) + '</div>', unsafe_allow_html=True)
        st.markdown('<div class="small-label">🌟 La réponse Aroéven</div>', unsafe_allow_html=True)
        st.markdown('<div class="bubble-a">' + __import__('html').escape(item["reponse"]).replace("\n", "<br>") + '</div>', unsafe_allow_html=True)
        st.markdown("### 🤔 Un autre cas de cette situation ?")
        for pos, (titre, index) in enumerate(cas):
            if index != i:
                st.button("👉 " + titre, key=f"autre-{st.session_state.situation}-{pos}",
                          on_click=selectionner_cas, args=(index,), use_container_width=True)

st.divider()
st.caption(f"💚 {len(faq)} questions issues des deux FAQ 2026 réunies • Sans IA • Sans barre de recherche")
st.caption("⚠️ Les consignes sensibles ou réglementaires sont à confirmer auprès de l'Aroéven avant application.")
