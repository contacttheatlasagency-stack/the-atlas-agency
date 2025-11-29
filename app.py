# Fichier: app.py
# LE MOTEUR FINAL (v4.0 - OPENROUTER EDITION)

import gradio as gr
from openai import OpenAI # On utilise la librairie standard OpenAI
import requests
import os
import re

# --- 1. CONFIGURATION DES VARIABLES ---
# On récupère la clé OpenRouter.
# Si elle n'est pas là, on ne plante pas tout de suite, on gère l'erreur plus tard.
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
LEMON_API_KEY = os.environ.get("LEMONSQUEEZY_API_KEY")
LEMON_PRODUCT_ID = os.environ.get("LEMONSQUEEZY_PRODUCT_ID")

# --- 2. PROMPT MAÎTRE ---
PROMPT_MAITRE = """
Tu es 'Atlas', le concierge de luxe de "The Atlas Agency".

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
- Langue : {langue}

RÈGLES :
1. Van Life : Si "{van_life}"="Oui", spots de nuit précis (pas d'hôtels).
2. Enfants : Si {children_count} > 0, activités adaptées.
3. Format Markdown strict.

STRUCTURE :
### JOUR 1 : [Titre]
- 📷 **Image :** [Mots-clés ANGLAIS pour Unsplash]
- ☀️ **Matin :** [Activité + Logistique + Lien Maps]
- 🍽️ **Midi :** [Resto/Pique-nique + Budget]
- 🏛️ **Après-midi :** [Activité + Logistique + Lien Maps]
- 🌙 **Soir :** [Dîner + Dodo précis]
- 💡 **Conseil Atlas :** [Astuce]

---
(Répète pour les autres jours)
---
### 💰 BUDGET ESTIMÉ
Total approx (hors vols).
"""

# --- 3. FONCTIONS TECHNIQUES ---

def verify_lemonsqueezy_license(license_key):
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
    m = re.search(r'- 📷 \*\*Image :\*\* \[(.*?)\]', text)
    return f"https://source.unsplash.com/800x600/?{m.group(1).strip().replace(' ', ',')}" if m else None

# --- 4. GÉNÉRATION VIA OPENROUTER ---
def generate_itinerary(langue, destination, duree, budget, persons, children_count, arrival_point, van_life, 
                       ic, ifood, iart, ishop, inat, inight, iadv, irelax, add_req, 
                       prelax, pmod, pfast, tpub, twalk, acc_wheel, constr, license_key):
    
    # Préparation des données
    interests = []
    if ic: interests.append("Culture")
    if ifood: interests.append("Gastronomie")
    if iart: interests.append("Art")
    if ishop: interests.append("Shopping")
    if inat: interests.append("Nature")
    if inight: interests.append("Sorties")
    if iadv: interests.append("Aventure")
    if irelax: interests.append("Détente")
    final_interests = ", ".join(interests) + (f", {add_req}" if add_req else "")
    
    logistics = []
    if prelax: logistics.append("Relax")
    if pmod: logistics.append("Modéré")
    if pfast: logistics.append("Intense")
    if tpub: logistics.append("Transports publics")
    if twalk: logistics.append("Marche")
    if acc_wheel: logistics.append("PMR")
    final_logistics = ", ".join(logistics)

    # --- APPEL OPENROUTER ---
    try:
        if not OPENROUTER_API_KEY:
            return "ERREUR : La clé OPENROUTER_API_KEY est manquante sur Render.", None, gr.Column(visible=False), gr.Column(visible=False)

        # Configuration du client (C'est ici que ça change tout !)
        client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=OPENROUTER_API_KEY,
            default_headers={"HTTP-Referer": "https://the-atlas-agency.onrender.com", "X-Title": "Atlas Agency"}
        )

        prompt = PROMPT_MAITRE.format(
            destination=destination, duree=duree, persons=persons, children_count=children_count,
            arrival_point=arrival_point or "Non précisé", van_life="Oui" if van_life else "Non",
            budget=budget, interets=final_interests or "Général", logistics=final_logistics,
            specific_constraints=constr or "Aucune", langue=langue
        )

        completion = client.chat.completions.create(
            # VOUS POUVEZ CHANGER LE MODÈLE ICI (ex: "meta-llama/llama-3.3-70b-instruct:free")
            model="google/gemini-2.0-flash-exp:free", 
            messages=[
                {"role": "system", "content": "Tu es un expert voyage."},
                {"role": "user", "content": prompt}
            ]
        )
        
        full_text = completion.choices[0].message.content
        
        # Traitement du texte (identique à avant)
        splits = re.split(r'(### JOUR 2 :.*)', full_text, 1, re.DOTALL)
        day1 = splits[0].strip()
        img_url = extract_image_url(day1)
        
        if not license_key:
            return day1, img_url, gr.Column(visible=True), gr.Column(visible=False)
        
        is_valid, msg = verify_lemonsqueezy_license(license_key)
        if is_valid:
            rest = splits[1] if len(splits) > 1 else "Fin."
            return day1.split("### JOUR 2")[0], img_url, gr.Column(visible=False), gr.Column(visible=True, value=rest)
        else:
            return day1, img_url, gr.Column(visible=True, value=f"⚠️ {msg}"), gr.Column(visible=False)

    except Exception as e:
        return f"Erreur OpenRouter : {e}", None, gr.Column(visible=False), gr.Column(visible=False)

# --- 5. INTERFACE ---
with gr.Blocks(theme=gr.themes.Monochrome(), css="footer {display:none}") as demo:
    gr.Markdown("# 🌍 The Atlas Agency (v4.0)\n*Propulsé par OpenRouter AI*")
    
    with gr.Row():
        with gr.Column(scale=1):
            with gr.Accordion("Voyage", open=True):
                langue = gr.Dropdown(["Français", "English", "Español"], label="Langue", value="Français")
                dest = gr.Textbox(label="Destination")
                arrivee = gr.Textbox(label="Arrivée")
                duree = gr.Slider(1, 30, 7, 1, label="Jours")
                with gr.Row():
                    adultes = gr.Number(label="Adultes", value=2)
                    enfants = gr.Number(label="Enfants", value=0)
                budget = gr.Radio(["Eco", "Standard", "Luxe"], label="Budget", value="Standard")
            
            with gr.Accordion("Préférences", open=False):
                van = gr.Checkbox(label="Voyage en Van")
                with gr.Row(): 
                    c_cult = gr.Checkbox(label="Culture")
                    c_food = gr.Checkbox(label="Gastronomie")
                    c_nat = gr.Checkbox(label="Nature")
                    c_relax = gr.Checkbox(label="Détente")
                autre = gr.Textbox(label="Autre")
            
            with gr.Accordion("Rythme", open=False):
                with gr.Row():
                    p_cool = gr.Checkbox(label="Cool")
                    p_speed = gr.Checkbox(label="Intense")
                pmr = gr.Checkbox(label="PMR")
                constr = gr.Textbox(label="Contraintes")

            btn = gr.Button("🚀 Générer l'itinéraire", variant="primary")

        with gr.Column(scale=2):
            with gr.Group():
                res_j1 = gr.Markdown("### Votre voyage commence ici...")
                img_j1 = gr.Image(show_label=False, height=300)
            
            with gr.Column(visible=False) as box_lock:
                gr.Markdown("### 🔒 Version Complète")
                gr.Markdown("Débloquez la suite pour **9.99€**.")
                gr.Markdown("[Acheter ma licence](https://theatlas.lemonsqueezy.com/buy/02e6f077-25c7-4d31-81d6-258588ff2ca4)")
                key_input = gr.Textbox(label="Clé de licence")
                btn_unlock = gr.Button("Déverrouiller")
            
            with gr.Column(visible=False) as box_full:
                res_full = gr.Markdown()

    inputs = [langue, dest, duree, budget, adultes, enfants, arrivee, van, 
              c_cult, c_food, c_cult, c_cult, c_nat, c_nat, c_nat, c_relax, autre,
              p_cool, p_cool, p_speed, p_speed, p_speed, pmr, constr, key_input]
    
    btn.click(generate_itinerary, inputs, [res_j1, img_j1, box_lock, box_full])
    btn_unlock.click(generate_itinerary, inputs, [res_j1, img_j1, box_lock, box_full])

port = int(os.environ.get("PORT", 7860))
demo.launch(server_name="0.0.0.0", server_port=port, share=True)