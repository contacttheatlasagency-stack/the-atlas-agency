
# Fichier: app.py
# LE MOTEUR COMPLET POUR "THE ATLAS AGENCY"
# Version corrigée et vérifiée

import streamlit as st
import google.generativeai as genai
import re
import requests 

# --- 1. CONFIGURATION DE LA PAGE ---
st.set_page_config(
    page_title="The Atlas Agency - Generator", 
    page_icon="🔑", 
    layout="wide"
)

# --- 2. CSS POUR LE DESIGN "FRAIS" (MODE SOMBRE) ---
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
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    LEMON_API_KEY = st.secrets["LEMONSQUEEZY_API_KEY"]
    LEMON_PRODUCT_ID = st.secrets["LEMONSQUEEZY_PRODUCT_ID"]
    LEMON_STORE_ID = st.secrets["LEMONSQUEEZY_STORE_ID"]
except Exception as e:
    st.error(f"Erreur: Secrets non configurés. Assurez-vous d'avoir ajouté vos 4 clés (TEST) dans les Secrets Streamlit.")

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
    - **Lien Pratique :** [Fournis un lien de recherche Google Maps pour le lieu. Ex: "http://googleusercontent.com/maps/api/staticmap"]

- 🍽️ **Midi :**
    - **Recommandation :** [Un type de cuisine ou une suggestion de restaurant (correspondant au budget).]
    - **Le "Pourquoi" :** [Ex: "C'est un favori local, pas un piège à touristes." ou "Parfait pour une bouchée rapide."]
    - **Logistique :** [Estimation du prix. Ex: "Budget : env. 10-15€ par personne"]
    - **Lien Pratique :** [Lien de recherche Google Maps. Ex: "http://googleusercontent.com/maps/api/staticmap"]

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
        # --- C'EST LA LIGNE QUI A ÉTÉ CORRIGÉE ---
        return False, f"Error connecting to verification API: {e}"

# --- 7. INTERFACE UTILISATEUR (LES DEUX COLONNES) ---
col1, col2 = st.columns([1, 2]) # Formulaire à gauche (1/3), résultats à droite (2/3)

# --- COLONNE 1 : LE FORMULAIRE ---
with col1:
    # (Remplacez ce lien par votre propre logo hébergé, ex: sur Imgur)
    st.image("https://i.imgur.com/vHqjM8K.png", width=200) 
    st.title("The Atlas Agency") # Votre nouveau nom
    st.markdown("Your trip is locked. Fill the form to unlock Day 1.")
    
    # Le formulaire commence ici
    with st.form(key="travel_form"):
        langue = st.selectbox("Itinerary Language", options=["English", "Français", "Español", "Deutsch", "Italiano", "Português", "日本語", "中文"])
        destination = st.text_input("Destination (City or Country)", placeholder="Ex: Tokyo, Japan")
        duree = st.number_input("Number of days", min_value=1, max_value=30, value=7)
        budget_options = ["Economic", "Mid-range", "Luxury"]
        budget = st.selectbox("Budget (General)", options=budget_options)
        
        st.divider()
        st.subheader("Interests (What you want to do)")
        
        # Grille d'icônes pour les Intérêts
        col_c1, col_c2 = st.columns(2)
        with col_c1: interest_culture = st.checkbox("🏛️ Culture & Museums")
        with col_c2: interest_food = st.checkbox("🍜 Local Gastronomy")
        col_c3, col_c4 = st.columns(2)
        with col_c3: interest_art = st.checkbox("🎨 Art & Monuments")
        with col_c4: interest_shopping = st.checkbox("🛍️ Shopping")
        col_c5, col_c6 = st.columns(2)
        with col_c5: interest_nature = st.checkbox("🌲 Nature & Parks")
        with col_c6: interest_nightlife = st.checkbox("🌙 Nightlife")
        col_c7, col_c8 = st.columns(2)
        with col_c7: interest_adventure = st.checkbox("🚵 Adventure & Sports")
        with col_c8: interest_relax = st.checkbox("🏖️ Relaxation")
        
        # Champ de texte pour les Intérêts Spécifiques
        additional_requests = st.text_area(
            "Specific Interests / Must-sees (Optional)", 
            placeholder="Ex: I must visit the 'XYZ' museum, I want to find a street art tour..."
        )
        
        st.divider()
        
        # NOUVEAU BLOC : CONTRAINTES & LOGISTIQUE
        st.subheader("Logistics & Pace (How you want to travel)")
        
        # Cases pour le Rythme
        col_p1, col_p2, col_p3 = st.columns(3)
        with col_p1: pace_relaxed = st.checkbox("🧘 Relaxed")
        with col_p2: pace_moderate = st.checkbox("🏃 Moderate")
        with col_p3: pace_fast = st.checkbox("⚡ Fast-Paced")
        
        # Cases pour le Transport
        col_t1, col_t2 = st.columns(2)
        with col_t1: transport_public = st.checkbox("🚇 Public Transport")
        with col_t2: transport_walk = st.checkbox("🚶 Walking")
            
        # Case pour l'Accessibilité
        accessibility_wheelchair = st.checkbox("♿ Wheelchair Accessible")
        
        # Champ de texte pour les Contraintes Spécifiques
        specific_constraints = st.text_area(
            "Specific Constraints & Details (Optional)", 
            placeholder="Ex: Peanut allergy, max 50€/day for food, no taxis, must leave hotel after 9am..."
        )
        
        # Le bouton de soumission
        submit_button = st.form_submit_button(label="Generate my free preview")

# --- 8. LOGIQUE DE GÉNÉRATION (QUAND LE BOUTON EST CLIQUÉ) ---
if submit_button and destination:
    # 1. Collecte les INTÉRÊTS (Cases + Texte)
    interests_list = []
    if interest_culture: interests_list.append("Culture & Museums")
    if interest_food: interests_list.append("Local Gastronomy")
    if interest_art: interests_list.append("Art & Monuments")
    if interest_shopping: interests_list.append("Shopping")
    if interest_nature: interests_list.append("Nature & Parks")
    if interest_nightlife: interests_list.append("Nightlife")
    if interest_adventure: interests_list.append("Adventure & Sports")
    if interest_relax: interests_list.append("Relaxation")
    
    final_interests_str = ", ".join(interests_list)
    if additional_requests:
        final_interests_str += f", {additional_requests}"
    if not final_interests_str:
        final_interests_str = "any"

    # 2. Collecte la LOGISTIQUE (Nouvelles Cases)
    logistics_list = []
    if pace_relaxed: logistics_list.append("Relaxed pace")
    if pace_moderate: logistics_list.append("Moderate pace")
    if pace_fast: logistics_list.append("Fast pace")
    if transport_public: logistics_list.append("Focus on public transport")
    if transport_walk: logistics_list.append("Focus on walking")
    if accessibility_wheelchair: logistics_list.append("Wheelchair accessible")
    
    final_logistics_str = ", ".join(logistics_list) if logistics_list else "None specified"
    
    # 3. Récupère les CONTRAINTES SPÉCIFIQUES (Nouveau Texte)
    final_constraints_str = specific_constraints if specific_constraints else "None"

    # 4. Lance la génération
    with st.spinner(f"Your AI art director is preparing your trip in {langue}..."):
        try:
            # Crée le prompt final avec les nouveaux champs
            prompt_final = PROMPT_MAITRE.format(
                destination=destination,
                duree=duree,
                budget=budget,
                interets=final_interests_str,
                logistics=final_logistics_str, 
                specific_constraints=final_constraints_str, 
                langue=langue
            )
            
            # Appelle Gemini
            model = genai.GenerativeModel('gemini-1.5-flash')
            response = model.generate_content(prompt_final)
            
            # Sauvegarde le résultat
            st.session_state.itinerary_generated = response.text
            st.session_state.unlocked = False 
            st.success("Visual preview generated!")
            
        except Exception as e:
            st.error(f"Error during generation: {e}")

# --- 9. COLONNE 2 : LES RÉSULTATS (AVEC VERROUILLAGE) ---
with col2:
    st.header("Your Visual Itinerary")
    
    # Si aucun itinéraire n'a encore été généré
    if st.session_state.itinerary_generated is None:
        st.info("Please fill the form on the left to generate your preview.")
    else:
        # S'il y a un itinéraire, on l'affiche
        jours = re.split(r'(### JOUR \d+ :.*)', st.session_state.itinerary_generated)[1:]
        
        if not jours:
            st.warning("The AI could not format the itinerary. Please try again.")
        else:
            # AFFICHE LE JOUR 1 (Gratuit)
            st.markdown(f"## {jours[0].replace('### ', '')}")
            display_day_content(jours[1])
            st.divider()
            
            # --- Le Mur de Paiement (Paywall) ---
            if not st.session_state.unlocked:
                st.info("Love this preview? Unlock the full trip!")
                
                # !! ASSUREZ-VOUS QUE CE LIEN EST VOTRE VRAI LIEN DE TEST LEMON SQUEEZY !!
                st.link_button("1. Buy your Unique License Key (9,99€)", "https://theatlas.lemonsqueezy.com/buy/02e6f077-25c7-4d31-81d6-258588ff2ca4")
                
                # Champ pour la clé de licence
                license_key_input = st.text_input("2. Enter your License Key", placeholder="Ex: XXXX-XXXX-XXXX-XXXX")
                
                if license_key_input:
                    # Si l'utilisateur entre une clé, on la vérifie
                    is_valid, message = verify_lemonsqueezy_license(license_key_input)
                    
                    if is_valid:
                        st.session_state.unlocked = True # Déverrouille !
                        st.success(f"{message} 🎉 Unlocked!")
                        st.rerun() # Recharge la page pour afficher le contenu
                    else:
                        st.error(message)

            # --- Affichage du reste des jours (si déverrouillé) ---
            for i in range(2, len(jours), 2):
                jour_titre = jours[i].replace('### ', '')
                jour_contenu = jours[i+1]
                
                if st.session_state.unlocked:
                    # Si c'est déverrouillé, on affiche un accordéon cliquable
                    with st.expander(f"## {jour_titre}"):
                        display_day_content(jour_contenu)
                else:
                    # Sinon, on affiche un accordéon grisé et verrouillé
                    st.expander(f"## {jour_titre} [🔒 LOCKED]", disabled=True)