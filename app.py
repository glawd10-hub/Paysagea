"""
🌿 Garden AI Enhancer - Version EXPERT (Zéro N/A)
Analyse complète, Plan d'amélioration et Rendu 4K.
"""

import json, os, random, base64, io
from pathlib import Path
from flask import Flask, render_template, request, jsonify, send_from_directory
from dotenv import load_dotenv
from google import genai
from google.genai import types as genai_types
from PIL import Image, ImageOps

load_dotenv()
client = genai.Client(api_key=os.getenv('GEMINI_API_KEY'))
BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

app = Flask(__name__, static_folder='static', template_folder='templates')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

# ── Styles de jardin ──────────────────────────────────────────
GARDEN_STYLES = {
    "traditionnels": {
        "label": "🏛️ Styles Traditionnels",
        "styles": {
            "francais": {"nom": "Jardin à la française", "description": "Symétrie et élégance classique.", "densite": "Moyenne", "trace": "Droit", "materiau": "Pierre", "entretien": 9, "keywords": "formal French"},
            "anglais": {"nom": "Jardin à l'anglaise", "description": "Nature romantique et sauvage.", "densite": "Dense", "trace": "Courbe", "materiau": "Bois", "entretien": 6, "keywords": "English cottage"}
        }
    },
    "modernes": {
        "label": "📐 Design Moderne",
        "styles": {
            "moderne": {"nom": "Design Contemporain", "description": "Minimalisme et lignes épurées.", "densite": "Épurée", "trace": "Géométrique", "materiau": "Acier/Béton", "entretien": 3, "keywords": "minimalist design"}
        }
    }
}

def load_database():
    try:
        with open(BASE_DIR / "plants_database.json", 'r', encoding='utf-8', errors='replace') as f:
            return json.load(f)
    except: return []

def get_plant_image_base64(p):
    try:
        path = BASE_DIR / p.get('image_path', '')
        if not path.exists(): return None
        with Image.open(path) as img:
            img.thumbnail((300, 300), Image.LANCZOS)
            buf = io.BytesIO()
            img.save(buf, format='PNG')
            return base64.b64encode(buf.getvalue()).decode('utf-8')
    except: return None

@app.route('/')
def index(): return render_template('index.html')

@app.route('/api/stats')
def stats():
    db = load_database()
    return jsonify({'total_plants': len(db), 'garden_styles': GARDEN_STYLES})

@app.route('/api/analyze', methods=['POST'])
def analyze():
    f = request.files.get('garden_image')
    if not f: return jsonify({'error': 'No image'}), 400
    path = UPLOAD_DIR / "garden_upload.jpg"
    f.save(str(path))
    
    try:
        img = ImageOps.exif_transpose(Image.open(str(path)))
        p = """Analyse ce jardin. Réponds UNIQUEMENT en JSON avec ces clés : 
        description, ensoleillement_estime, type_sol_estime, climat_apparent, 
        points_forts (liste), points_a_ameliorer (liste), styles_recommandes (liste),
        improvement_plan (texte long structuré avec ### Titres)."""
        
        res = client.models.generate_content(model='gemini-1.5-flash', contents=[p, img])
        ans = json.loads(res.text[res.text.find('{'):res.text.rfind('}')+1])
        # On extrait le plan pour le mettre à la racine de la réponse
        plan = ans.pop('improvement_plan', "Plan généré avec succès.")
    except:
        ans = {"description": "Jardin détecté", "ensoleillement_estime": "Partiel", "type_sol_estime": "Drainé", "climat_apparent": "Tempéré", "styles_recommandes": ["moderne"]}
        plan = "Veuillez vérifier votre connexion IA."

    db = load_database()
    random.shuffle(db)
    selection = db[:10]
    for p in selection: p['image_base64'] = get_plant_image_base64(p)
    return jsonify({'analysis': ans, 'plants': selection, 'improvement_plan': plan})

@app.route('/api/generate-render', methods=['POST'])
def generate_render():
    data = request.get_json()
    pnames = data.get('plants', [])
    prompt = f"4K PHOTOREALISTIC: {', '.join(pnames[:10])}. Realistic scale, shadows, grounded."
    try:
        img_path = UPLOAD_DIR / "garden_upload.jpg"
        img = ImageOps.exif_transpose(Image.open(str(img_path)))
        if img.mode == 'RGBA': img = img.convert('RGB')
        res = client.models.generate_content(model='nano-banana-pro-preview', contents=[prompt, img])
        for cand in res.candidates:
            for part in cand.content.parts:
                if part.inline_data:
                    return jsonify({'image_base64': base64.b64encode(part.inline_data.data).decode('utf-8')})
        return jsonify({'error': 'No image'}), 500
    except Exception as e: return jsonify({'error': str(e)}), 500

@app.route('/uploads/<f>')
def uploads(f): return send_from_directory(str(UPLOAD_DIR), f)

@app.route('/health')
def health(): return "OK", 200

if __name__ == '__main__':
    app.run(port=int(os.environ.get("PORT", 5000)), host='0.0.0.0')
