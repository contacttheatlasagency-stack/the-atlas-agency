# Fichier: app.py
# LE MOTEUR FINAL (v3.1 - FIX UI & ENFANTS)

import gradio as gr
import google.generativeai as genai
import requests
import os
import re

# --- 1. CONFIGURATION DES SECRETS ---
try:
    # On lit les variables, mais on ne configure PAS l'API ici pour éviter le crash au démarrage
    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
    LEMON_API_KEY = os.environ.get("LEMONSQUEEZY_API_KEY")
    LEMON_PRODUCT_ID = os.environ.get("LEMONSQUEEZY_PRODUCT_ID")
    LEMON_STORE_ID = os.environ.get("LEMONSQUEEZY_STORE_ID")
except Exception as e:
    print(f"Erreur de lecture des variables: {e}")

# --- 2. PROMPT MAÎTRE (OPTIMISÉ GEMINI PRO) ---
PROMPT_MAITRE = """
Tu es 'Atlas', le concierge de luxe de "The Atlas Agency". Tu crées des itinéraires de voyage hyper-détaillés et réalistes.

DONNÉES CLIENT :
- Destination : {destination}
- Durée : {duree} jours
- Groupe : {persons} adultes + {children_count} enfants.
- Arrivée : {arrival_point}
- Mode Van Life : {van_life}
- Budget : {budget}
- Intérêts : {interets}
- Rythme : {logistics}
- Contraintes : {specific_constraints}
- Langue de réponse : {langue}

RÈGLES STRICTES :
1. **Van Life :** Si "{van_life}" est "Oui", ignore les hôtels. Trouve des spots de nuit (camping, aires nature) précis.
2. **Enfants :** Si il y a des enfants ({children_count} > 0), le rythme doit être adapté. Si enfants en bas âge, prévoir des parcs et pauses.
3. **Réalisme :** Ne bourre pas les journées. Prends en compte les temps de trajet.

STRUCTURE REQUISE (MARKDOWN) :

### JOUR 1 : [Titre du jour]
- 📷 **Image :** [Mots-clés ANGLAIS pour la photo]

- ☀️ **Matin (09:00 - 12:00) :**
    - **Quoi :** [Activité précise]
    - **Pourquoi :** [L'argument "Atlas" unique]
    - **Logistique :** [Prix & Durée]
    - **Lien :** [Lien Google Maps]

- 🍽️ **Déjeuner (12:30) :**
    - **Lieu :** [Nom du resto ou type de pique-nique]
    - **Budget :** [Prix approx]

- 🏛️ **Après-midi (14:30 - 18:00) :**
    - **Quoi :** [Activité culturelle ou détente]
    - **Pourquoi :** [Le détail qui tue]
    - **Lien :** [Lien Google Maps]

- 🌙 **Soirée & Nuit :**
    - **Dîner :** [Resto ou cuisine locale]
    - **Dodo :** [Adresse hôtel ou Spot Van précis avec coordonnées]

- 💡 **Le Conseil d'Atlas :** [Une astuce transport ou "piège à touristes" à éviter ce jour-là]

---
(Répète pour chaque jour)
---

### 💰 ESTIMATION BUDGET (Sur place)
Calcul approximatif (hors vols) pour tout le séjour : [Montant]
"""

# --- 3. FONCTIONS TECHNIQUES ---

def verify_lemonsqueezy_license(license_key):
    """Vérifie la licence payante."""
    if not license_key: return False, "Clé manquante."
    try:
        headers = {'Accept': 'application/vnd.api+json', 'Authorization': f'Bearer {LEMON_API_KEY}'}
        r = requests.post("https://api.lemonsqueezy.com/v1/licenses/validate", headers=headers, json={'license_key': license_key.strip()})
        if r.status_code != 200: return False, "Erreur API."
        res = r.json()
        if res.get("valid") and str(res['instance']['product_id']) == str(LEMON_PRODUCT_ID):
            return True, "Validé."
        return False, "Clé invalide."
    except: return False, "Erreur connexion."

def extract_image_url(text):
    """Trouve l'image dans le texte."""
    m = re.search(r'- 📷 \*\*Image :\*\* \[(.*?)\]', text)
    return f"https://source.unsplash.com/800x600/?{m.group(1).strip().replace(' ', ',')}" if m else None

# --- 4. CŒUR DU SYSTÈME ---
def generate_itinerary(langue, destination, duree, budget, persons, children_count, arrival_point, van_life, 
                       ic, ifood, iart, ishop, inat, inight, iadv, irelax, add_req, 
                       prelax, pmod, pfast, tpub, twalk, acc_wheel, constr, license_key):
    
    # Construction des listes d'intérêts
    interests = []
    if ic: interests.append("Culture")
    if ifood: interests.append("Gastronomie")
    if iart: interests.append("Art")
    if ishop: interests.append("Shopping")
    if inat: interests.append("Nature")
    if inight: interests.append("Vie Nocturne")
    if iadv: interests.append("Aventure")
    if irelax: interests.append("Détente")
    final_interests = ", ".join(interests) + (f", {add_req}" if add_req else "")
    
    logistics = []
    if prelax: logistics.append("Relax")
    if pmod: logistics.append("Modéré")
    if pfast: logistics.append("Intense")
    if tpub: logistics.append("Transports en commun")
    if twalk: logistics.append("Marche")
    if acc_wheel: logistics.append("Accès PMR")
    final_logistics = ", ".join(logistics)

    try:
        # --- CONFIGURATION API AU MOMENT DU CLIC (Anti-Crash) ---
        genai.configure(api_key=GEMINI_API_KEY)
        
        # --- UTILISATION DE GEMINI 1.5 PRO ---
        model = genai.GenerativeModel('gemini-1.5-pro') 
        
        prompt = PROMPT_MAITRE.format(
            destination=destination, duree=duree, persons=persons, children_count=children_count,
            arrival_point=arrival_point or "Non précisé", van_life="Oui" if van_life else "Non",
            budget=budget, interets=final_interests or "Général", logistics=final_logistics,
            specific_constraints=constr or "Aucune", langue=langue
        )
        
        response = model.generate_content(prompt)
        full_text = response.text
        
        # Découpage du texte
        splits = re.split(r'(### JOUR 2 :.*)', full_text, 1, re.DOTALL)
        day1 = splits[0].strip()
        img_url = extract_image_url(day1)
        
        # Logique Paywall
        if not license_key:
            return day1, img_url, gr.Column(visible=True), gr.Column(visible=False)
        
        is_valid, msg = verify_lemonsqueezy_license(license_key)
        if is_valid:
            # On nettoie le texte pour afficher la suite
            rest = splits[1] if len(splits) > 1 else "Fin de l'itinéraire."
            return day1.split("### JOUR 2")[0], img_url, gr.Column(visible=False), gr.Column(visible=True, value=rest)
        else:
            return day1, img_url, gr.Column(visible=True, value=f"⚠️ {msg}"), gr.Column(visible=False)

    except Exception as e:
        err = str(e).upper()
        if "API_KEY" in err or "NOT FOUND" in err:
            debug_msg = "ERREUR CRITIQUE : La clé GEMINI_API_KEY est introuvable sur Render. Vérifiez vos Variables d'Environnement."
        else:
            debug_msg = f"Erreur technique : {e}"
        return debug_msg, None, gr.Column(visible=False), gr.Column(visible=False)

# --- 5. INTERFACE ---
with gr.Blocks(theme=gr.themes.Monochrome(), css="footer {display:none}") as demo:
    gr.Markdown("# 🌍 The Atlas Agency (v3.1)\n*Propulsé par Gemini 1.5 Pro*")
    
    with gr.Row():
        with gr.Column(scale=1):
            with gr.Accordion("Voyage", open=True):
                langue = gr.Dropdown(["Français", "English", "Español"], label="Langue", value="Français")
                dest = gr.Textbox(label="Destination", placeholder="Ex: Tokyo, Japon")
                arrivee = gr.Textbox(label="Arrivée (Aéroport/Gare)")
                duree = gr.Slider(1, 30, 7, 1, label="Jours")
                
                with gr.Row():
                    adultes = gr.Number(label="Adultes", value=2, precision=0)
                    # MODIFICATION ICI : Nombre d'enfants au lieu de Oui/Non
                    enfants = gr.Number(label="Enfants (-11 ans)", value=0, precision=0)
                
                budget = gr.Radio(["Eco", "Standard", "Luxe"], label="Budget", value="Standard")
            
            with gr.Accordion("Préférences", open=False):
                van = gr.Checkbox(label="🚐 Voyage en Van")
                # MODIFICATION ICI : Labels explicites pour corriger l'affichage
                with gr.Row(): 
                    c_cult = gr.Checkbox(label="🏛️ Culture")
                    c_food = gr.Checkbox(label="🍜 Gastronomie")
                with gr.Row():
                    c_art = gr.Checkbox(label="🎨 Art")
                    c_shop = gr.Checkbox(label="🛍️ Shopping")
                with gr.Row():
                    c_nat = gr.Checkbox(label="🌲 Nature")
                    c_night = gr.Checkbox(label="💃 Sorties")
                with gr.Row():
                    c_sport = gr.Checkbox(label="🏅 Sport")
                    c_relax = gr.Checkbox(label="🏖️ Détente")
                autre = gr.Textbox(label="Autre envie ?")
            
            with gr.Accordion("Rythme", open=False):
                with gr.Row():
                    p_cool = gr.Checkbox(label="🧘 Cool")
                    p_moy = gr.Checkbox(label="🏃 Modéré")
                    p_speed = gr.Checkbox(label="⚡ Intense")
                with gr.Row():
                    t_pub = gr.Checkbox(label="🚇 Transports publics")
                    t_pied = gr.Checkbox(label="🚶 Marche")
                pmr = gr.Checkbox(label="♿ Accès PMR")
                constr = gr.Textbox(label="Contraintes (Allergies...)")

            btn = gr.Button("🚀 Générer l'itinéraire", variant="primary")

        with gr.Column(scale=2):
            with gr.Group():
                res_j1 = gr.Markdown("### Votre voyage commence ici...")
                img_j1 = gr.Image(show_label=False, height=300)
            
            with gr.Column(visible=False) as box_lock:
                gr.Markdown("### 🔒 Version Complète")
                gr.Markdown("Débloquez la suite pour **9.99€**.")
                # LIEN LEMON SQUEEZY
                gr.Markdown("[Acheter ma licence](https://theatlas.lemonsqueezy.com/buy/02e6f077-25c7-4d31-81d6-258588ff2ca4)")
                key_input = gr.Textbox(label="Clé de licence")
                btn_unlock = gr.Button("Déverrouiller")
            
            with gr.Column(visible=False) as box_full:
                res_full = gr.Markdown()

    inputs = [langue, dest, duree, budget, adultes, enfants, arrivee, van, 
              c_cult, c_food, c_art, c_shop, c_nat, c_night, c_sport, c_relax, autre,
              p_cool, p_moy, p_speed, t_pub, t_pied, pmr, constr, key_input]
    
    btn.click(generate_itinerary, inputs, [res_j1, img_j1, box_lock, box_full])
    btn_unlock.click(generate_itinerary, inputs, [res_j1, img_j1, box_lock, box_full])

# LANCEMENT
port = int(os.environ.get("PORT", 7860))
demo.launch(server_name="0.0.0.0", server_port=port, share=True)