"""
🌿 Garden AI Enhancer - Version Intégrale & Réaliste
Contient TOUTES vos fonctionnalités (Recherche, Debug, Analyse) avec le rendu IA boosté.
"""

import json, os, random, base64, io
from pathlib import Path
from flask import Flask, render_template, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename
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
        "label": "🏛️ Styles Classiques & Traditionnels",
        "styles": {
            "francais": {"nom": "Jardin à la française", "keywords": "formal French style, geometric parterre lines, symmetrical topiary"},
            "anglais": {"nom": "Jardin à l'anglaise", "keywords": "English cottage style, herbaceous mixed borders, romantic soft curves"},
            "mediterraneen": {"nom": "Jardin Méditerranéen", "keywords": "Mediterranean landscape, cypress profiles, lavender"}
        }
    },
    "expulsifs": {
        "label": "✨ Ambiances & Atmosphères",
        "styles": {
            "japonais": {"nom": "Jardin Zen / Japonais", "keywords": "Zen Japanese, sculpted maple, mossy textures"},
            "tropical": {"nom": "Jardin Tropical", "keywords": "tropical jungle aesthetic, oversized foliage"}
        }
    },
    "modernes": {
        "label": "📐 Design & Modernité",
        "styles": {"moderne": {"nom": "Design Contemporain", "keywords": "contemporary minimalist design, sharp geometric lines"}}
    }
}

# ── Fonctions Utilitaires ───────────────────────────────────────
def load_database():
    path = BASE_DIR / "plants_database.json"
    try:
        with open(path, 'r', encoding='utf-8', errors='replace') as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except: return []

def get_plant_image_base64(plant):
    try:
        p = plant.get('image_path', '')
        if not p: return None
        path = BASE_DIR / p
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
        'types': sorted(list(set(p.get('type_excel', '') for p in db if p.get('type_excel')))),
        'garden_styles': GARDEN_STYLES
    })

@app.route('/api/analyze', methods=['POST'])
def analyze():
    f = request.files.get('garden_image')
    if not f: return jsonify({'error': 'No image'}), 400
    path = UPLOAD_DIR / "garden_upload.jpg"
    f.save(str(path))
    
    # Analyse IA simplifiée
    try:
        img = ImageOps.exif_transpose(Image.open(str(path)))
        p = "Analyse ce jardin. Réponds UNIQUEMENT en JSON: description, styles_recommandes."
        res = client.models.generate_content(model='gemini-1.5-flash', contents=[p, img])
        ans = json.loads(res.text[res.text.find('{'):res.text.rfind('}')+1])
    except: ans = {"description": "Jardin détecté", "styles_recommandes": ["moderne"]}

    db = load_database()
    random.shuffle(db)
    selection = db[:10]
    for p in selection: p['image_base64'] = get_plant_image_base64(p)
    return jsonify({'analysis': ans, 'plants': selection})

@app.route('/api/generate-render', methods=['POST'])
def generate_render():
    data = request.get_json()
    pnames = data.get('plants', [])
    sid = data.get('garden_style', 'moderne')
    
    skw = "modern landscape"
    for cat in GARDEN_STYLES.values():
        if sid in cat['styles']:
            skw = cat['styles'][sid]['keywords']
            break

    # LE PROMPT MAGIQUE (RÉALISME MAXIMAL)
    prompt = f"""4K PHOTOREALISTIC LANDSCAPE (REALISTIC SCALE): 
STRICT CATALOG: ONLY USE: {', '.join(pnames[:10])}
- SCALE: Use house height as reference. No oversized flowers.
- DEPTH: Distribute plants across the field. No floating.
- PERSPECTIVE: Wide-angle. Keep roof and chimney in frame.
- GROUND: Rooted with realistic contact shadows.
NEGATIVE: oversized plants, giant flowers, zoom, cropped, hallucination."""

    try:
        img_path = UPLOAD_DIR / "garden_upload.jpg"
        img = ImageOps.exif_transpose(Image.open(str(img_path)))
        if img.mode == 'RGBA': img = img.convert('RGB')
        img.thumbnail((1536, 1536), Image.LANCZOS)
        
        res = client.models.generate_content(model='nano-banana-pro-preview', contents=[prompt, img])
        
        for pt in res.parts:
            if pt.inline_data:
                final_img = Image.open(io.BytesIO(pt.inline_data.data))
                out_name = f"render_{random.randint(1000,9999)}.jpg"
                final_img.save(str(UPLOAD_DIR / out_name), quality=95)
                return jsonify({'render_url': f'/uploads/{out_name}'})
        return jsonify({'error': 'No image'}), 500
    except Exception as e: return jsonify({'error': str(e)}), 500

@app.route('/api/search-plants')
def search_plants():
    db = load_database()
    q = request.args.get('q', '').lower()
    results = [p for p in db if q in p.get('nom','').lower()][:20]
    for p in results: p['image_base64'] = get_plant_image_base64(p)
    return jsonify({'plants': results})

@app.route('/uploads/<f>')
def uploads(f): return send_from_directory(str(UPLOAD_DIR), f)

@app.route('/health')
def health(): return "OK", 200

@app.route('/api/debug-files')
def debug_files():
    fichiers = os.listdir(BASE_DIR)
    return jsonify({'dossier': str(BASE_DIR), 'fichiers': fichiers, 'db': 'plants_database.json' in fichiers})

if __name__ == '__main__':
    app.run(port=int(os.environ.get("PORT", 5000)), host='0.0.0.0')
