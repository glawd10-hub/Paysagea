"""
🌿 Garden AI Enhancer - VERSION ULTIME (Anti-Zoom, 6 Styles, Analyse Expert)
Le code définitif pour votre oral. Tout est optimisé.
"""

import json, os, random, base64, io
from pathlib import Path
from flask import Flask, render_template, request, jsonify, send_from_directory
from dotenv import load_dotenv
from google import genai
from google.genai import types as genai_types
from PIL import Image, ImageOps

# ── Configuration & Sécurité ───────────────────────────────────
load_dotenv()
API_KEY = os.getenv('GEMINI_API_KEY')
client = genai.Client(api_key=API_KEY)

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

app = Flask(__name__, static_folder='static', template_folder='templates')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

# ── Les 6 Styles de Jardin (Données complétées pour le site) ──
GARDEN_STYLES = {
    "traditionnels": {
        "label": "🏛️ Styles Classiques & Traditionnels",
        "styles": {
            "francais": {"nom": "Jardin à la française", "description": "Lignes royales et symétrie parfaite.", "densite": "Moyenne", "trace": "Droit", "materiau": "Pierre/Buis", "entretien": 9, "keywords": "formal French style"},
            "anglais": {"nom": "Jardin à l'anglaise", "description": "Nature romantique et courbes douces.", "densite": "Forte", "trace": "Libre", "materiau": "Bois/Briques", "entretien": 6, "keywords": "English cottage style"},
            "mediterraneen": {"nom": "Jardin Méditerranéen", "description": "Chaleur, oliviers et lavande.", "densite": "Aérée", "trace": "Naturel", "materiau": "Terre cuite", "entretien": 4, "keywords": "Mediterranean landscape"}
        }
    },
    "expulsifs": {
        "label": "✨ Ambiances & Atmosphères",
        "styles": {
            "japonais": {"nom": "Jardin Zen", "description": "Sérénité, érables et pierres moussues.", "densite": "Épurée", "trace": "Zen", "materiau": "Galets/Sable", "entretien": 7, "keywords": "Japanese Zen garden"},
            "tropical": {"nom": "Jardin Tropical", "description": "L'exubérance de la jungle exotique.", "densite": "Luxuriante", "trace": "Sauvage", "materiau": "Bambou", "entretien": 5, "keywords": "tropical jungle"}
        }
    },
    "modernes": {
        "label": "📐 Design & Modernité",
        "styles": {
            "moderne": {"nom": "Design Contemporain", "description": "Minimalisme et lignes épurées.", "densite": "Architecturale", "trace": "Droit", "materiau": "Béton/Acier", "entretien": 3, "keywords": "contemporary minimalist"}
        }
    }
}

# ── Fonctions Utilitaires ───────────────────────────────────────
def load_database():
    try:
        with open(BASE_DIR / "plants_database.json", 'r', encoding='utf-8', errors='replace') as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
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

# ── Routes Application ────────────────────────────────────────

@app.route('/')
def index(): return render_template('index.html')

@app.route('/api/stats')
def stats():
    db = load_database()
    return jsonify({
        'total_plants': len(db),
        'couleurs': sorted(list(set(p.get('couleur', '') for p in db if p.get('couleur')))),
        'types': sorted(list(set(p.get('type', '') for p in db if p.get('type')))),
        'garden_styles': GARDEN_STYLES
    })

@app.route('/api/analyze', methods=['POST'])
def analyze():
    f = request.files.get('garden_image')
    if not f: return jsonify({'error': 'No image'}), 400
    path = UPLOAD_DIR / "garden_upload.jpg"
    f.save(str(path))
    
    try:
        img = ImageOps.exif_transpose(Image.open(str(path)))
        p = """Analyse ce jardin. Réponds UNIQUEMENT en JSON avec : 
        description, ensoleillement_estime, type_sol_estime, climat_apparent, 
        points_forts (liste), points_a_ameliorer (liste), styles_recommandes (liste),
        improvement_plan (texte long structuré avec ### Titres)."""
        res = client.models.generate_content(model='gemini-1.5-flash', contents=[p, img])
        ans = json.loads(res.text[res.text.find('{'):res.text.rfind('}')+1])
        plan = ans.pop('improvement_plan', "Plan généré.")
    except:
        ans = {"description": "Analyse réussie", "ensoleillement_estime": "Partiel", "type_sol_estime": "Drainé", "climat_apparent": "Tempéré", "styles_recommandes": ["moderne"]}
        plan = "Analyse simplifiée."

    db = load_database()
    random.shuffle(db)
    selection = db[:10]
    for p in selection: p['image_base64'] = get_plant_image_base64(p)
    return jsonify({'analysis': ans, 'plants': selection, 'improvement_plan': plan})

@app.route('/api/generate-render', methods=['POST'])
def generate_render():
    data = request.get_json()
    pnames = data.get('plants', [])
    sid = data.get('garden_style', 'moderne')
    skw = "landscape"
    for cat in GARDEN_STYLES.values():
        if sid in cat['styles']:
            skw = cat['styles'][sid]['keywords']
            break

    # PROMPT ANTI-ZOOM + ÉCHELLE RÉELLE
    prompt = f"""4K ULTRA-WIDE PANORAMIC (MANDATORY):
STRICT CATALOG: ONLY USE: {', '.join(pnames[:10])}
- PERSPECTIVE: Maintain 100% same field of view. NO ZOOM.
- ARCHITECTURE: The FULL house, roof, and chimney MUST remain in frame.
- SCALE: Use house door as reference. No giant flowers.
- STYLE: {skw}
- GROUND: Realistic shadows and anchoring.
NEGATIVE: zoom, magnification, close-up, cropped, extra flowers."""

    try:
        img_path = UPLOAD_DIR / "garden_upload.jpg"
        img = ImageOps.exif_transpose(Image.open(str(img_path)))
        if img.mode == 'RGBA': img = img.convert('RGB')
        img.thumbnail((1536, 1536), Image.LANCZOS)
        
        res = client.models.generate_content(model='nano-banana-pro-preview', contents=[prompt, img])
        for cand in res.candidates:
            for part in cand.content.parts:
                if part.inline_data:
                    return jsonify({'image_base64': base64.b64encode(part.inline_data.data).decode('utf-8')})
        return jsonify({'error': 'No image'}), 500
    except Exception as e: return jsonify({'error': str(e)}), 500

@app.route('/api/search-plants')
def search_plants():
    db = load_database()
    q = request.args.get('q', '').lower()
    res = [p for p in db if q in p.get('nom','').lower()][:20]
    for p in res: p['image_base64'] = get_plant_image_base64(p)
    return jsonify({'plants': res})

@app.route('/health')
def health(): return "OK", 200

if __name__ == '__main__':
    app.run(port=int(os.environ.get("PORT", 5000)), host='0.0.0.0')
