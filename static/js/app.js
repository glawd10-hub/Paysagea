/**
 * 🌿 my garden Designer - Frontend Logic
 * with plant toggle checkboxes and garden style selector
 */

document.addEventListener('DOMContentLoaded', () => {
    const uploadArea = document.getElementById('upload-area');
    const fileInput = document.getElementById('file-input');
    const previewContainer = document.getElementById('preview-container');
    const previewImage = document.getElementById('preview-image');
    const analyzeSection = document.getElementById('analyze-section');
    const analyzeBtn = document.getElementById('analyze-btn');
    const loadingOverlay = document.getElementById('loading-overlay');
    const resultsSection = document.getElementById('results-section');
    const errorMessage = document.getElementById('error-message');
    const heroSection = document.getElementById('hero-section');

    let selectedFile = null;
    let currentAnalysis = null;
    let currentPlants = [];
    let addedPlants = [];
    let removedPlantIds = new Set();
    // Track which plants are "checked" (enabled) by id
    let checkedPlantIds = new Set();
    // Track selected garden style
    let selectedGardenStyle = '';

    loadStats();

    // ── Upload ──
    uploadArea.addEventListener('click', () => fileInput.click());
    uploadArea.addEventListener('dragover', e => { e.preventDefault(); uploadArea.classList.add('dragover'); });
    uploadArea.addEventListener('dragleave', () => uploadArea.classList.remove('dragover'));
    uploadArea.addEventListener('drop', e => {
        e.preventDefault();
        uploadArea.classList.remove('dragover');
        if (e.dataTransfer.files.length > 0 && e.dataTransfer.files[0].type.startsWith('image/'))
            handleFile(e.dataTransfer.files[0]);
    });
    fileInput.addEventListener('change', e => { if (e.target.files.length > 0) handleFile(e.target.files[0]); });

    function handleFile(file) {
        selectedFile = file;
        const reader = new FileReader();
        reader.onload = e => {
            previewImage.src = e.target.result;
            previewContainer.classList.add('visible');
            document.getElementById('pre-style-section').style.display = 'block';
            analyzeSection.classList.add('visible');
        };
        reader.readAsDataURL(file);
    }

    window.removePreview = function () {
        selectedFile = null;
        previewContainer.classList.remove('visible');
        document.getElementById('pre-style-section').style.display = 'none';
        analyzeSection.classList.remove('visible');
        previewImage.src = '';
        fileInput.value = '';
    };

    // ── Analyze ──
    analyzeBtn.addEventListener('click', async () => {
        if (!selectedFile) return;
        loadingOverlay.classList.add('visible');
        resultsSection.classList.remove('visible');
        errorMessage.classList.remove('visible');
        analyzeBtn.disabled = true;
        removedPlantIds.clear();
        addedPlants = [];
        checkedPlantIds.clear();
        animateLoadingSteps();

        const formData = new FormData();
        formData.append('garden_image', selectedFile);
        formData.append('user_location', document.getElementById('user-location').value);
        formData.append('user_soil', document.getElementById('user-soil').value);
        formData.append('user_budget', document.getElementById('user-budget').value);
        formData.append('user_maintenance', document.getElementById('user-maintenance').value);
        if (selectedGardenStyle) {
            formData.append('user_style', selectedGardenStyle);
        }

        try {
            const response = await fetch('/api/analyze', { method: 'POST', body: formData });
            const data = await response.json();
            if (!response.ok) throw new Error(data.error || 'Erreur lors de l\'analyse');
            currentAnalysis = data.analysis;
            currentPlants = data.plants;
            // All plants checked by default
            currentPlants.forEach(p => checkedPlantIds.add(String(p.id)));
            renderResults(data);
        } catch (err) {
            console.error('Error:', err);
            errorMessage.querySelector('.error-text').textContent = err.message;
            errorMessage.classList.add('visible');
        } finally {
            loadingOverlay.classList.remove('visible');
            analyzeBtn.disabled = false;
        }
    });

    function animateLoadingSteps() {
        const steps = document.querySelectorAll('.loading-step');
        steps.forEach(s => { s.classList.remove('active', 'done'); s.querySelector('.loading-step-icon').textContent = '◉'; });
        [0, 3000, 8000, 15000].forEach((time, i) => {
            setTimeout(() => {
                if (i > 0 && steps[i - 1]) { steps[i - 1].classList.remove('active'); steps[i - 1].classList.add('done'); steps[i - 1].querySelector('.loading-step-icon').textContent = '✓'; }
                if (steps[i]) steps[i].classList.add('active');
            }, time);
        });
    }

    // ── Render Results ──
    function renderResults(data) {
        const { analysis, plants, improvement_plan } = data;
        document.getElementById('analysis-content').innerHTML = buildSimplifiedAnalysis(analysis);
        renderPlantsGrid();
        document.getElementById('plan-content').innerHTML = formatPlan(improvement_plan);
        const renderSection = document.getElementById('render-section');
        renderSection.classList.remove('visible');
        document.getElementById('render-result').innerHTML = '';
        resultsSection.classList.add('visible');
        setTimeout(() => resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' }), 300);
    }

    // ── Simplified Analysis Display ──
    function buildSimplifiedAnalysis(analysis) {
        const sun = analysis.ensoleillement_estime || 'N/A';
        const soil = analysis.type_sol_estime || 'N/A';
        const climate = analysis.climat_apparent || 'N/A';
        const desc = analysis.description || '';
        const styles = (analysis.styles_recommandes || []).map(s => `<span class="tag style">🎨 ${s}</span>`).join('');
        const strengths = (analysis.points_forts || []).slice(0, 3).map(p => `<span class="tag positive">✓ ${p}</span>`).join('');
        const improve = (analysis.points_a_ameliorer || []).slice(0, 3).map(p => `<span class="tag improve">⚡ ${p}</span>`).join('');

        return `
            <div class="analysis-summary">
                <p class="analysis-desc">${desc}</p>
                <div class="analysis-chips">
                    <div class="chip">☀️ ${sun}</div>
                    <div class="chip">🌍 ${soil}</div>
                    <div class="chip">🌡️ ${climate}</div>
                </div>
                ${strengths || improve ? `<div class="analysis-tags">${strengths}${improve}</div>` : ''}
                ${styles ? `<div class="analysis-tags" style="margin-top:0.5rem;">${styles}</div>` : ''}
            </div>
        `;
    }

    // ── Plants Grid ──
    function getAllActivePlants() {
        const fromAnalysis = currentPlants.filter(p => !removedPlantIds.has(String(p.id)));
        return [...fromAnalysis, ...addedPlants];
    }

    function getCheckedPlants() {
        return getAllActivePlants().filter(p => checkedPlantIds.has(String(p.id)));
    }

    function renderPlantsGrid() {
        const activePlants = getAllActivePlants();
        const html = activePlants.map((p, i) => buildPlantCard(p, i < currentPlants.length)).join('');
        document.getElementById('plants-grid').innerHTML = html;
        const checkedCount = getCheckedPlants().length;
        updatePlantCount(activePlants.length, checkedCount);
        updateGenerateBtn(checkedCount);
    }

    function updatePlantCount(total, checked) {
        const el = document.getElementById('plant-count');
        if (el) el.textContent = `${checked}/${total} plante${checked !== 1 ? 's' : ''} cochée${checked !== 1 ? 's' : ''}`;
    }

    function updateGenerateBtn(count) {
        const btn = document.getElementById('generate-render-btn');
        if (btn) btn.disabled = count === 0;
    }

    // ── Toggle plant checkbox ──
    window.togglePlant = function (plantId) {
        const id = String(plantId);
        if (checkedPlantIds.has(id)) {
            checkedPlantIds.delete(id);
        } else {
            checkedPlantIds.add(id);
        }
        // Update just the visual state without full re-render
        const card = document.getElementById(`plant-card-${plantId}`);
        if (card) {
            const checkbox = card.querySelector('.plant-checkbox');
            const isChecked = checkedPlantIds.has(id);
            if (checkbox) {
                checkbox.classList.toggle('checked', isChecked);
                checkbox.innerHTML = isChecked ? '✓' : '';
            }
            card.classList.toggle('unchecked', !isChecked);
        }
        const allActive = getAllActivePlants();
        const checkedCount = getCheckedPlants().length;
        updatePlantCount(allActive.length, checkedCount);
        updateGenerateBtn(checkedCount);
    };

    // ── Select / Deselect All ──
    window.selectAllPlants = function () {
        getAllActivePlants().forEach(p => checkedPlantIds.add(String(p.id)));
        renderPlantsGrid();
    };

    window.deselectAllPlants = function () {
        checkedPlantIds.clear();
        renderPlantsGrid();
    };

    window.removePlant = function (plantId) {
        const card = document.getElementById(`plant-card-${plantId}`);
        if (card) {
            card.style.transform = 'scale(0.8)';
            card.style.opacity = '0';
            setTimeout(() => {
                const addedIdx = addedPlants.findIndex(p => String(p.id) === String(plantId));
                if (addedIdx >= 0) {
                    addedPlants.splice(addedIdx, 1);
                } else {
                    removedPlantIds.add(String(plantId));
                }
                checkedPlantIds.delete(String(plantId));
                renderPlantsGrid();
            }, 300);
        }
    };

    window.restorePlants = function () {
        removedPlantIds.clear();
        addedPlants = [];
        checkedPlantIds.clear();
        currentPlants.forEach(p => checkedPlantIds.add(String(p.id)));
        renderPlantsGrid();
    };

    // ── Add Plant from search ──
    window.addPlantToSelection = function (plantData) {
        const allActive = getAllActivePlants();
        if (allActive.some(p => String(p.id) === String(plantData.id))) {
            alert('Cette plante est déjà dans votre sélection !');
            return;
        }
        addedPlants.push({ ...plantData, raison: 'Ajoutée manuellement', emplacement: '' });
        checkedPlantIds.add(String(plantData.id));
        renderPlantsGrid();
        document.getElementById('plants-grid').scrollIntoView({ behavior: 'smooth', block: 'center' });
    };

    // ── Generate Render ──
    window.generateRender = async function () {
        const checkedPlants = getCheckedPlants();
        const plantNames = checkedPlants.map(p => p.nom);
        if (plantNames.length === 0) {
            alert('Veuillez cocher au moins une plante.');
            return;
        }

        const renderSection = document.getElementById('render-section');
        const renderResult = document.getElementById('render-result');
        const renderBtn = document.getElementById('generate-render-btn');
        const renderLoading = document.getElementById('render-loading');
        const suggestionsEl = document.getElementById('user-suggestions');
        const userSuggestions = suggestionsEl ? suggestionsEl.value.trim() : '';

        renderBtn.disabled = true;
        renderLoading.classList.add('visible');
        renderSection.classList.add('visible');
        renderResult.innerHTML = '';
        renderSection.scrollIntoView({ behavior: 'smooth', block: 'start' });

        try {
            const response = await fetch('/api/generate-render', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    analysis: currentAnalysis,
                    plants: plantNames,
                    user_suggestions: userSuggestions,
                    garden_style: selectedGardenStyle
                })
            });
            const data = await response.json();
            if (!response.ok) throw new Error(data.error || 'Erreur lors de la génération');

            renderResult.innerHTML = `
                <div class="render-image-wrapper">
                    <img class="render-image" src="data:image/jpeg;base64,${data.image_base64}" alt="Rendu du jardin">
                </div>
                <div class="render-actions">
                    <button class="render-download-btn" onclick="downloadRender()"><span>💾</span> Télécharger</button>
                    <button class="new-analysis-btn" onclick="generateRender()"><span>🔄</span> Regénérer</button>
                </div>
            `;
            window._lastRenderBase64 = data.image_base64;
        } catch (err) {
            console.error('Render error:', err);
            renderResult.innerHTML = `
                <div class="render-error">
                    <span class="error-icon">⚠️</span>
                    <p>${err.message}</p>
                    <button class="new-analysis-btn" onclick="generateRender()" style="margin-top: 1rem;"><span>🔄</span> Réessayer</button>
                </div>
            `;
        } finally {
            renderBtn.disabled = false;
            renderLoading.classList.remove('visible');
        }
    };

    window.downloadRender = function () {
        if (!window._lastRenderBase64) return;
        const link = document.createElement('a');
        link.href = 'data:image/jpeg;base64,' + window._lastRenderBase64;
        link.download = 'jardin_ameliore.jpg';
        link.click();
    };

    // ── Search Panel ──
    window.toggleSearchPanel = function () {
        const panel = document.getElementById('search-panel');
        panel.classList.toggle('visible');
        if (panel.classList.contains('visible')) {
            panel.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
    };

    window.searchPlants = async function () {
        const q = document.getElementById('search-query').value;
        const color = document.getElementById('filter-color').value;
        const type = document.getElementById('filter-type').value;
        const sous_type = document.getElementById('filter-sous-type').value;
        const resultsDiv = document.getElementById('search-results');
        resultsDiv.innerHTML = '<p class="search-hint">🔄 Recherche en cours...</p>';

        const params = new URLSearchParams();
        if (q) params.set('q', q);
        if (color) params.set('color', color);
        if (type) params.set('type', type);
        if (sous_type) params.set('sous_type', sous_type);

        try {
            const response = await fetch(`/api/search-plants?${params.toString()}`);
            const data = await response.json();
            if (data.plants.length === 0) {
                resultsDiv.innerHTML = '<p class="search-hint">Aucune plante trouvée avec ces critères.</p>';
                return;
            }

            // Mise en cache pour éviter les problèmes d'évasion JSON dans les attributs HTML
            window._searchCache = window._searchCache || {};
            data.plants.forEach(p => { window._searchCache[p.id] = p; });

            resultsDiv.innerHTML = `
                <p class="search-count">${data.total} résultat${data.total > 1 ? 's' : ''}</p>
                <div class="search-results-grid">
                    ${data.plants.map(p => buildSearchResultCard(p)).join('')}
                </div>
            `;
        } catch (err) {
            resultsDiv.innerHTML = `<p class="search-hint">Erreur: ${err.message}</p>`;
        }
    };

    document.getElementById('search-query')?.addEventListener('keypress', e => {
        if (e.key === 'Enter') searchPlants();
    });

    function buildSearchResultCard(plant) {
        const img = plant.image_base64
            ? `<img src="data:image/png;base64,${plant.image_base64}" alt="${plant.nom}">`
            : `<div class="search-img-placeholder">🌱</div>`;
        const displayNomResult = plant.nom_vernaculaire && plant.nom_vernaculaire !== 'nan' && plant.nom_vernaculaire !== 'unknown' 
            ? `${plant.nom_vernaculaire} <span style="font-size:0.85em; opacity:0.75;">(${plant.nom})</span>` 
            : plant.nom;
        
        return `
            <div class="search-result-card">
                <div class="search-result-img">${img}</div>
                <div class="search-result-info">
                    <div class="search-result-name">${displayNomResult}</div>
                    <div class="search-result-meta">
                        <span>🎨 ${plant.couleur || 'N/A'}</span>
                        <span>📁 ${plant.sous_type || plant.type || 'N/A'}</span>
                    </div>
                </div>
                <button class="search-add-btn" onclick="addPlantFromCache('${plant.id}')">
                    + Ajouter
                </button>
            </div>
        `;
    }

    window.addPlantFromCache = function(id) {
        if (window._searchCache && window._searchCache[id]) {
            addPlantToSelection(window._searchCache[id]);
        }
    };

    function buildPlantCard(plant, isFromAnalysis) {
        const imageHTML = plant.image_base64
            ? `<img class="plant-image" src="data:image/png;base64,${plant.image_base64}" alt="${plant.nom}" loading="lazy">`
            : `<div class="plant-image-placeholder">🌱</div>`;

        const waterLevel = getWaterLevel(plant.besoin_eau);
        const badge = isFromAnalysis ? (plant.sous_type || plant.type || 'Plante') : '➕ Ajoutée';
        const badgeClass = isFromAnalysis ? '' : ' added-badge';
        const isChecked = checkedPlantIds.has(String(plant.id));
        const uncheckedClass = isChecked ? '' : ' unchecked';
        
        const displayNom = plant.nom_vernaculaire && plant.nom_vernaculaire !== 'nan' && plant.nom_vernaculaire !== 'unknown' 
            ? `${plant.nom_vernaculaire} <span style="font-size:0.8em; opacity:0.75; font-weight:normal;">(${plant.nom || 'Inconnue'})</span>` 
            : (plant.nom || 'Inconnue');

        return `
            <div class="plant-card${uncheckedClass}" id="plant-card-${plant.id}">
                <div class="plant-image-wrapper" onclick="togglePlant('${plant.id}')">
                    ${imageHTML}
                    <span class="plant-type-badge${badgeClass}">${badge}</span>
                    <div class="plant-checkbox ${isChecked ? 'checked' : ''}">${isChecked ? '✓' : ''}</div>
                </div>
                <div class="plant-info">
                    <div class="plant-name">${displayNom}</div>
                    <div class="plant-common-type">${plant.type || ''} ${plant.sous_type && plant.sous_type !== plant.type ? '• ' + plant.sous_type : ''}</div>
                    <div class="plant-meta">
                        <div class="plant-meta-item" title="Couleur"><span class="plant-meta-icon">🎨</span><span>${plant.couleur || 'N/A'}</span></div>
                        <div class="plant-meta-item" title="Floraison/Saison"><span class="plant-meta-icon">📅</span><span>${plant.floraison || 'N/A'}</span></div>
                        <div class="plant-meta-item" title="Prix estimé (en fonction du budget)"><span class="plant-meta-icon">💰</span><span style="font-weight: bold; color: #10b981;">${plant.prix || 'N/A'}</span></div>
                        <div class="plant-meta-item" title="Besoin en eau"><span class="plant-meta-icon">💧</span><span>${waterLevel}</span></div>
                    </div>
                    <div class="plant-card-actions">
                        <button class="plant-toggle-btn ${isChecked ? 'active' : ''}" onclick="togglePlant('${plant.id}')">
                            ${isChecked ? '✓ Sélectionnée' : '○ Désélectionnée'}
                        </button>
                        <button class="plant-remove-btn-small" onclick="removePlant('${plant.id}')" title="Retirer définitivement">🗑️</button>
                    </div>
                </div>
            </div>
        `;
    }

    function getWaterLevel(besoin) {
        if (!besoin || besoin === 'N/A' || besoin === 'unknown') return 'N/A';
        const nums = besoin.split(',').map(n => parseInt(n.trim()));
        const avg = nums.reduce((a, b) => a + b, 0) / nums.length;
        if (avg <= 3) return 'Peu 💧';
        if (avg <= 5) return 'Modéré 💧💧';
        return 'Beaucoup 💧💧💧';
    }

    function formatPlan(text) {
        if (!text) return '<p>Plan non disponible</p>';
        let html = text
            .replace(/### (.*)/g, '<h3>$1</h3>')
            .replace(/## (.*)/g, '<h2>$1</h2>')
            .replace(/# (.*)/g, '<h1>$1</h1>')
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/\n- (.*)/g, '\n<li>$1</li>')
            .replace(/\n\d+\. (.*)/g, '\n<li>$1</li>')
            .replace(/\n\n/g, '</p><p>')
            .replace(/\n/g, '<br>');
        return `<div class="plan-content"><p>${html}</p></div>`;
    }

    async function loadStats() {
        try {
            const response = await fetch('/api/stats');
            const data = await response.json();
            const statsEl = document.getElementById('stats-total');
            if (statsEl) statsEl.textContent = data.total_plants || '0';
            populateSelect('filter-color', data.couleurs || [], '🎨 Toutes les couleurs');
            populateSelect('filter-type', data.types || [], '🌱 Tous les types');
            populateSelect('filter-sous-type', data.sous_types || [], '📁 Tous les sous-types');
            // Render garden styles
            if (data.garden_styles) {
                renderGardenStyles(data.garden_styles);
            }
        } catch (err) {
            console.log('Stats not loaded:', err);
        }
    }

    function populateSelect(id, values, defaultLabel) {
        const select = document.getElementById(id);
        if (!select) return;
        select.innerHTML = `<option value="">${defaultLabel}</option>`;
        values.forEach(v => {
            const opt = document.createElement('option');
            opt.value = v;
            opt.textContent = v;
            select.appendChild(opt);
        });
    }

    window.newAnalysis = function () {
        resultsSection.classList.remove('visible');
        errorMessage.classList.remove('visible');
        document.getElementById('search-panel').classList.remove('visible');
        currentAnalysis = null;
        currentPlants = [];
        addedPlants = [];
        checkedPlantIds.clear();
        removedPlantIds.clear();
        removePreview();
        heroSection.scrollIntoView({ behavior: 'smooth' });
    };

    // ── Garden Styles ──
    function renderGardenStyles(gardenStyles) {
        const container = document.getElementById('styles-container');
        if (!container) return;
        let html = '';
        
        for (const [catId, category] of Object.entries(gardenStyles)) {
            html += `<div class="style-category">`;
            html += `<h3 class="style-category-title">${category.label}</h3>`;
            html += `<div class="style-cards-grid">`;
            
            for (const [styleId, style] of Object.entries(category.styles)) {
                const entretienBars = '█'.repeat(Math.round(style.entretien / 2)) + '░'.repeat(5 - Math.round(style.entretien / 2));
                html += `
                    <div class="style-card" id="style-card-${styleId}" onclick="selectGardenStyle('${styleId}')">
                        <div class="style-radio"></div>
                        <div class="style-card-content">
                            <div class="style-card-name">${style.nom}</div>
                            <div class="style-card-desc">${style.description}</div>
                            <div class="style-card-meta">
                                <span title="Densité">🌿 ${style.densite}</span>
                                <span title="Tracé">📐 ${style.trace}</span>
                                <span title="Matériau">🧱 ${style.materiau}</span>
                                <span title="Entretien">🔧 ${entretienBars} (${style.entretien}/10)</span>
                            </div>
                        </div>
                    </div>
                `;
            }
            html += `</div></div>`;
        }
        container.innerHTML = html;
    }

    window.selectGardenStyle = function(styleId) {
        // Deselect previous
        document.querySelectorAll('.style-card').forEach(card => {
            card.classList.remove('selected');
            const radio = card.querySelector('.style-radio');
            if (radio) radio.innerHTML = '';
        });
        
        // Toggle: if clicking the same one, deselect
        if (selectedGardenStyle === styleId) {
            selectedGardenStyle = '';
            return;
        }
        
        selectedGardenStyle = styleId;
        const card = document.getElementById(`style-card-${styleId}`);
        if (card) {
            card.classList.add('selected');
            const radio = card.querySelector('.style-radio');
            if (radio) radio.innerHTML = '✓';
        }
    };

});
