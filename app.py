# Fichier: app.py
# LE MOTEUR FINAL (v2.1) - Utilise gr.Group pour la compatibilité

import gradio as gr
import google.generativeai as genai
import requests
import os
import re

# --- 1. CONFIGURATION DES SECRETS (Lus depuis Hugging Face) ---
try:
    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
    LEMON_API_KEY = os.environ.get("LEMONSQUEEZY_API_KEY")
    LEMON_PRODUCT_ID = os.environ.get("LEMONSQUEEZY_PRODUCT_ID")
    LEMON_STORE_ID = os.environ.get("LEMONSQUEEZY_STORE_ID")
    
    genai.configure(api_key=GEMINI_API_KEY)
except Exception as e:
    print(f"Erreur de Secrets: {e}")

# --- 2. PROMPT MAÎTRE (v2.0 - AVEC VOS NOUVELLES IDÉES) ---
PROMPT_MAITRE = """
Tu es 'Atlas', le concierge principal de "The Atlas Agency". Ta réputation repose sur la création d'itinéraires "indispensables".

MÉTA-RÈGLES CRUCIALES :
1.  **RÈGLE DE RYTHME (LA DURÉE) :** Analyse la `{duree}` totale. 
    * **Si 8+ jours (Long) :** Tu DOIS inclure des "Journées libres / repos" et des "Excursions d'une journée" (day trips) pour éviter l'ennui.
2.  **RÈGLE D'AUTHENTICITÉ (LANGUE LOCALE) :**
    * Tu dois simuler une recherche en langue locale pour trouver les vrais "joyaux cachés" et éviter les pièges à touristes.
3.  **RÈGLE D'ADAPTATION (NOUVEAU) :**
    * **Si `{van_life}` est 'Oui' :** NE PAS suggérer d'hôtels. Suggérer des spots de van, des campings, et des points d'eau. Les "liens pratiques" doivent pointer vers des parkings ou des aires de service.
    * **Si `{children_under_11}` est 'Oui' :** Toutes les activités (matin, après-midi) et les restaurants DOIVENT être adaptés aux familles et aux jeunes enfants.
    * **Point d'arrivée :** Le "Jour 1" DOIT commencer logiquement depuis `{arrival_point}` (ex: "Depuis l'aéroport, prenez le train RER B...").

---
INSTRUCTIONS CLIENT :
- Destination : {destination}
- Durée : {duree} jours
- Nombre de personnes : {persons}
- Enfants de moins de 11 ans : {children_under_11}
- Point d'arrivée (Gare/Aéroport/Adresse) : {arrival_point}
- Voyage en Van / Camping-car : {van_life}
- Budget (Général) : {budget}
- Intérêts principaux : {interets}
- Logistique & Rythme : {logistics}
- Contraintes Spécifiques : {specific_constraints}
- LANGUE FINALE : {langue}
---

MISSION :
Génère l'itinéraire complet. La structure Markdown est OBLIGATOIRE.

### JOUR 1 : [Titre thématique, DANS LA LANGUE {langue}]
- 📷 **Image :** [Mots-clés en ANGLAIS pour Unsplash]

- ☀️ **Matin :**
    - **Activité :** [Description adaptée aux enfants/van si nécessaire.]
    - **Le "Pourquoi" :** [Conseil d'initié/local.]
    - **Logistique :** [Temps sur place ET prix d'entrée (pour {persons} personnes).]
    - **Lien Pratique :** [Fournis un lien de recherche Google Maps pour le lieu. Ex: "http://googleusercontent.com/maps/api/staticmap"]

- 🍽️ **Midi :**
    - **Recommandation :** [Restaurant (adapté aux enfants si nécessaire).]
    - **Le "Pourquoi" :** [Pourquoi ce choix.]
    - **Logistique :** [Budget approx. pour {persons} personnes.]
    - **Lien Pratique :** [Lien Google Maps.]

- 🏛️ **Après-midi :**
    - **Activité :** [...]
    - **Le "Pourquoi" :** [...]
    - **Logistique :** [...]
    - **Lien Pratique :** [...]

- 🌙 **Soir :**
    - **Activité :** [Dîner ET (si van_life='Oui') OÙ SE GARER POUR LA NUIT.]
    - **Le "Pourquoi" :** [...]
    - **Logistique :** [...]
    - **Lien Pratique :** [...]

- 🎁 **Option Extra / Joyau Caché :**
    - [Une activité "bonus" à proximité.]

- 💡 **Résumé de la Journée :**
    - **Transport :** [Conseil global de transport (ex: "Prenez le Pass Métro Journée...").]
    - **Budget Approx. :** [Estimation du total de la journée (activités + nourriture). Ex: "Total estimé (hors shopping) : 85€"]

(Tu continues ce format pour TOUS les jours demandés.)

---
### 💰 RÉSUMÉ DU BUDGET (SUR PLACE)
À la toute fin, crée un résumé du budget total.
- **Budget Total Estimé (Sur Place) :** [Additionne TOUS les "Budget Approx." de chaque jour et donne le total.]
- **Note Importante :** [Précise que ce total ESTIME les activités, la nourriture et les transports locaux, mais **EXCLUT** les vols internationaux/nationaux et le logement (sauf si van/camping).]
"""

# --- 3. FONCTIONS TECHNIQUES ---

def verify_lemonsqueezy_license(license_key):
    """
    Contacte l'API Lemon Squeezy pour valider une clé de licence.
    """
    if not license_key:
        return False, "No license key provided."
        
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
        
        if response.status_code != 200:
             return False, result.get("error", "API communication error.")
             
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
        return False, f"Error connecting to verification API: {e}"

def extract_image_url(text):
    """
    Extrait le mot-clé de l'image du texte et retourne une URL Unsplash.
    """
    image_match = re.search(r'- 📷 \*\*Image :\*\* \[(.*?)\]', text)
    if image_match:
        image_keyword = image_match.group(1).strip().replace(" ", ",")
        return f"https://source.unsplash.com/800x600/?{image_keyword}"
    return None

# --- 4. LA LOGIQUE DE GÉNÉRATION ---
def generate_itinerary(
    # NOUVEAUX CHAMPS AJOUTÉS
    langue, destination, duree, budget, 
    persons, children_under_11, arrival_point, van_life,
    # (Champs existants)
    interest_culture, interest_food, interest_art, interest_shopping,
    interest_nature, interest_nightlife, interest_adventure, interest_relax,
    additional_requests,
    pace_relaxed, pace_moderate, pace_fast,
    transport_public, transport_walk, accessibility_wheelchair,
    specific_constraints,
    license_key
):
    
    # 1. Collecte les INTÉRÊTS
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

    # 2. Collecte la LOGISTIQUE
    logistics_list = []
    if pace_relaxed: logistics_list.append("Relaxed pace")
    if pace_moderate: logistics_list.append("Moderate pace")
    if pace_fast: logistics_list.append("Fast pace")
    if transport_public: logistics_list.append("Focus on public transport")
    if transport_walk: logistics_list.append("Focus on walking")
    if accessibility_wheelchair: logistics_list.append("Wheelchair accessible")
    
    final_logistics_str = ", ".join(logistics_list) if logistics_list else "None specified"
    
    # 3. Récupère les CONTRAINTES SPÉCIFIQUES
    final_constraints_str = specific_constraints if specific_constraints else "None"

    # 4. Gère la génération ou le déverrouillage
    try:
        # Appelle Gemini pour générer le contenu
        model = genai.GenerativeModel('gemini-1.5-flash-latest')
        prompt_final = PROMPT_MAITRE.format(
            destination=destination,
            duree=duree,
            persons=persons,
            children_under_11=children_under_11,
            arrival_point=arrival_point if arrival_point else "Non spécifié",
            van_life="Oui" if van_life else "Non",
            budget=budget,
            interets=final_interests_str,
            logistics=final_logistics_str,
            specific_constraints=final_constraints_str,
            langue=langue
        )
        response = model.generate_content(prompt_final)
        full_itinerary = response.text
        
        # Sépare le Jour 1 du reste
        jours = re.split(r'(### JOUR 2 :.*)', full_itinerary, 1, re.DOTALL)
        jour_1_text = jours[0].strip()
        jour_1_image_url = extract_image_url(jour_1_text)

        # 5. Logique de Paywall
        if not license_key:
            # PAS de clé : Montre l'aperçu gratuit
            return (
                jour_1_text, 
                jour_1_image_url, 
                gr.Column(visible=True), 
                gr.Column(visible=False)
            )
        else:
            # L'utilisateur a entré une clé
            is_valid, message = verify_lemonsqueezy_license(license_key)
            
            if is_valid:
                # Clé VALIDE : Montre tout
                # Sépare l'itinéraire du résumé budget
                parts = re.split(r'(### 💰 RÉSUMÉ DU BUDGET.*)', full_itinerary, 1, re.DOTALL)
                itinerary_part = parts[0].strip()
                budget_summary = parts[1] if len(parts) > 1 else "Budget non calculé."
                
                # Sépare le Jour 1 du reste de l'itinéraire
                jours_2_plus_match = re.search(r'(### JOUR 2 :.*)', itinerary_part, re.DOTALL)
                reste_itinerary = jours_2_plus_match.group(1) if jours_2_plus_match else "Aucun jour supplémentaire trouvé."
                
                # On combine le reste ET le résumé budget
                full_itinerary_content = reste_itinerary + "\n\n" + budget_summary

                return (
                    jour_1_text.split("### JOUR 2 :")[0].strip(), # Affiche Jour 1 seulement
                    jour_1_image_url,
                    gr.Column(visible=False), # Cache la boîte de déverrouillage
                    gr.Column(visible=True, value=full_itinerary_content) # Montre Jours 2+ ET le résumé
                )
            else:
                # Clé INVALIDE : Montre l'aperçu + erreur
                return (
                    jour_1_text,
                    jour_1_image_url,
                    gr.Column(visible=True, value=f"Erreur de clé: {message}"), # Montre la boîte + erreur
                    gr.Column(visible=False) # Cache le reste
                )

    except Exception as e:
        # S'il y a une erreur avec Gemini (ex: clé API)
        return str(e), None, gr.Column(visible=False), gr.Column(visible=False)


# --- 5. L'INTERFACE UTILISATEUR (CORRIGÉE AVEC gr.Group) ---
with gr.Blocks(theme=gr.themes.Monochrome(primary_hue="indigo", secondary_hue="blue"), css="footer {display: none !important}") as demo:
    
    gr.Markdown("# 🔑 The Atlas Agency\n*Votre itinéraire sur mesure, généré par IA.*")
    
    with gr.Row():
        # --- COLONNE 1 : LE FORMULAIRE ---
        with gr.Column(scale=1):
            gr.Markdown("### 1. Remplissez le formulaire")
            
            with gr.Accordion("Détails principaux", open=True):
                langue = gr.Dropdown(["English", "Français", "Español", "Deutsch", "Italiano", "Português", "日本語", "中文"], label="Langue de l'itinéraire", value="English")
                destination = gr.Textbox(label="Destination", placeholder="Ex: Tokyo, Japan")
                arrival_point = gr.Textbox(label="Point d'arrivée (Aéroport, Gare...)", placeholder="Ex: Aéroport de Tokyo-Narita (NRT)")
                duree = gr.Slider(1, 30, value=7, step=1, label="Nombre de jours")
                persons = gr.Number(label="Nombre de voyageurs (adultes)", value=2, precision=0)
                children_under_11 = gr.Radio(["Oui", "Non"], label="Enfants de moins de 11 ans ?", value="Non")
                budget = gr.Radio(["Economic", "Mid-range", "Luxury"], label="Budget (Général)", value="Mid-range")
            
            with gr.Accordion("Intérêts (Ce que vous voulez faire)", open=False):
                with gr.Row():
                    interest_culture = gr.Checkbox("🏛️ Culture & Museums")
                    interest_food = gr.Checkbox("🍜 Local Gastronomy")
                with gr.Row():
                    interest_art = gr.Checkbox("🎨 Art & Monuments")
                    interest_shopping = gr.Checkbox("🛍️ Shopping")
                with gr.Row():
                    interest_nature = gr.Checkbox("🌲 Nature & Parks")
                    interest_nightlife = gr.Checkbox("🌙 Nightlife")
                with gr.Row():
                    interest_adventure = gr.Checkbox("🚵 Adventure & Sports")
                    interest_relax = gr.Checkbox("🏖️ Relaxation")
                additional_requests = gr.Textbox(label="Intérêts Spécifiques / Incontournables", placeholder="Ex: Je dois voir le musée 'XYZ'...")

            with gr.Accordion("Logistique & Rythme (Comment vous voyagez)", open=False):
                van_life = gr.Checkbox("🚐 Voyage en Van / Camping-car")
                with gr.Row():
                    pace_relaxed = gr.Checkbox("🧘 Relaxed")
                    pace_moderate = gr.Checkbox("🏃 Moderate")
                    pace_fast = gr.Checkbox("⚡ Fast-Paced")
                with gr.Row():
                    transport_public = gr.Checkbox("🚇 Public Transport")
                    transport_walk = gr.Checkbox("🚶 Walking")
                accessibility_wheelchair = gr.Checkbox("♿ Wheelchair Accessible")
                specific_constraints = gr.Textbox(label="Contraintes Spécifiques (Allergies, Budget max...)", placeholder="Ex: Allergie aux cacahuètes, max 50€/jour...")

            generate_btn = gr.Button("Générer mon aperçu gratuit", variant="primary")

        # --- COLONNE 2 : LES RÉSULTATS ---
        with gr.Column(scale=2):
            gr.Markdown("### 2. Votre Itinéraire")
            
            # --- CORRIGÉ : gr.Box() remplacé par gr.Group() ---
            with gr.Group():
                gr.Markdown("#### ✨ Aperçu Gratuit (Jour 1)")
                jour_1_output = gr.Markdown("Remplissez le formulaire et cliquez sur 'Générer' pour voir votre Jour 1 ici.")
                jour_1_image = gr.Image(label="Inspiration Visuelle", type="filepath")
            
            with gr.Column(visible=False) as unlock_box:
                gr.Markdown("--- \n ### 🔒 Déverrouillez la suite !")
                gr.Markdown("Vous aimez cet aperçu ? Obtenez l'itinéraire complet pour **9,99€**.")
                
                # !! REMPLACEZ CE LIEN par votre lien de paiement de TEST (de Lemon Squeezy) !!
                gr.Markdown("[1. Achetez votre Clé de Licence Unique ici](https://theatlas.lemonsqueezy.com/buy/02e6f077-25c7-4d31-81d6-258588ff2ca4)")
                
                license_key_input = gr.Textbox(label="2. Collez votre clé de licence ici", placeholder="Ex: XXXX-XXXX-XXXX-XXXX", interactive=True)
                unlock_btn = gr.Button("Déverrouiller l'itinéraire complet")

            with gr.Column(visible=False) as full_itinerary_box:
                gr.Markdown("--- \n ### 🔑 Votre Itinéraire Complet (Jours 2+ et Résumé)")
                full_itinerary_output = gr.Markdown()

    # --- Connexions des Boutons ---
    all_inputs = [
        langue, destination, duree, budget, 
        persons, children_under_11, arrival_point, van_life,
        interest_culture, interest_food, interest_art, interest_shopping,
        interest_nature, interest_nightlife, interest_adventure, interest_relax,
        additional_requests,
        pace_relaxed, pace_moderate, pace_fast,
        transport_public, transport_walk, accessibility_wheelchair,
        specific_constraints,
        license_key_input
    ]
    
    generate_btn.click(
        fn=generate_itinerary,
        inputs=all_inputs,
        outputs=[jour_1_output, jour_1_image, unlock_box, full_itinerary_box]
    )
    
    unlock_btn.click(
        fn=generate_itinerary,
        inputs=all_inputs,
        outputs=[jour_1_output, jour_1_image, unlock_box, full_itinerary_box]
    )

# --- 6. Lancer l'application ---
#render fournit le port via la variable d'environnement PORT
#Nous utilisions 7860 comme valeur par défaut si nous l'exécutons localement
serveur_port = int(os.environ.get("PORT", 7860))
demo.launch(serveur_name="0.0.0.0", serveur_port=server_port)