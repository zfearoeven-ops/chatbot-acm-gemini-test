import os
import json
import re
import urllib.request
import urllib.error
import streamlit as st
import pandas as pd

st.set_page_config(page_title="Assistant de séjour", page_icon="🏕️", layout="centered")

# ---------- Configuration ----------
PERMANENCE_JOUR = "03 20 75 10 85"
PERMANENCE_HORS_HORAIRES = "06 25 31 21 64"
EMERGENCY_CONTACTS = "15 (SAMU) • 18 (pompiers) • 112 (urgence européenne) • 114 (urgence accessible par SMS/app)"
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/chat")

st.markdown("""
<style>
.block-container {max-width: 850px; padding-top: 1.2rem; padding-bottom: 2rem;}
div.stButton > button {width:100%; min-height:3rem; white-space:normal; border-radius:12px;}
.small-note {font-size:0.88rem; color:#666;}
</style>
""", unsafe_allow_html=True)

if "stay" not in st.session_state:
    st.session_state.stay = {
        "effectif": None, "age_min": None, "age_max": None, "nuits": None,
        "animateurs_presents": None, "directeur": True, "activites": None
    }
if "messages" not in st.session_state:
    st.session_state.messages = []
if "mode" not in st.session_state:
    st.session_state.mode = None
if "flow_step" not in st.session_state:
    st.session_state.flow_step = 0
if "flow_answers" not in st.session_state:
    st.session_state.flow_answers = {}
if "topic" not in st.session_state:
    st.session_state.topic = None

def ollama_ready():
    """Vérifie que l'API locale d'Ollama répond."""
    try:
        req = urllib.request.Request("http://localhost:11434/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=3) as response:
            return response.status == 200
    except Exception:
        return False


def stay_summary():
    s = st.session_state.stay
    bits = []
    if s["effectif"] is not None: bits.append(f"{s['effectif']} jeunes")
    if s["age_min"] is not None and s["age_max"] is not None:
        bits.append(f"âgés de {s['age_min']} à {s['age_max']} ans")
    if s["nuits"] is not None: bits.append(f"{s['nuits']} nuits")
    if s["animateurs_presents"] is not None: bits.append(f"{s['animateurs_presents']} animateur(s) présent(s)")
    return ", ".join(bits) if bits else "Dossier de séjour non renseigné"

def contacts_block():
    return f"""
**Contacts à garder à portée de main**
- Permanence (8h30–17h) : **{PERMANENCE_JOUR}**
- Permanence hors horaires de bureau : **{PERMANENCE_HORS_HORAIRES}**
- Urgence immédiate en France : **15 (SAMU), 18 (pompiers), 112**. Le **114** est un service d'urgence accessible notamment par SMS/app pour les personnes sourdes ou malentendantes.
"""

def safety_triage(topic, answers):
    # Conservative deterministic first-line safety messaging.
    urgent = False
    if topic == "Jeune blessé":
        if answers.get("conscience") in ["Non", "Je ne sais pas"] or answers.get("respiration") in ["Non", "Je ne sais pas"] or answers.get("gravite") in ["Oui", "Je ne sais pas"]:
            urgent = True
    if topic == "Jeune introuvable":
        urgent = True
    if topic == "Jeune malade":
        if answers.get("gravite") in ["Oui", "Je ne sais pas"]:
            urgent = True
    if urgent:
        return ("🔴 **Priorité sécurité.** Ne reste pas seul face à la situation : applique les consignes de sécurité de ton organisme et appelle immédiatement les secours si un danger grave, une urgence médicale ou un doute sérieux existe. "
                "Pour un jeune introuvable, lance immédiatement la procédure de recherche/alerte de l'organisateur et des autorités compétentes ; ne retarde pas l'alerte pour répondre au chatbot.\n\n" + contacts_block())
    return None

SYSTEM_PROMPT = f"""
Tu es l'assistant conversationnel d'un directeur de séjour ACM en France. Tu réponds en français, avec empathie, de façon claire, opérationnelle et concise.
Contexte connu du séjour : {{stay_context}}
Tu dois utiliser ce contexte sans redemander une information déjà connue. Si une information manque, pose une seule question utile à la fois et propose des choix courts quand possible.
RÈGLES IMPORTANTES :
- La règle 1 animateur pour 8 jeunes est une règle interne indiquée par l'organisme de l'utilisateur, pas une règle légale générale. Pour les calculs internes simples, effectif requis = arrondi supérieur(effectif / 8). Indique clairement « selon votre règle interne ».
- Ne présente jamais une règle interne comme une obligation légale. Pour les questions de droit ACM, distingue ce qui est vérifié de ce qui doit être vérifié dans les textes officiels. N'invente pas de citation d'article.
- En cas de danger immédiat, problème médical potentiellement grave, enfant introuvable ou risque sérieux : priorité à la sécurité et aux secours, pas à la conversation. Rappelle 15 SAMU, 18 pompiers, 112 ; 114 est un service accessible notamment par SMS/app selon les situations.
- Permanence de l'organisme : 03 20 75 10 85 de 8h30 à 17h ; hors horaires de bureau : 06 25 31 21 64.
- Manager One : selon la règle interne fournie, après chaque paiement par carte virtuelle, le ticket/justificatif doit être ajouté dans l'application. Ne prétends pas pouvoir vérifier ou déposer le justificatif toi-même.
- Handicap/besoins particuliers : ne présume pas qu'un accompagnant individuel est légalement obligatoire du seul fait d'un handicap. Propose une analyse individualisée des besoins, adaptations, sécurité, équipe et échanges avec la famille/organisateur.
- Ne prétends pas que tu as contacté les secours ou la permanence. Ne remplace pas les secours, les professionnels de santé ni l'organisateur.
- Si l'utilisateur demande quelque chose hors de tes informations, dis-le et oriente vers la bonne personne.
"""

def ask_ai(user_text):
    """Envoie la conversation à Ollama en local, sans clé API."""
    try:
        instructions = SYSTEM_PROMPT.format(stay_context=stay_summary())
        sejours_context = format_sejours_for_ai(st.session_state.sejours_df, user_text) if st.session_state.sejours_df is not None else ""
        if sejours_context:
            instructions += "\n\nBASE DE SÉJOURS IMPORTÉE (données du fichier utilisateur ; ne pas inventer les champs absents) :\n" + sejours_context + "\n\nPour toute question sur les séjours, réponds uniquement à partir de ces lignes. Si l'information n'est pas présente, dis-le. Pour des chiffres, dates, tarifs et effectifs, reprends exactement les valeurs du fichier. Signale quand plusieurs séjours correspondent."
        conversation = [{"role": "system", "content": instructions}]
        # Conserve l'historique de la session pour que l'IA puisse suivre le fil.
        for message in st.session_state.messages[-16:]:
            role = message.get("role")
            content = message.get("content", "")
            if role in ("user", "assistant") and content:
                conversation.append({"role": role, "content": content})
        # Évite de doubler le dernier message si l'appel vient d'un parcours guidé.
        if not conversation or conversation[-1].get("role") != "user" or conversation[-1].get("content") != user_text:
            conversation.append({"role": "user", "content": user_text})
        payload = json.dumps({"model": OLLAMA_MODEL, "messages": conversation, "stream": False}).encode("utf-8")
        request = urllib.request.Request(OLLAMA_URL, data=payload, headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(request, timeout=180) as response:
            data = json.loads(response.read().decode("utf-8"))
        answer = data.get("message", {}).get("content", "").strip()
        if not answer:
            return None, "Ollama a répondu, mais aucun texte n'a été reçu. Vérifie que le modèle est installé avec `ollama list`."
        return answer, None
    except urllib.error.URLError as e:
        return None, "Impossible de joindre Ollama. Vérifie qu'Ollama est ouvert et que `ollama list` fonctionne. Détail : " + str(e)
    except Exception as e:
        return None, f"Échec de l'appel à Ollama ({OLLAMA_MODEL}) : {e}"


def add_user_message(text):
    st.session_state.messages.append({"role":"user", "content":text})

def add_assistant_message(text):
    st.session_state.messages.append({"role":"assistant", "content":text})


# ---------- Base de séjours importée depuis Excel ----------
if "sejours_df" not in st.session_state:
    st.session_state.sejours_df = None
if "sejours_source" not in st.session_state:
    st.session_state.sejours_source = None

def format_sejours_for_ai(df, question, limit=35):
    """Construit un contexte lisible depuis le classeur importé; les données Excel restent la source de vérité."""
    if df is None or df.empty:
        return ""
    work = df.copy()
    # Filtrage simple par mots de la question pour limiter le contexte envoyé au modèle.
    terms = [t.lower() for t in re.findall(r"[A-Za-zÀ-ÿ0-9'-]+", question) if len(t) >= 3]
    if terms:
        row_text = work.fillna("").astype(str).agg(" | ".join, axis=1).str.lower()
        scored = row_text.apply(lambda s: sum(1 for term in set(terms) if term in s))
        if (scored > 0).any():
            work = work.assign(_score=scored).sort_values("_score", ascending=False).drop(columns="_score")
    work = work.head(limit)
    lines = []
    for _, row in work.iterrows():
        vals = []
        for col, val in row.items():
            if pd.isna(val):
                continue
            if isinstance(val, (pd.Timestamp,)):
                val = val.strftime("%d/%m/%Y")
            vals.append(f"{col}: {val}")
        lines.append("- " + "; ".join(vals))
    return "\n".join(lines)

# Injecte les séjours dans le contexte système uniquement lorsqu'un fichier a été importé.

st.title("🏕️ Assistant de séjour")
st.caption("Assistant guidé pour les directeurs • IA locale Ollama • version de test")

with st.expander("📚 Base de séjours (Excel)", expanded=True):
    st.write("Importe le classeur Excel des séjours pour permettre à l’IA de répondre à partir des données réelles.")
    uploaded = st.file_uploader("Choisir le fichier Excel (.xlsx)", type=["xlsx"], key="upload_sejours")
    if uploaded is not None:
        try:
            df_sejours = pd.read_excel(uploaded)
            if df_sejours.empty:
                st.warning("Le fichier ne contient aucune ligne.")
            else:
                st.session_state.sejours_df = df_sejours
                st.session_state.sejours_source = uploaded.name
                st.success(f"Fichier chargé : {uploaded.name} — {len(df_sejours)} séjours, {len(df_sejours.columns)} colonnes.")
        except Exception as e:
            st.error(f"Impossible de lire ce fichier Excel : {e}")
    if st.session_state.sejours_df is not None:
        st.caption(f"Base active : {st.session_state.sejours_source}")
        st.dataframe(st.session_state.sejours_df, use_container_width=True, hide_index=True)
        if st.button("Retirer la base de séjours", key="clear_sejours"):
            st.session_state.sejours_df = None
            st.session_state.sejours_source = None
            st.rerun()


with st.expander("⚙️ État de l’IA locale", expanded=False):
    st.write(f"Modèle configuré : **{OLLAMA_MODEL}**")
    if ollama_ready():
        st.success("Ollama est accessible sur cet ordinateur.")
        if st.button("Tester la connexion IA", key="test_api"):
            with st.spinner("Test de connexion…"):
                result, error = ask_ai("Réponds uniquement : « Test IA réussi. »")
            if error: st.error(error)
            else: st.success(result)
    else:
        st.error("Ollama ne répond pas. Ouvre l’application Ollama et vérifie que le modèle est installé.")
    st.caption("Aucune clé API ni abonnement n’est nécessaire. Les réponses sont générées par le modèle local installé sur ton PC.")

with st.expander("📋 Mon séjour", expanded=False):
    s = st.session_state.stay
    c1, c2 = st.columns(2)
    with c1:
        effectif = st.number_input("Nombre de jeunes", min_value=0, max_value=500, value=int(s["effectif"] or 0), step=1)
        age_min = st.number_input("Âge minimum", min_value=0, max_value=17, value=int(s["age_min"] or 6), step=1)
        nuits = st.number_input("Nombre de nuits", min_value=0, max_value=365, value=int(s["nuits"] or 0), step=1)
    with c2:
        age_max = st.number_input("Âge maximum", min_value=0, max_value=17, value=int(s["age_max"] or 10), step=1)
        anims = st.number_input("Animateurs présents (hors direction)", min_value=0, max_value=100, value=int(s["animateurs_presents"] or 0), step=1)
    if st.button("Enregistrer le séjour"):
        s.update({"effectif":int(effectif) if effectif else None, "age_min":int(age_min), "age_max":int(age_max),
                  "nuits":int(nuits) if nuits else None, "animateurs_presents":int(anims)})
        st.success("Dossier mis à jour.")
        st.rerun()
    st.info(f"Contexte actuel : {stay_summary()}")
    if s["effectif"] is not None:
        required = (s["effectif"] + 7) // 8
        st.write(f"Selon votre règle interne de 1 animateur pour 8 jeunes : **{required} animateur(s)** pour {s['effectif']} jeunes.")
        if s["animateurs_presents"] is not None and s["animateurs_presents"] < required:
            st.warning("L’effectif déclaré est inférieur à votre règle interne. Vérifie l’organisation et contacte la permanence si aucune solution immédiate n’est disponible.")

st.subheader("Que veux-tu faire ?")
categories = [
    ("🚨 Une situation", "situation"),
    ("👥 Encadrement / équipe", "encadrement"),
    ("🧩 Besoins particuliers / handicap", "handicap"),
    ("💳 Manager One / justificatif", "manager"),
    ("📋 Préparer ou vérifier mon séjour", "sejour"),
    ("📚 Une question réglementaire", "reglementation"),
]
cols = st.columns(2)
for i, (label, mode) in enumerate(categories):
    with cols[i % 2]:
        if st.button(label, key=f"cat_{mode}"):
            st.session_state.mode = mode
            st.session_state.topic = None
            st.session_state.flow_answers = {}
            st.session_state.flow_step = 0
            add_user_message(f"Le directeur ouvre le parcours : {label}.")
            st.rerun()

if st.session_state.mode:
    st.divider()
    if st.session_state.mode == "situation":
        st.markdown("**Quelle situation rencontres-tu ?**")
        options = ["🤒 Animateur absent", "🤕 Jeune blessé", "🌡️ Jeune malade", "🏃 Jeune introuvable", "🚌 Problème de transport", "⚠️ Problème d’encadrement", "Autre situation"]
    elif st.session_state.mode == "encadrement":
        options = ["Calculer l’effectif selon la règle interne 1/8", "Animateur absent", "Vérifier les qualifications", "Remplacement / équipe"]
    elif st.session_state.mode == "handicap":
        options = ["Préparer l’accueil", "Besoin d’un accompagnement individuel", "Crise ou difficulté pendant le séjour", "Adapter une activité"]
    elif st.session_state.mode == "manager":
        options = ["Je viens de payer avec la carte virtuelle", "Justificatif oublié", "Je n’ai plus le ticket", "Ma carte ne fonctionne plus", "Autre question Manager One"]
    elif st.session_state.mode == "sejour":
        options = ["Créer / modifier mon dossier", "Vérifier mon séjour", "Ajouter une activité", "Autre question sur mon séjour"]
    else:
        options = ["Encadrement réglementaire", "Qualifications", "Baignade / activité physique", "Santé / médicaments", "Documents obligatoires", "Autre question"]
    chosen = st.radio("Choisis une situation :", options, key="chosen_option")
    if st.button("Continuer", key="continue_flow"):
        st.session_state.topic = chosen
        st.session_state.flow_answers = {}
        add_user_message(f"Le directeur choisit le parcours : {chosen}.")
        if "blessé" in chosen.lower():
            add_assistant_message("Je vais d’abord vérifier la sécurité immédiate. Le jeune est-il conscient ?")
        elif "introuvable" in chosen.lower():
            add_assistant_message("🔴 Un jeune introuvable peut être une urgence. Lance immédiatement la procédure d’alerte de ton organisme et contacte les autorités/secours compétents sans attendre le chatbot. As-tu déjà alerté le responsable de l’organisateur ?")
        elif "carte virtuelle" in chosen.lower() or "justificatif" in chosen.lower() or "ticket" in chosen.lower():
            add_assistant_message("Selon votre règle interne, le justificatif de chaque paiement par carte virtuelle doit être ajouté dans Manager One. **As-tu le ticket ou la facture à disposition ?**")
        else:
            add_assistant_message(f"D’accord, on regarde cela ensemble : **{chosen}**. Je vais utiliser le contexte connu : {stay_summary()}.")
        st.rerun()

if st.session_state.topic:
    topic = st.session_state.topic.lower()
    if "blessé" in topic:
        a1, a2 = st.columns(2)
        with a1:
            conscious = st.radio("Le jeune est-il conscient ?", ["Oui", "Non", "Je ne sais pas"], key="inj_conscious")
        with a2:
            breathing = st.radio("Respire-t-il normalement ?", ["Oui", "Non", "Je ne sais pas"], key="inj_breathing")
        severe = st.radio("Blessure importante, choc à la tête ou doute sérieux ?", ["Non", "Oui", "Je ne sais pas"], key="inj_severe")
        if st.button("Analyser la situation", key="inj_analyze"):
            ans = {"conscience":conscious, "respiration":breathing, "gravite":severe}
            msg = safety_triage("Jeune blessé", ans)
            if msg:
                add_assistant_message(msg)
                st.error("Priorité sécurité")
            else:
                add_assistant_message("Si le jeune est conscient, respire normalement et qu’aucun signe inquiétant n’est identifié, applique le protocole de premiers secours de ton organisme, surveille son état et fais appel à un professionnel de santé en cas de doute ou d’aggravation. Note les faits et informe les responsables selon votre procédure. " + contacts_block())
            st.rerun()
    elif "introuvable" in topic:
        st.error("N’attends pas une réponse de l’IA pour lancer la procédure de recherche/alerte. Contacte immédiatement le responsable de l’organisateur et les autorités compétentes selon les circonstances.")
        st.markdown(contacts_block())
    elif "carte virtuelle" in topic or "justificatif" in topic or "ticket" in topic:
        receipt = st.radio("As-tu le ticket ou la facture ?", ["Oui, je peux l’ajouter maintenant", "Je l’ai mais je l’ajouterai plus tard", "Non, je ne l’ai pas"], key="receipt")
        if st.button("Continuer", key="receipt_continue"):
            if receipt.startswith("Oui"):
                msg = "Parfait. Ouvre Manager One et ajoute maintenant le ticket/la facture au paiement concerné. Une fois le dépôt fait, vérifie que le justificatif est bien associé au paiement. Je ne peux pas effectuer le dépôt à ta place."
            elif receipt.startswith("Je l’ai"):
                msg = "Je te conseille de l’ajouter tout de suite plutôt que de le remettre à plus tard : selon votre règle interne, chaque paiement par carte virtuelle doit avoir son justificatif dans l’application. Si la carte est déjà inutilisable, contacte le support/la personne référente prévue par votre organisme."
            else:
                msg = "Ne crée pas de faux justificatif. Vérifie si tu peux récupérer un duplicata auprès du commerçant ou une facture par e-mail, puis suis la procédure interne. Si la carte est bloquée ou si tu ne sais pas régulariser, contacte la personne référente ou la permanence."
            add_assistant_message(msg + "\n\n" + contacts_block())
            st.rerun()

st.divider()
st.subheader("💬 Conversation avec l’assistant")
st.caption("Tu peux cliquer sur les parcours ou écrire une phrase courte. Les réponses IA utilisent Ollama sur ton ordinateur.")

for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

prompt = st.chat_input("Ex. : mon animateur est malade demain…")
if prompt:
    add_user_message(prompt)
    with st.spinner("L’assistant réfléchit…"):
        result, error = ask_ai(prompt)
    if error:
        add_assistant_message("Je n’ai pas pu joindre l’IA. " + error + "\n\nTu peux continuer à utiliser les parcours guidés ci-dessus.")
        st.error(error)
    else:
        add_assistant_message(result)
    st.rerun()

with st.expander("📞 Contacts utiles", expanded=False):
    st.markdown(contacts_block())
    st.caption("En cas de danger immédiat, appelle les secours sans attendre la réponse du chatbot.")
with st.expander("ℹ️ À propos de cette version", expanded=False):
    st.write("Prototype de test. La règle 1/8 est traitée comme une règle interne de votre organisme, pas comme une règle légale générale. Les parcours ne remplacent pas les procédures officielles de l’organisateur, les secours ou un avis professionnel.")
