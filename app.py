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


def demander(i):
    st.session_state.historique.append(i)
    st.session_state.historique = st.session_state.historique[-8:]
    st.session_state.page = 0


def accueil():
    st.session_state.historique = []
    st.session_state.page = 0


def surprise():
    # Ordre pseudo-aléatoire reproductible, aucune API ni donnée utilisateur.
    st.session_state.decouverte += 1
    demander((st.session_state.decouverte * 17 + 5) % len(faq))


def trouver(texte, autre=""):
    for i, item in enumerate(faq):
        q = item["question"].lower()
        if texte.lower() in q and (not autre or autre.lower() in q):
            return i
    return 0


DEMARRAGE = [
    ("🧳 Je prépare mon départ", trouver("premières étapes")),
    ("📅 J'ai une échéance", trouver("projet pédagogique doit")),
    ("💳 J'ai une question de budget", trouver("deux cartes")),
    ("🚨 J'ai un souci pendant le séjour", trouver("jeune consulte")),
    ("🚌 Je gère les transports", trouver("convoyage")),
    ("🙋 J'ai besoin d'un contact", trouver("horaires de bureau")),
]

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

if st.session_state.historique:
    col_a, col_b = st.columns([1, 1])
    with col_a:
        st.button("🏠 Revenir au début", on_click=accueil, use_container_width=True)
    with col_b:
        st.button("🎲 Surprends-moi !", on_click=surprise, use_container_width=True)

    i = st.session_state.historique[-1]
    item = faq[i]
    st.markdown('<div class="small-label">💬 Votre question</div>', unsafe_allow_html=True)
    st.markdown('<div class="bubble-q">' + __import__("html").escape(item["question"]) + '</div>', unsafe_allow_html=True)
    st.markdown('<div class="small-label">🌟 La réponse Aroéven</div>', unsafe_allow_html=True)
    st.markdown('<div class="bubble-a">' + __import__("html").escape(item["reponse"]).replace("\n", "<br>") + '</div>', unsafe_allow_html=True)

    if len(st.session_state.historique) > 1:
        precedent = st.session_state.historique[-2]
        st.button("↩️ Revoir la question précédente", on_click=demander, args=(precedent,))

    st.markdown("### 🔎 Et si tu te demandais aussi…")
    voisins = proches(i)
    if not voisins:
        voisins = [(i + j) % len(faq) for j in range(1, 5)]
    for j in voisins:
        st.button("💬 " + faq[j]["question"], key=f"rel-{i}-{j}", on_click=demander, args=(j,), use_container_width=True)
else:
    st.markdown("### 👋 Bonjour ! Qu'est-ce qui t'amène ?")
    st.write("Pas besoin de taper quoi que ce soit : touche simplement une situation ci-dessous.")
    for a in range(0, len(DEMARRAGE), 2):
        cols = st.columns(2)
        for col, (libelle, index) in zip(cols, DEMARRAGE[a:a + 2]):
            with col:
                st.button(libelle, key=f"start-{index}-{a}", on_click=demander, args=(index,), use_container_width=True)
    st.button("🎲 Une question au hasard !", on_click=surprise, use_container_width=True)

st.divider()
with st.expander("🃏 Je veux piocher parmi toutes les questions", expanded=False):
    st.caption("Toutes les questions des deux documents réunies, sans distinction ni rubrique obligatoire.")
    par_page = 8
    debut = st.session_state.page * par_page
    fin = min(debut + par_page, len(faq))
    for j in range(debut, fin):
        st.button("❔ " + faq[j]["question"], key=f"all-{j}", on_click=demander, args=(j,), use_container_width=True)
    ca, cb, cc = st.columns([1, 1, 1])
    with ca:
        if st.button("⬅️ Avant", disabled=st.session_state.page == 0, use_container_width=True):
            st.session_state.page -= 1
            st.rerun()
    with cb:
        st.caption(f"Page {st.session_state.page + 1} / {(len(faq) + par_page - 1) // par_page}")
    with cc:
        if st.button("Après ➡️", disabled=fin == len(faq), use_container_width=True):
            st.session_state.page += 1
            st.rerun()

st.caption(f"💚 {len(faq)} questions issues des deux FAQ 2026 réunies • Sans IA • Sans barre de recherche • Aucune donnée saisie")
st.caption("⚠️ Les consignes sensibles ou réglementaires sont à confirmer auprès de l'Aroéven avant application.")
