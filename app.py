"""
🌿 Garden AI Enhancer - Version 100% Moderne (Render Ready)
Application Flask utilisant le nouveau SDK Google GenAI v1
"""

import json
import os
import random
import base64
import io
from pathlib import Path
from flask import Flask, render_template, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
from google import genai
from google.genai import types as genai_types
from PIL import Image, ImageOps

# ── Configuration & Sécurité ───────────────────────────────────
load_dotenv()
API_KEY = os.getenv('GEMINI_API_KEY')

# Initialisation du client unique (le cerveau de l'app)
client = genai.Client(api_key=API_KEY)

BASE_DIR = Path(__file__).resolve().parent
DB_FILE = Path(os.path.join(os.path.dirname(__file__), 'plants_database.json'))
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

app = Flask(__name__, static_folder='static', template_folder='templates')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

# ── Styles de jardin ──────────────────────────────────────────
GARDEN_STYLES = {
    "traditionnels": {
        "label": "🏛️ Styles Classiques & Traditionnels",
        "styles": {
            "francais": {
                "nom": "Jardin à la française",
                "keywords": "formal French style, geometric parterre lines, symmetrical topiary, needle-sharp hedge cutting"
            },
            "anglais": {
                "nom": "Jardin à l'anglaise",
                "keywords": "English cottage style, herbaceous mixed borders, romantic soft flowing curves"
            },
            "mediterraneen": {
                "nom": "Jardin Méditerranéen",
                "keywords": "Mediterranean landscape, silver-grey foliage, Italian cypress profiles, lavender, terracotta"
            }
        }
    },
    "expulsifs": {
        "label": "✨ Ambiances & Atmosphères",
        "styles": {
            "japonais": {
                "nom": "Jardin Zen / Japonais",
                "keywords": "Zen Japanese, sculpted maple, mossy textures, stepping stones, minimalist harmony"
            },
            "tropical": {
                "nom": "Jardin Tropical",
                "keywords": "tropical jungle aesthetic, oversized foliage, exotic bold leaf textures, vibrant colors"
            }
        }
    },
    "modernes": {
        "label": "📐 Design & Modernité",
        "styles": {
            "moderne": {
                "nom": "Design Contemporain",
                "keywords": "contemporary minimalist design, sharp geometric lines, architectural plant shapes"
            }
        }
    }
}

# ── Fonctions Utilitaires ───────────────────────────────────────
def load_database():
    try:
        if not DB_FILE.exists(): return []
        with open(DB_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except: return []

def get_plant_image_base64(plant):
    try:
        p = plant.get('image_path', '')
        if not p: return None
        # On cherche l'image dans le dossier de l'app ou static
        path = BASE_DIR / p
        if not path.exists(): return None
        with Image.open(path) as img:
            img.thumbnail((300, 300), Image.LANCZOS)
            buf = io.BytesIO()
            img.save(buf, format='PNG')
            return base64.b64encode(buf.getvalue()).decode('utf-8')
    except: return None

# ── Logique IA (Version Moderne client.models) ──────────────────

def analyze_garden_image(image_path, user_location, user_soil, user_style):
    try:
        img = ImageOps.exif_transpose(Image.open(image_path))
        ctx = f"Localisation: {user_location}, Sol: {user_soil}, Style: {user_style or 'Libre'}"
        prompt = f"Analyse cette photo de jardin. {ctx}. Réponds UNIQUEMENT en JSON avec : description, points_forts, points_a_ameliorer, styles_recommandes."
        
        response = client.models.generate_content(
            model='gemini-1.5-flash',
            contents=[prompt, img]
        )
        
        text = response.text.strip()
        idx, end = text.find('{'), text.rfind('}')
        return json.loads(text[idx:end+1])
    except Exception as e:
        print(f"Erreur analyse: {e}")
        return {"description": "Analyse simplifiée", "styles_recommandes": ["moderne"]}

def select_plants_for_garden(analysis, max_plants=10):
    db = load_database()
    if not db: return []
    random.shuffle(db)
    selection = db[:max_plants]
    for p in selection:
        p['image_base64'] = get_plant_image_base64(p)
    return selection

# ── Routes Application ────────────────────────────────────────

@app.route('/')
def index(): return render_template('index.html')

@app.route('/api/stats')
def stats():
    db = load_database()
    couleurs = sorted(list(set(p.get('couleur', '') for p in db if p.get('couleur'))))
    types = sorted(list(set(p.get('type_excel', '') for p in db if p.get('type_excel'))))
    return jsonify({
        'total_plants': len(db),
        'couleurs': couleurs,
        'types': types,
        'garden_styles': GARDEN_STYLES
    })

@app.route('/api/analyze', methods=['POST'])
def analyze():
    f = request.files.get('garden_image')
    if not f: return jsonify({'error': 'No image'}), 400
    path = UPLOAD_DIR / "garden_upload.jpg"
    f.save(str(path))
    ans = analyze_garden_image(str(path), "", "", "")
    pts = select_plants_for_garden(ans)
    return jsonify({'analysis': ans, 'plants': pts})

@app.route('/api/generate-render', methods=['POST'])
def generate_render():
    data = request.get_json()
    pnames = data.get('plants', [])
    sid = data.get('garden_style', 'moderne')
    
    # Récupération style
    skw = "modern landscape"
    for cat in GARDEN_STYLES.values():
        if sid in cat['styles']:
            skw = cat['styles'][sid]['keywords']
            break

    prompt = f"""4K WIDE-ANGLE LANDSCAPE OVERLAY:
STRICT CATALOG ENFORCEMENT: ONLY USE: {', '.join(pnames[:10])}
- PERSPECTIVE LOCK: Maintain original wide-angle view. No zoom.
- LANDMARK: The chimney and roof corners must stay inside the frame.
- STYLE: {skw}
- GROUND ANCHORING: Realistic shadows and ground integration.
NEGATIVE: zoom, magnification, close-up, cropped, extra flowers, hallucination."""

    try:
        path = UPLOAD_DIR / "garden_upload.jpg"
        img = ImageOps.exif_transpose(Image.open(str(path)))
        if img.mode == 'RGBA': img = img.convert('RGB')
        img.thumbnail((1536, 1536), Image.LANCZOS)
        
        # Le fameux "Nano-Banana" pour le rendu
        res = client.models.generate_content(
            model='nano-banana-pro-preview',
            contents=[prompt, img],
            config=genai_types.GenerateContentConfig()
        )
        
        for pt in res.parts:
            if pt.inline_data:
                final_img = Image.open(io.BytesIO(pt.inline_data.data))
                out_name = f"render_{random.randint(1000,9999)}.jpg"
                final_img.save(str(UPLOAD_DIR / out_name), quality=95)
                return jsonify({'render_url': f'/uploads/{out_name}'})
                
        return jsonify({'error': 'No image returned'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/search-plants')
def search_plants():
    db = load_database()
    q = request.args.get('q', '').lower()
    results = [p for p in db if q in p.get('nom','').lower()][:20]
    for p in results: p['image_base64'] = get_plant_image_base64(p)
    return jsonify({'plants': results})

@app.route('/uploads/<f>')
def uploads(f): return send_from_directory(str(UPLOAD_DIR), f)

# Route de santé pour Render
@app.route('/santé')
@app.route('/health')
def health(): return "OK", 200

if __name__ == '__main__':
    app.run(debug=True, port=int(os.environ.get("PORT", 5000)), host='0.0.0.0')
