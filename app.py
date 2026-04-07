"""
🌿 Garden AI Enhancer - Application Flask
Analyse une photo de jardin et propose des améliorations
avec uniquement les plantes de la base de données locale.
"""

import json
import os
import random
import base64
import traceback
import logging
from pathlib import Path
from flask import Flask, render_template, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
import google.generativeai as genai
from PIL import Image, ImageFilter, ImageDraw, ImageOps
import io

# Import pour la génération d'images (Imagen)
try:
    from google import genai as genai_client
    from google.genai import types as genai_types
    IMAGEN_AVAILABLE = True
except ImportError:
    IMAGEN_AVAILABLE = False
    print("⚠️  google-genai non installé. pip install google-genai pour la génération d'images.")

# ── Configuration ──────────────────────────────────────────────
load_dotenv()
API_KEY = os.getenv('GEMINI_API_KEY')
if not API_KEY:
    print("⚠️  ATTENTION : Clé API Gemini manquante dans .env")

genai.configure(api_key=API_KEY)

# Essayer plusieurs noms de modèle
MODEL_NAMES = ['gemini-2.5-flash', 'gemini-1.5-flash']
model = None
for model_name in MODEL_NAMES:
    try:
        model = genai.GenerativeModel(model_name)
        print(f"✅ Modèle texte : {model_name}")
        break
    except Exception:
        continue

if model is None:
    model = genai.GenerativeModel('gemini-1.5-flash')

# Client pour Imagen (génération d'images)
if IMAGEN_AVAILABLE and API_KEY:
    imagen_client = genai_client.Client(api_key=API_KEY)
else:
    imagen_client = None

BASE_DIR = Path(__file__).resolve().parent
DB_FILE = BASE_DIR / "output" / "plants_database.json"
PHOTOS_DIR = BASE_DIR.parent / "all_photos"
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
                "description": "Symmetry, topiaires, parterres géométriques, élégance classique",
                "densite": "Faible",
                "trace": "Géométrique",
                "entretien": 10,
                "materiau": "Bordure / Alignement",
                "keywords": "formal French style, geometric parterre lines, symmetrical topiary, needle-sharp hedge cutting"
            },
            "anglais": {
                "nom": "Jardin à l'anglaise",
                "description": "Bordures mixtes, romantisme, courbes douces, floraison vaporeuse",
                "densite": "Haute",
                "trace": "Courbe",
                "entretien": 6,
                "materiau": "Gazon / Mixed-border",
                "keywords": "English cottage style, herbaceous mixed borders, romantic soft flowing curves, misty flowering clusters"
            },
            "mediterraneen": {
                "nom": "Jardin Méditerranéen",
                "description": "Oliviers, lavandes, cyprès, pots en terre cuite, harmonie solaire",
                "densite": "Modérée",
                "trace": "Libre",
                "entretien": 4,
                "materiau": "Bois / Terre Cuite",
                "keywords": "Mediterranean landscape, silver-grey foliage, Italian cypress silhouettes, lavender clusters, terracotta pots"
            }
        }
    },
    "expulsifs": {
        "label": "✨ Ambiances & Atmosphères",
        "styles": {
            "japonais": {
                "nom": "Jardin Zen / Japonais",
                "description": "Érables, mousses, asymétrie maîtrisée, équilibre et sérénité",
                "densite": "Basse",
                "trace": "Précis",
                "entretien": 8,
                "materiau": "Pas japonais / Lanterne",
                "keywords": "Zen Japanese style, sculpted maple silhouettes, asymmetrical balance, mossy textures, stepping stones"
            },
            "tropical": {
                "nom": "Jardin Tropical / Exotique",
                "description": "Feuillage géant, bananiers, couleurs saturées, jungle ordonnée",
                "densite": "Très haute",
                "trace": "Organique",
                "entretien": 6,
                "materiau": "Bois exotique",
                "keywords": "tropical jungle aesthetic, oversized foliage, exotic bold leaf textures, vibrant saturated colors"
            },
            "sauvage": {
                "nom": "Jardin Naturel / Prairie",
                "description": "Prairie fleurie, biodiversité, laisser-faire maîtrisé",
                "densite": "Haute",
                "trace": "Naturaliste",
                "entretien": 2,
                "materiau": "Bois brut / Paillage",
                "keywords": "wildlife-friendly natural garden, meadow aesthetic, organic chaotic beauty, ecological layering"
            }
        }
    },
    "modernes": {
        "label": "📐 Design & Modernité",
        "styles": {
            "moderne": {
                "nom": "Design Contemporain",
                "description": "Lignes épurées, contrastes de textures, minimalisme chic",
                "densite": "Basse",
                "trace": "Géométrique",
                "entretien": 5,
                "materiau": "Métal / Ardoise / Béton",
                "keywords": "contemporary minimalist design, sharp geometric lines, monochromatic foliage, architectural plant shapes"
            },
            "ville": {
                "nom": "Jardin de Ville / Patio",
                "description": "Optimisation verticale, bacs sur mesure, chic urbain",
                "densite": "Modérée",
                "trace": "Compact",
                "entretien": 5,
                "materiau": "Bac / Métal",
                "keywords": "urban patio garden, vertical planting beds, container gardening, integrated terrace lighting"
            }
        }
    },
    "techniques": {
        "label": "📐 Styles Techniques",
        "styles": {
            "rocaille": {
                "nom": "Jardin de Rocaille / Alpin",
                "description": "Terrain pentu, roches, plantes de basse stature, drainage",
                "densite": "Modérée",
                "trace": "Organique",
                "entretien": 3,
                "materiau": "Pierre naturelle",
                "keywords": "rock garden, alpine plants, stone, low-growing, well-drained, mountain plants"
            },
            "sec": {
                "nom": "Jardin Sec (Xéropaysagisme)",
                "description": "Zéro arrosage, paillis minéral, pas de gazon, plantes xérophiles",
                "densite": "Faible",
                "trace": "Libre",
                "entretien": 2,
                "materiau": "Paillis minéral",
                "keywords": "xeriscaping, dry garden, gravel mulch, drought-resistant, succulents, no lawn"
            }
        }
    }
}

# ── Fonctions Utilitaires ───────────────────────────────────────
def load_database():
    try:
        if not DB_FILE.exists(): return []
        with open(DB_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        valid = []
        for p in data:
            path = p.get('image_path', 'unknown')
            if path and path != 'unknown':
                res = (BASE_DIR / path).resolve()
                if res.exists():
                    p['_resolved_image'] = str(res)
                    valid.append(p)
        return valid
    except: return []

def get_plant_image_base64(plant):
    try:
        p = plant.get('_resolved_image', '')
        if not p or not Path(p).exists(): return None
        with Image.open(p) as img:
            img.thumbnail((400, 400), Image.LANCZOS)
            buf = io.BytesIO()
            img.save(buf, format='PNG')
            return base64.b64encode(buf.getvalue()).decode('utf-8')
    except: return None

# ── Logique Métier ──────────────────────────────────────────────
def analyze_garden_image(image_path, user_location, user_soil, user_style):
    try:
        img = ImageOps.exif_transpose(Image.open(image_path))
        ctx = f"Localisation: {user_location}\nSol: {user_soil}\nStyle désiré: {user_style or 'Libre'}\n"
        prompt = f"Expert paysagiste. Analyse cette photo.\n{ctx}\nRéponds UNIQUEMENT en JSON:\n{{\"description\":\"\",\"points_forts\":[],\"points_a_ameliorer\":[],\"ensoleillement_estime\":\"\",\"type_sol_estime\":\"\",\"climat_apparent\":\"\",\"styles_recommandes\":[],\"zones_plantation\":[{{\"zone\":\"\",\"description\":\"\",\"type_plante_ideal\":\"\"}}]}}"
        res = model.generate_content([prompt, img])
        text = res.text.strip()
        idx = text.find('{')
        end = text.rfind('}')
        return json.loads(text[idx:end+1])
    except Exception as e:
        print(f"Erreur analyse: {e}")
        return {"description":"Analyse simplifiée","points_forts":[], "points_a_ameliorer":[], "ensoleillement_estime":"unknown", "styles_recommandes":[], "zones_plantation":[]}

def select_plants_for_garden(analysis, max_plants=12, user_budget="moyen", user_maintenance="modere"):
    db = load_database()
    if not db: return []
    styles = analysis.get('styles_recommandes', [])
    search = " ".join(styles).lower()
    pool = []
    for p in db:
        score = 0
        txt = f"{p.get('nom','')} {p.get('type_excel','')} {p.get('sous_type_excel','')} {p.get('entretien','')}".lower()
        if any(kw in txt for kw in search.split()): score += 10
        if score > 0 or random.random() < 0.02:
            p_copy = p.copy()
            p_copy['score'] = score
            pool.append(p_copy)
    pool.sort(key=lambda x: x.get('score', 0), reverse=True)
    sel = pool[:max_plants]
    for p in sel:
        p['raison_selection'] = "Adapté au style"
        p['emplacement_suggere'] = "Zone ensoleillée"
        p['image_base64'] = get_plant_image_base64(p)
    return sel

def generate_improvement_plan(analysis, plants):
    names = [p.get('nom', '?') for p in plants]
    prompt = f"Plan d'amélioration pour ce jardin avec: {names}. Sois enthousiaste."
    try: return model.generate_content(prompt).text
    except: return "Plan indisponible."

# ── Routes ────────────────────────────────────────────────────
@app.route('/')
def index(): return render_template('index.html')

@app.route('/api/analyze', methods=['POST'])
def analyze():
    f = request.files.get('garden_image')
    if not f: return jsonify({'error': 'No image'}), 400
    path = UPLOAD_DIR / "garden_upload.jpg"
    f.save(str(path))
    loc = request.form.get('user_location','')
    soil = request.form.get('user_soil','unknown')
    style = request.form.get('user_style')
    ans = analyze_garden_image(str(path), loc, soil, style)
    pts = select_plants_for_garden(ans)
    plan = generate_improvement_plan(ans, pts)
    return jsonify({'analysis': ans, 'plants': pts, 'improvement_plan': plan})

@app.route('/api/stats')
def stats():
    db = load_database()
    # Extraire les valeurs uniques pour les filtres
    couleurs = sorted(list(set(p.get('couleur', '') for p in db if p.get('couleur'))))
    types = sorted(list(set(p.get('type_excel', p.get('type', '')) for p in db if p.get('type_excel', p.get('type')))))
    sous_types = sorted(list(set(p.get('sous_type_excel', p.get('sous_type', '')) for p in db if p.get('sous_type_excel', p.get('sous_type')))))
    
    return jsonify({
        'total_plants': len(db),
        'couleurs': couleurs,
        'types': types,
        'sous_types': sous_types,
        'garden_styles': GARDEN_STYLES
    })

@app.route('/api/search-plants')
def search_plants():
    q = request.args.get('q', '').lower()
    color = request.args.get('color', '').lower()
    ptype = request.args.get('type', '').lower()
    stype = request.args.get('sous_type', '').lower()
    
    db = load_database()
    results = []
    
    for p in db:
        # Match filters
        if color and color != p.get('couleur', '').lower(): continue
        if ptype and ptype != p.get('type_excel', p.get('type', '')).lower(): continue
        if stype and stype != p.get('sous_type_excel', p.get('sous_type', '')).lower(): continue
        
        # Match query
        search_blob = f"{p.get('nom', '')} {p.get('nom_vernaculaire', '')} {p.get('descr_generale', '')}".lower()
        if q and q not in search_blob: continue
        
        # Prepare for frontend
        p_copy = p.copy()
        p_copy['image_base64'] = get_plant_image_base64(p)
        results.append(p_copy)
        
    # Limit results for performance
    return jsonify({
        'plants': results[:50],
        'total': len(results)
    })

@app.route('/api/generate-render', methods=['POST'])
def generate_render():
    data = request.get_json()
    pnames = data.get('plants', [])
    sid = data.get('garden_style', '')
    
    # Récupérer keywords style
    skw = ""
    sname = sid
    for cat in GARDEN_STYLES.values():
        if sid in cat['styles']:
            skw = cat['styles'][sid]['keywords']
            sname = cat['styles'][sid]['nom']
            break

    prompt = f"""4K WIDE-ANGLE LANDSCAPE OVERLAY (STRICT CATALOG):
STRICT CATALOG ENFORCEMENT: YOU MUST ONLY USE these plants: {', '.join(pnames[:10])}
- NO EXTRA VEGETATION: Do not add any plants, flowers, or trees NOT in the list above.
- PERSPECTIVE LOCK: Maintain 100% of the original wide-angle view. Do not zoom.
- LANDMARK PRESERVATION: The ROOF TOP, CHIMNEY, and HOUSE CORNERS must stay visible in the frame.
- GROUND ANCHORING: Root all plants well into the ground with realistic shadows and seamless integration.
- STYLE: {sname} ({skw})
- NO DELETION: Add new plants without removing original elements.
NEGATIVE: extra plants, hallucinated flowers, random trees, zoom, magnification, close-up, cropped edges, cut chimney, cut roof."""

    try:
        path = UPLOAD_DIR / "garden_upload.jpg"
        if not path.exists(): return jsonify({'error': 'No source'}), 404
        
        img = ImageOps.exif_transpose(Image.open(str(path)))
        if img.mode == 'RGBA': img = img.convert('RGB')
        
        img = ImageOps.exif_transpose(Image.open(str(path)))
        if img.mode == 'RGBA': img = img.convert('RGB')
        
        # 1. Redimensionner sans déformer (Ratio original préservé)
        max_d = 1536
        img.thumbnail((max_d, max_d), Image.LANCZOS)
        
        # 2. Appel IA Direct (Format Panoramique Naturel)
        if imagen_client:
            res = imagen_client.models.generate_content(
                model='nano-banana-pro-preview',
                contents=[prompt, img],
                config=genai_types.GenerateContentConfig()
            )
        else:
            res = model.generate_content([prompt, img])
            
        final_img = None
        for pt in res.parts:
            if pt.inline_data:
                final_img = Image.open(io.BytesIO(pt.inline_data.data))
                break
        
        if not final_img: return jsonify({'error': 'No image returned'}), 500
        
        # --- SAUVEGARDE ET QUALITÉ ---
        out_name = f"render_{random.randint(1000,9999)}.jpg"
        final_img.save(str(UPLOAD_DIR / out_name), quality=95)
        
        img_buffer = io.BytesIO()
        final_img.save(img_buffer, format='JPEG')
        return jsonify({'render_url': f'/uploads/{out_name}', 'image_base64': base64.b64encode(img_buffer.getvalue()).decode()})
        
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/uploads/<f>')
def uploads(f): return send_from_directory(str(UPLOAD_DIR), f)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
