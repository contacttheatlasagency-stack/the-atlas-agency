# Fichier: app.py
# LE MOTEUR COMPLET POUR "THE ATLAS AGENCY"

import streamlit as st
import google.generativeai as genai
import re
import requests 

# --- 1. CONFIGURATION DE LA PAGE ---
# Définit le titre de l'onglet, l'icône et la mise en page
st.set_page_config(
    page_title="The Atlas Agency - Generator", 
    page_icon="🔑", # Emoji pour la marque
    layout="wide"
)

# --- 2. CSS POUR LE DESIGN "FRAIS" (MODE SOMBRE) ---
# C'est ce qui rend l'application belle et "premium"
FRESH_DESIGN_CSS = """
<style>
/* Fond principal */
[data-testid="stAppViewContainer"] { 
    background-color: #0B0F19; 
}
/* Fond des boîtes */
[data-testid="stForm"], [data-testid="stInfo"], [data-testid="stExpander"] { 
    background-color: #12192D; 
    border-radius: 15px; 
}
[data-testid="stInfo"] { 
    background-color: #19223D; 
}
/* Titres des jours */
[data-testid="stExpander"] > summary { 
    font-size: 1.2rem; 
    font-weight: 600; 
}
/* Texte */
body, [data-testid="stText"], [data-testid="stMarkdown"], h1, h2, h3 { 
    color: #FFFFFF; 
}
/* Champs de formulaire */
[data-testid="stTextInput"] input, 
[data-testid="stSelectbox"] div[data-baseweb="select"],
[data-testid="stTextArea"] textarea,
[data-testid="stNumberInput"] input {
    background-color: #0B0F19; 
    color: #FFFFFF; 
    border-radius: 10px; 
    border-color: #2E3A59;
}
/* Boutons (Couleur "fraîche") */
[data-testid="stButton"] button {
    background-color: #00F2C1; 
    color: #0B0F19; 
    border: none;
    border-radius: 10px; 
    font-weight: 600;
}
[data-testid="stButton"] button:hover { 
    background-color: #00C19A; 
    color: #0B0F19; 
}
/* Bouton Lien (Acheter la clé) */
[data-testid="stLinkButton"] a {
    background-color: #00F2C1; 
    color: #0B0F19; 
    border-radius: 10px;
    font-weight: 600; 
    padding: 0.35rem 0.75rem;
}
[data-testid="stLinkButton"] a:hover { 
    background-color: #00C19A; 
    color: #0B0F19; 
    text-decoration: none; 
}
/* Icônes d'intérêt */
[data-testid="stCheckbox"] label { 
    font-size: 1.05rem; 
}
</style>
"""
st.markdown(FRESH_DESIGN_CSS, unsafe_allow_html=True)

# --- 3. SECRETS ET CONFIGURATION API ---
# Récupère vos clés secrètes depuis Streamlit Cloud
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    LEMON_API_KEY = st.secrets["LEMONSQUEEZY_API_KEY"]
    LEMON_PRODUCT_ID = st.secrets["LEMONSQUEEZY_PRODUCT_ID"]
    LEMON_STORE_ID = st.secrets["LEMONSQUEEZY_STORE_ID"]
except Exception as e:
    st.error(f"Erreur: Secrets non configurés. Assurez-vous d'avoir ajouté vos 4 clés (TEST) dans les Secrets Streamlit.")


# Fichier: app.py
# --- 4. PROMPT MAÎTRE (VERSION "AGENCE 5 ÉTOILES") ---

PROMPT_MAITRE = """
Tu es 'Atlas', le concierge principal de "The Atlas Agency", un service de voyage de luxe 5 étoiles.
Ta réputation repose sur la création d'itinéraires "indispensables" : hyper-détaillés, rassurants, et remplis de joyaux locaux.

AVANT DE COMMENCER, TU DOIS SUIVRE CES 3 MÉTA-RÈGLES CRUCIALES :

1.  **RÈGLE DE RYTHME (LA DURÉE) :** Analyse la `{duree}` totale.
    * **Si 1-3 jours (Court) :** Concentre-toi sur les "incontournables" (must-sees) de manière efficace. Le rythme est dense.
    * **Si 4-7 jours (Moyen) :** Mélange les "incontournables" avec 1-2 "joyaux cachés" (expériences locales).
    * **Si 8+ jours (Long) :** C'est un marathon, pas un sprint. Tu DOIS inclure des options de "Journée libre / repos" (ex: Jour 7), des "Excursions d'une journée" (day trips) vers des villes voisines, et des "journées de quartier" (deep dives).

2.  **RÈGLE D'AUTHENTICITÉ (LA LANGUE LOCALE) :**
    * Pour trouver les "joyaux cachés" et les "bons conseils", tu dois simuler une recherche comme un local.
    * Pense en silence : "Pour {destination}, je vais utiliser ma connaissance du [Langue du pays] pour trouver les restaurants et les lieux que les touristes ne connaissent pas."
    * Tu dois activement éviter les "pièges à touristes" bien notés mais génériques.

3.  **RÈGLE DE CONFIANCE (DÉTAILS COMPLETS) :**
    * Le client est en vacances et ne doit "pas se prendre la tête".
    * Chaque suggestion doit inclure le **temps estimé**, le **prix approximatif**, et un **lien Google Maps** pour la navigation.

---
INSTRUCTIONS CLIENT :
- Destination : {destination}
- Durée : {duree} jours
- Budget : {budget}
- Intérêts principaux : {interets}
- Logistique & Rythme : {logistics}
- Contraintes Spécifiques : {specific_constraints}
- LANGUE FINALE : {langue}
---

MISSION :
Tu vas maintenant générer l'itinéraire complet.
Tu DOIS respecter TOUTES les règles suivantes :

1.  **RÈGLE DE LANGUE :**
    Tout le texte de l'itinéraire DOIT être rédigé UNIQUEMENT en **{langue}**.
    
2.  **RÈGLE DE STRUCTURE (Ne pas traduire !) :**
    Tu DOIS suivre EXACTEMENT cette structure Markdown pour CHAQUE jour. Les emojis sont obligatoires.

### JOUR 1 : [Titre accrocheur et thématique pour le Jour 1, DANS LA LANGUE {langue}]
- 📷 **Image :** [Un ou deux mots-clés en ANGLAIS pour Unsplash, ex: "Kyoto,Temple"]

- ☀️ **Matin :**
    - **Activité :** [Description de l'activité principale. Sois précis.]
    - **Le "Pourquoi" :** [1-2 lignes de conseil d'initié. Ex: "C'est populaire, mais voici l'astuce : arrivez avant 9h..." ou "Le meilleur spot photo se trouve à gauche..."]
    - **Logistique :** [Temps sur place ET prix d'entrée. Ex: "Approx. 2h sur place / 15€ par personne"]
    - **Lien Pratique :** [Fournis un lien de recherche Google Maps pour le lieu. Ex: "https://www.google.com/maps/search/Nom+du+lieu+exact"]

- 🍽️ **Midi :**
    - **Recommandation :** [Un type de cuisine ou une suggestion de restaurant (correspondant au budget).]
    - **Le "Pourquoi" :** [Ex: "C'est un favori local, pas un piège à touristes." ou "Parfait pour une bouchée rapide."]
    - **Logistique :** [Estimation du prix. Ex: "Budget : env. 10-15€ par personne"]
    - **Lien Pratique :** [Lien de recherche Google Maps. Ex: "https://www.google.com/maps/search/restaurant+japonais,Quartier+XYZ"]

- 🏛️ **Après-midi :**
    - **Activité :** [Description de l'activité principale.]
    - **Le "Pourquoi" :** [Conseil d'initié.]
    - **Logistique :** [Temps et prix.]
    - **Lien Pratique :** [Lien Google Maps.]

- 🌙 **Soir :**
    - **Activité :** [Suggestion de dîner et/ou d'activité (ex: spectacle, promenade).]
    - **Le "Pourquoi" :** [Ex: "Parfait pour un dîner mémorable..."]
    - **Logistique :** [Temps et prix.]
    - **Lien Pratique :** [Lien Google Maps.]

- 🎁 **Option Extra / Joyau Caché :**
    - [Une petite activité "bonus" ou un lieu secret à proximité, que le client n'a pas demandé, pour enrichir son voyage.]

- 💡 **Résumé de la Journée :**
    - **Transport :** [Conseil global de transport pour la journée. Ex: "Aujourd'hui, tout se fait à pied (env. 20 min de marche max)" ou "Prenez le Pass Métro Journée (8€)..."]
    - **Budget Approx. :** [Estimation du total de la journée (activités + nourriture). Ex: "Total estimé (hors shopping) : 85€"]

(Tu continues ce format pour TOUS les jours demandés, en respectant la RÈGLE DE RYTHME.)
Commence directement par "### JOUR 1 :".
"""


# --- 5. ÉTAT DE SESSION (POUR MÉMORISER) ---
if 'itinerary_generated' not in st.session_state:
    st.session_state.itinerary_generated = None
if 'unlocked' not in st.session_state:
    st.session_state.unlocked = False

# --- 6. FONCTIONS TECHNIQUES ---

# Fonction pour afficher le jour avec l'image dynamique
def display_day_content(jour_contenu_brut):
    image_url = None
    contenu_final = jour_contenu_brut
    image_keyword = "travel"
    image_match = re.search(r'- 📷 \*\*Image :\*\* \[(.*?)\]', jour_contenu_brut)
    if image_match:
        image_keyword = image_match.group(1).strip().replace(" ", ",")
        image_url = f"https://source.unsplash.com/800x600/?{image_keyword}"
        contenu_final = re.sub(r'- 📷 \*\*Image :\*\* \[.*?\]\n?', '', jour_contenu_brut).strip()
    if image_url:
        col_txt, col_img = st.columns([2, 1])
        with col_txt: st.markdown(contenu_final)
        with col_img: 
            st.image(image_url, caption=f"Inspiration for {image_keyword}", use_column_width=True)
            st.caption("Image dynamically sourced from Unsplash.")
    else:
        st.markdown(contenu_final)

# Fonction pour vérifier la clé de licence Lemon Squeezy
def verify_lemonsqueezy_license(license_key):
    try:
        headers = {
            'Accept': 'application/vnd.api+json',
            'Content-Type': 'application/vnd.api+json',
            'Authorization': f'Bearer {LEMON_API_KEY}'
        }
        data = { 'license_key': license_key.strip() }
        response = requests.post(
            f"https://api.lemonsqueezy.com/v1/licenses/validate",
            headers=headers,
            json=data
        )
        result = response.json()
        if result.get("valid") == True:
            instance = result.get("instance", {})
            product_id = instance.get("product_id")
            if str(product_id) == str(LEMON_PRODUCT_ID):
                return True, "License key validated!"
            else:
                return False, "This key is valid, but for the wrong product."
        else:
            return False, result.get("error", "Invalid license key.")
    except Exception as e:
        return False, f"Error connecting to verification API:
