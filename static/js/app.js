// ============================================================================
// SANHUB UNIFIED - Frontend Logic
// ============================================================================

// State
let allOrders = [];
let allTeams = [];
let map = null;
let routeLayer = null;
let markersLayer = null;

// Initialization
document.addEventListener('DOMContentLoaded', () => {
    initNavigation();
    initDate();
    initMap();
    initDragAndDrop();
    initFileInputs();
    
    // Load initial data
    loadDashboard();
    loadTeams();
    
    // Event Listeners
    document.getElementById('import-form').addEventListener('submit', handleImport);
    document.getElementById('team-form').addEventListener('submit', handleTeamSubmit);
    document.getElementById('cache-import-form').addEventListener('submit', handleCacheImport);
    document.getElementById('settings-form').addEventListener('submit', handleSettingsSubmit);
    
    // Filters
    document.getElementById('filter-status').addEventListener('change', loadTableData);
    document.getElementById('filter-category').addEventListener('change', loadTableData);
    document.getElementById('filter-search').addEventListener('input', debounce(loadTableData, 300));
    document.getElementById('btn-refresh-table').addEventListener('click', loadTableData);
    
    // Programing
    document.getElementById('prog-filter-cat').addEventListener('change', loadProgramingData);
    document.getElementById('prog-team-select').addEventListener('change', loadProgramingData);
    
    // Checkboxes and Assignment
    document.getElementById('check-all-available').addEventListener('change', (e) => {
        document.querySelectorAll('.chk-avail').forEach(cb => cb.checked = e.target.checked);
    });
    document.getElementById('check-all-team').addEventListener('change', (e) => {
        document.querySelectorAll('.chk-team').forEach(cb => cb.checked = e.target.checked);
    });
    
    document.getElementById('btn-assign-right').addEventListener('click', assignSelectedToTeam);
    document.getElementById('btn-assign-left').addEventListener('click', unassignSelectedFromTeam);
    document.getElementById('btn-save-order').addEventListener('click', saveTeamOrder);
    document.getElementById('btn-auto-assign').addEventListener('click', autoAssignSweep);
    
    // Routing
    document.getElementById('route-team-select').addEventListener('change', handleRouteTeamSelect);
    document.getElementById('btn-calculate-route').addEventListener('click', calculateRoute);
});

// ─────────────────────────────────────────────────────────────────────────────
// UI & NAVIGATION
// ─────────────────────────────────────────────────────────────────────────────

function initNavigation() {
    const navItems = document.querySelectorAll('.nav-item');
    const sections = document.querySelectorAll('.view-section');
    const pageTitle = document.getElementById('page-title');
    
    navItems.forEach(item => {
        item.addEventListener('click', (e) => {
            e.preventDefault();
            const targetId = item.getAttribute('data-target');
            
            // Update nav active state
            navItems.forEach(nav => nav.classList.remove('active'));
            item.classList.add('active');
            
            // Update page title
            pageTitle.textContent = item.textContent.trim();
            
            // Show target section
            sections.forEach(sec => sec.classList.add('hidden'));
            const targetSec = document.getElementById(targetId);
            targetSec.classList.remove('hidden');
            
            // Trigger specific load actions
            if (targetId === 'dashboard') loadDashboard();
            if (targetId === 'view') loadTableData();
            if (targetId === 'programing') loadProgramingData();
            if (targetId === 'teams') loadTeams();
            if (targetId === 'routing') {
                setTimeout(() => map.invalidateSize(), 100);
            }
        });
    });
}

function initDate() {
    const options = { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' };
    const dateStr = new Date().toLocaleDateString('pt-BR', options);
    document.getElementById('current-date').textContent = dateStr.charAt(0).toUpperCase() + dateStr.slice(1);
}

function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    sidebar.classList.toggle('collapsed');
    setTimeout(() => { if (map) map.invalidateSize(); }, 350);
}

function initFileInputs() {
    const fileInputs = document.querySelectorAll('.file-drop-area input[type="file"]');
    fileInputs.forEach(input => {
        input.addEventListener('change', (e) => {
            const fileName = e.target.files[0] ? e.target.files[0].name : '';
            const span = e.target.parentElement.querySelector('span');
            if (fileName) {
                span.textContent = fileName;
                span.classList.add('text-success', 'font-bold');
            }
        });
    });
}

function toggleModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal.classList.contains('hidden')) {
        modal.classList.remove('hidden');
    } else {
        modal.classList.add('hidden');
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// UTILS
// ─────────────────────────────────────────────────────────────────────────────

function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

function getCategoryBadge(cat) {
    if (cat === 'Calçada') return `<span class="badge badge-calcada">Calçada</span>`;
    if (cat === 'Asfalto') return `<span class="badge badge-asfalto">Asfalto</span>`;
    return `<span class="badge" style="background:#555; color:white;">${cat}</span>`;
}

function getStatusBadge(status) {
    if (status === 'Pendente') return `<span class="badge badge-pendente">Pendente</span>`;
    if (status === 'Executado') return `<span class="badge badge-executado">Executado</span>`;
    return `<span class="badge" style="background:#555; color:white;">${status}</span>`;
}

// ─────────────────────────────────────────────────────────────────────────────
// API CALLS
// ─────────────────────────────────────────────────────────────────────────────

async function fetchAPI(endpoint, options = {}) {
    try {
        const res = await fetch(endpoint, options);
        if (!res.ok) {
            const text = await res.text();
            try {
                const err = JSON.parse(text);
                throw new Error(err.detail || 'Erro na requisição');
            } catch (e) {
                // If it's not JSON, throw the raw text (e.g. Internal Server Error)
                throw new Error(`Erro no Servidor (${res.status}): ${text}`);
            }
        }
        return await res.json();
    } catch (error) {
        console.error(error);
        alert(error.message);
        throw error;
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// DASHBOARD
// ─────────────────────────────────────────────────────────────────────────────

async function loadDashboard() {
    const stats = await fetchAPI('/api/stats');
    document.getElementById('stat-total').textContent = stats.total;
    document.getElementById('stat-pendente').textContent = stats.pendente;
    document.getElementById('stat-executado').textContent = stats.executado;
    document.getElementById('stat-sem-equipe').textContent = stats.sem_equipe;
    
    document.getElementById('stat-calcada').textContent = stats.calcada_pendente;
    document.getElementById('stat-asfalto').textContent = stats.asfalto_pendente;
    
    // Bars logic
    const totalCat = stats.calcada_pendente + stats.asfalto_pendente;
    const calcadaPct = totalCat ? (stats.calcada_pendente / totalCat) * 100 : 0;
    const asfaltoPct = totalCat ? (stats.asfalto_pendente / totalCat) * 100 : 0;
    
    setTimeout(() => {
        document.getElementById('bar-calcada').style.width = `${calcadaPct}%`;
        document.getElementById('bar-asfalto').style.width = `${asfaltoPct}%`;
    }, 100);
}

// ─────────────────────────────────────────────────────────────────────────────
// IMPORT
// ─────────────────────────────────────────────────────────────────────────────

async function handleImport(e) {
    e.preventDefault();
    const form = e.target;
    const formData = new FormData(form);
    
    const btn = document.getElementById('btn-importar');
    const loader = document.getElementById('import-loader');
    
    btn.classList.add('hidden');
    loader.classList.remove('hidden');
    
    try {
        const res = await fetchAPI('/api/import', {
            method: 'POST',
            body: formData
        });
        alert(res.message);
        toggleModal('import-modal');
        loadDashboard();
    } catch (error) {
        // already handled in fetchAPI
    } finally {
        btn.classList.remove('hidden');
        loader.classList.add('hidden');
        form.reset();
        // Reset file input label
        const span = form.querySelector('.file-drop-area span');
        if(span && span.textContent !== 'Samsys A (Pendentes Gerais)') {
            span.classList.remove('text-success', 'font-bold');
        }
    }
}

async function handleCacheImport(e) {
    e.preventDefault();
    const form = e.target;
    const formData = new FormData(form);
    
    const btn = document.getElementById('btn-import-cache');
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Processando...';
    btn.disabled = true;
    
    try {
        const res = await fetchAPI('/api/cache/import', {
            method: 'POST',
            body: formData
        });
        alert(res.message);
        toggleModal('cache-modal');
    } catch (error) {
        // already handled
    } finally {
        btn.innerHTML = '<i class="fas fa-upload"></i> Substituir/Mesclar Banco';
        btn.disabled = false;
        form.reset();
        const span = form.querySelector('span');
        if(span) {
            span.textContent = 'banco_bairros_compartilhar.json';
            span.classList.remove('text-success', 'font-bold');
        }
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// VIEW TABLES
// ─────────────────────────────────────────────────────────────────────────────

async function loadTableData() {
    const status = document.getElementById('filter-status').value;
    const category = document.getElementById('filter-category').value;
    const search = document.getElementById('filter-search').value;
    
    const params = new URLSearchParams();
    if (status) params.append('status', status);
    if (category) params.append('category', category);
    if (search) params.append('search', search);
    
    const orders = await fetchAPI(`/api/orders?${params.toString()}`);
    const tbody = document.querySelector('#orders-table tbody');
    tbody.innerHTML = '';
    
    orders.forEach((o, i) => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td class="text-muted text-sm">${i + 1}</td>
            <td class="font-bold">${o.os_number}</td>
            <td>${o.neighborhood}</td>
            <td class="text-sm" style="max-width:250px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;" title="${o.service_description}">${o.service_description || '-'}</td>
            <td>${getCategoryBadge(o.category)}</td>
            <td>${getStatusBadge(o.status)}</td>
            <td>${o.team_name || '<span class="text-muted">Sem Equipe</span>'}</td>
        `;
        tbody.appendChild(tr);
    });
}

// ─────────────────────────────────────────────────────────────────────────────
// TEAMS
// ─────────────────────────────────────────────────────────────────────────────

async function loadTeams() {
    const teams = await fetchAPI('/api/teams');
    
    // Update Teams Table
    const tbody = document.querySelector('#teams-table tbody');
    if (tbody) {
        tbody.innerHTML = '';
        teams.forEach(t => {
            const isRouted = t.os_count > 0 && t.routed_count === t.os_count;
            const routeBadge = isRouted 
                ? '<span class="badge bg-success-soft text-success" style="margin-left: 8px;"><i class="fas fa-route"></i> Roteirizada</span>'
                : (t.os_count > 0 ? '<span class="badge bg-warning-soft text-warning" style="margin-left: 8px;">Sem Rota</span>' : '');
                
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${t.id}</td>
                <td class="font-bold">${t.name}</td>
                <td>${getCategoryBadge(t.type)}</td>
                <td><span class="badge bg-primary-soft text-primary">${t.os_count} Pendentes</span>${routeBadge}</td>
                <td>
                    <button class="btn btn-icon" onclick="deleteTeam(${t.id})"><i class="fas fa-trash text-danger"></i></button>
                </td>
            `;
            tbody.appendChild(tr);
        });
    }
    
    // Update Selects
    const selects = [
        document.getElementById('prog-team-select'),
        document.getElementById('route-team-select')
    ];
    
    selects.forEach(select => {
        if (!select) return;
        const currentVal = select.value;
        select.innerHTML = '<option value="">Selecione uma Equipe...</option>';
        teams.forEach(t => {
            const isRouted = t.os_count > 0 && t.routed_count === t.os_count;
            const routeText = isRouted ? ' ✔ Roteirizada' : '';
            select.innerHTML += `<option value="${t.id}">${t.name} (${t.type})${routeText}</option>`;
        });
        if (currentVal) select.value = currentVal;
    });
}

function openTeamModal() {
    document.getElementById('team-form').reset();
    document.getElementById('team_id').value = '';
    toggleModal('team-modal');
}

async function handleTeamSubmit(e) {
    e.preventDefault();
    const id = document.getElementById('team_id').value;
    const name = document.getElementById('team_name').value;
    const type = document.getElementById('team_type').value;
    
    const payload = { name, type };
    
    if (id) {
        await fetchAPI(`/api/teams/${id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
    } else {
        await fetchAPI(`/api/teams`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
    }
    
    toggleModal('team-modal');
    loadTeams();
}

async function deleteTeam(id) {
    if (confirm('Deseja realmente excluir esta equipe? As OS voltarão para Sem Equipe.')) {
        await fetchAPI(`/api/teams/${id}`, { method: 'DELETE' });
        loadTeams();
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// PROGRAMING (DRAG & DROP)
// ─────────────────────────────────────────────────────────────────────────────

function initDragAndDrop() {
    const list = document.getElementById('team-orders-sortable');
    Sortable.create(list, {
        handle: '.drag-handle',
        animation: 150,
        ghostClass: 'sortable-ghost',
        dragClass: 'sortable-drag',
        onEnd: () => {
            document.getElementById('btn-save-order').disabled = false;
        }
    });
}

async function loadProgramingData() {
    const cat = document.getElementById('prog-filter-cat').value;
    const teamId = document.getElementById('prog-team-select').value;
    
    // 1. Available OS (Pendente, sem equipe)
    const availParams = new URLSearchParams({ status: 'Pendente' });
    if (cat) availParams.append('category', cat);
    const availableOrders = await fetchAPI(`/api/orders?${availParams.toString()}`);
    
    const tbodyAvail = document.querySelector('#available-orders-table tbody');
    tbodyAvail.innerHTML = '';
    availableOrders.filter(o => !o.team_id).forEach(o => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td><input type="checkbox" class="chk-avail" value="${o.os_number}"></td>
            <td class="font-bold">${o.os_number}</td>
            <td class="text-sm" style="max-width:150px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">${o.neighborhood}</td>
            <td>${getCategoryBadge(o.category)}</td>
        `;
        tbodyAvail.appendChild(tr);
    });
    
    // 2. Team OS
    const tbodyTeam = document.getElementById('team-orders-sortable');
    const emptyState = document.getElementById('team-empty');
    const badge = document.getElementById('prog-team-badge');
    const btnSave = document.getElementById('btn-save-order');
    
    tbodyTeam.innerHTML = '';
    btnSave.disabled = true;
    
    if (!teamId) {
        emptyState.classList.remove('hidden');
        badge.textContent = '0 OS';
        return;
    }
    
    const teamOrders = await fetchAPI(`/api/orders?status=Pendente&team_id=${teamId}`);
    
    if (teamOrders.length === 0) {
        emptyState.classList.remove('hidden');
    } else {
        emptyState.classList.add('hidden');
        teamOrders.forEach(o => {
            const tr = document.createElement('tr');
            tr.setAttribute('data-id', o.os_number);
            tr.innerHTML = `
                <td><input type="checkbox" class="chk-team" value="${o.os_number}"></td>
                <td class="font-bold">${o.os_number}</td>
                <td class="text-sm" style="max-width:150px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">${o.neighborhood}</td>
                <td class="drag-handle"><i class="fas fa-bars"></i></td>
            `;
            tbodyTeam.appendChild(tr);
        });
    }
    badge.textContent = `${teamOrders.length} OS`;
}

async function assignSelectedToTeam() {
    const teamId = document.getElementById('prog-team-select').value;
    if (!teamId) return alert('Selecione uma equipe na direita primeiro.');
    
    const selected = Array.from(document.querySelectorAll('.chk-avail:checked')).map(cb => cb.value);
    if (selected.length === 0) return alert('Selecione pelo menos uma OS na esquerda.');
    
    await fetchAPI('/api/orders/assign', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ os_numbers: selected, team_id: parseInt(teamId) })
    });
    
    document.getElementById('check-all-available').checked = false;
    loadProgramingData();
}

async function unassignSelectedFromTeam() {
    const selected = Array.from(document.querySelectorAll('.chk-team:checked')).map(cb => cb.value);
    if (selected.length === 0) return alert('Selecione pelo menos uma OS na direita.');
    
    await fetchAPI('/api/orders/assign', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ os_numbers: selected, team_id: null })
    });
    
    document.getElementById('check-all-team').checked = false;
    loadProgramingData();
}

async function saveTeamOrder() {
    const teamId = document.getElementById('prog-team-select').value;
    if (!teamId) return;
    
    const rows = document.querySelectorAll('#team-orders-sortable tr');
    const osNumbers = Array.from(rows).map(tr => tr.getAttribute('data-id'));
    
    await fetchAPI('/api/orders/reorder', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ team_id: parseInt(teamId), os_numbers: osNumbers })
    });
    
    document.getElementById('btn-save-order').disabled = true;
    // alert('Ordem salva com sucesso!');
}

async function autoAssignSweep() {
    const cat = document.getElementById('prog-filter-cat').value;
    if (!cat) {
        alert("Selecione uma categoria específica (Calçada ou Asfalto) para realizar a divisão automática.");
        return;
    }
    
    const btn = document.getElementById('btn-auto-assign');
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Auto';
    btn.disabled = true;
    
    try {
        const res = await fetchAPI('/api/orders/auto-assign', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ category: cat })
        });
        alert(res.message);
        loadProgramingData();
    } catch (e) {
        // Erro já tratado no fetchAPI
    } finally {
        btn.innerHTML = '<i class="fas fa-magic"></i> Auto';
        btn.disabled = false;
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// ROUTING MAP
// ─────────────────────────────────────────────────────────────────────────────

function initMap() {
    // Inicializa centrado em Cuiabá (pode ser ajustado via config)
    map = L.map('map').setView([-15.5989, -56.0949], 12);
    
    L.tileLayer('https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png', {
        attribution: '&copy; OpenStreetMap &copy; CARTO',
        subdomains: 'abcd',
        maxZoom: 19
    }).addTo(map);
    
    markersLayer = L.layerGroup().addTo(map);
    routeLayer = L.layerGroup().addTo(map);
}

function handleRouteTeamSelect() {
    const val = document.getElementById('route-team-select').value;
    const btn = document.getElementById('btn-calculate-route');
    btn.disabled = !val;
    
    // Clear results
    document.getElementById('route-results').classList.add('hidden');
    markersLayer.clearLayers();
    routeLayer.clearLayers();
}

async function calculateRoute() {
    const teamId = document.getElementById('route-team-select').value;
    if (!teamId) return;
    
    const btn = document.getElementById('btn-calculate-route');
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Calculando...';
    btn.disabled = true;
    
    try {
        const res = await fetchAPI(`/api/route/${teamId}`, { method: 'POST' });
        renderRoute(res);
    } catch (e) {
        // Handled
    } finally {
        btn.innerHTML = '<i class="fas fa-route"></i> Calcular Rota (TSP)';
        btn.disabled = false;
    }
}

function renderRoute(res) {
    document.getElementById('route-results').classList.remove('hidden');
    
    const ul = document.getElementById('route-list-ul');
    ul.innerHTML = '';
    
    document.getElementById('route-dist').textContent = `${res.total_km} km`;
    document.getElementById('route-stops').textContent = res.route.length - 2; // Desconta Base inicial e final
    document.getElementById('route-gmaps').href = res.maps_link;
    
    markersLayer.clearLayers();
    routeLayer.clearLayers();
    
    if (res.route.length === 0) {
        ul.innerHTML = '<li class="text-muted">Nenhuma rota calculada.</li>';
        return;
    }
    
    const latlngs = [];
    
    res.route.forEach((p, idx) => {
        // Build Title and Badges
        let titleHtml = '';
        if (p.os_numbers.length === 1 && p.os_numbers[0] === 'BASE') {
            titleHtml = `<strong>BASE</strong><br><span class="text-sm text-muted">${p.neighborhood}</span>`;
        } else {
            const badges = p.os_numbers.map(os => `<span class="badge" style="background:var(--primary-soft); color:var(--primary); margin-right:4px; margin-bottom:4px; display:inline-block; font-size:0.75rem;">${os}</span>`).join('');
            titleHtml = `<strong>${p.neighborhood}</strong><br><div class="mt-1">${badges}</div>`;
        }

        // Lista UI
        const li = document.createElement('li');
        li.className = p.os_numbers[0] === 'BASE' ? '' : 'route-draggable';
        li.dataset.lat = p.lat;
        li.dataset.lon = p.lon;
        li.dataset.os = JSON.stringify(p.os_numbers);
        li.dataset.neighborhood = p.neighborhood;
        li.dataset.idx = idx;
        
        const dragHandle = p.os_numbers[0] === 'BASE' ? '' : '<div style="cursor: grab; margin-left: 10px; color: var(--text-muted);"><i class="fas fa-bars"></i></div>';
        
        li.innerHTML = `
            <div class="badge-num">${idx}</div>
            <div style="flex:1;">
                ${titleHtml}
                <div class="route-dist-calc text-sm text-primary mt-1">${p.distance_km > 0 ? '+' + p.distance_km + ' km' : ''}</div>
            </div>
            ${dragHandle}
        `;
        ul.appendChild(li);
        
        // Map markers & lines
        latlngs.push([p.lat, p.lon]);
        
        let color = '#3b82f6';
        if (p.os_numbers[0] === 'BASE') color = '#ef4444';
        
        const markerHtml = `
            <div style="background-color:${color}; color:white; width:24px; height:24px; border-radius:50%; display:flex; justify-content:center; align-items:center; font-weight:bold; border:2px solid white; box-shadow:0 2px 4px rgba(0,0,0,0.3);">
                ${idx}
            </div>
        `;
        const icon = L.divIcon({ html: markerHtml, className: '', iconSize: [24,24], iconAnchor: [12,12] });
        
        const popupText = p.os_numbers[0] === 'BASE' 
            ? `<b>BASE</b><br>${p.neighborhood}` 
            : `<b>${p.neighborhood}</b><br>${p.os_numbers.join(', ')}`;

        L.marker([p.lat, p.lon], { icon }).bindPopup(popupText).addTo(markersLayer);
    });
    
    // Draw line connecting points
    L.polyline(latlngs, { color: '#3b82f6', weight: 4, opacity: 0.7, dashArray: '10, 10' }).addTo(routeLayer);
    
    // Fit map bounds
    const bounds = L.latLngBounds(latlngs);
    map.fitBounds(bounds, { padding: [50, 50] });
    
    if (res.not_found && res.not_found.length > 0) {
        alert(`Atenção: Não foi possível geocodificar as seguintes OS/Bairros:\n${res.not_found.join(', ')}`);
    }
    
    // Init Sortable
    if (window.routeSortable) window.routeSortable.destroy();
    window.routeSortable = Sortable.create(ul, {
        animation: 150,
        filter: ':not(.route-draggable)', // Don't drag base
        onEnd: function() {
            recalcularRotaVisual();
        }
    });
}

function haversineDist(lat1, lon1, lat2, lon2) {
    const R = 6371;
    const dLat = (lat2 - lat1) * Math.PI / 180;
    const dLon = (lon2 - lon1) * Math.PI / 180;
    const a = Math.sin(dLat/2) * Math.sin(dLat/2) +
              Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
              Math.sin(dLon/2) * Math.sin(dLon/2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
    return R * c;
}

function recalcularRotaVisual() {
    const ul = document.getElementById('route-list-ul');
    const items = Array.from(ul.children);
    
    markersLayer.clearLayers();
    routeLayer.clearLayers();
    
    const latlngs = [];
    let totalKm = 0;
    
    // Google Maps link generation
    let gmapsUrl = "https://www.google.com/maps/dir/";
    
    items.forEach((li, idx) => {
        const lat = parseFloat(li.dataset.lat);
        const lon = parseFloat(li.dataset.lon);
        const osList = JSON.parse(li.dataset.os);
        const neighborhood = li.dataset.neighborhood;
        
        // Update numbering
        li.querySelector('.badge-num').textContent = idx;
        
        // Calculate distance from previous
        let distKm = 0;
        if (idx > 0) {
            const prevLi = items[idx-1];
            const prevLat = parseFloat(prevLi.dataset.lat);
            const prevLon = parseFloat(prevLi.dataset.lon);
            distKm = haversineDist(prevLat, prevLon, lat, lon);
            totalKm += distKm;
            
            const distDiv = li.querySelector('.route-dist-calc');
            if (distDiv) distDiv.textContent = `+${distKm.toFixed(2)} km`;
        }
        
        // Map markers
        latlngs.push([lat, lon]);
        gmapsUrl += `${lat},${lon}/`;
        
        let color = '#3b82f6';
        if (osList[0] === 'BASE') color = '#ef4444';
        
        const markerHtml = `
            <div style="background-color:${color}; color:white; width:24px; height:24px; border-radius:50%; display:flex; justify-content:center; align-items:center; font-weight:bold; border:2px solid white; box-shadow:0 2px 4px rgba(0,0,0,0.3);">
                ${idx}
            </div>
        `;
        const icon = L.divIcon({ html: markerHtml, className: '', iconSize: [24,24], iconAnchor: [12,12] });
        
        const popupText = osList[0] === 'BASE' 
            ? `<b>BASE</b><br>${neighborhood}` 
            : `<b>${neighborhood}</b><br>${osList.join(', ')}`;

        L.marker([lat, lon], { icon }).bindPopup(popupText).addTo(markersLayer);
    });
    
    // Draw line
    L.polyline(latlngs, { color: '#3b82f6', weight: 4, opacity: 0.7, dashArray: '10, 10' }).addTo(routeLayer);
    
    // Update total dist and maps link
    document.getElementById('route-dist').textContent = `${totalKm.toFixed(2)} km`;
    document.getElementById('route-gmaps').href = gmapsUrl;
}

function reverseRoute() {
    const ul = document.getElementById('route-list-ul');
    const items = Array.from(ul.children);
    if (items.length <= 2) return;
    
    // items[0] and items[items.length-1] might be BASE. Let's check them.
    const isBaseFirst = JSON.parse(items[0].dataset.os)[0] === 'BASE';
    const isBaseLast = JSON.parse(items[items.length - 1].dataset.os)[0] === 'BASE';
    
    let startIndex = isBaseFirst ? 1 : 0;
    let endIndex = isBaseLast ? items.length - 1 : items.length;
    
    const middleItems = items.slice(startIndex, endIndex);
    middleItems.reverse();
    
    // Re-append
    for(let i=0; i<middleItems.length; i++) {
        ul.insertBefore(middleItems[i], items[endIndex]);
    }
    
    recalcularRotaVisual();
}

// Limpar cache temporário local
async function clearLocalCache() {
    if(!confirm("Tem certeza que deseja apagar o cache temporário de geocodificação do SQLite? Os bairros do JSON continuarão seguros.")) return;
    
    try {
        const res = await fetchAPI('/api/cache', { method: 'DELETE' });
        alert(res.message || "Cache limpo com sucesso!");
    } catch (err) {
        // Error já tratado no fetchAPI
    }
}

// Configurações
async function openSettingsModal() {
    try {
        const settings = await fetchAPI('/api/settings');
        document.getElementById('base_lat').value = settings.base_lat || '';
        document.getElementById('base_lon').value = settings.base_lon || '';
        toggleModal('settings-modal');
    } catch (err) {
        console.error(err);
    }
}

async function handleSettingsSubmit(e) {
    e.preventDefault();
    const lat = document.getElementById('base_lat').value;
    const lon = document.getElementById('base_lon').value;
    
    try {
        const res = await fetchAPI('/api/settings', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ base_lat: lat, base_lon: lon })
        });
        alert(res.message);
        toggleModal('settings-modal');
    } catch (err) {
        // Error já tratado no fetchAPI
    }
}
