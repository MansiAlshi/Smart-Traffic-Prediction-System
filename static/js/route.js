let routeMap = null;
let routeLayers = [];
let lastRouteData = null;
let stepLayers = [];
let navState = {
    routeName: null,
    steps: [],
    idx: 0,
};

const routeColors = { 'Route A': '#0d6efd', 'Route B': '#198754', 'Route C': '#fd7e14' };

document.addEventListener('DOMContentLoaded', () => {
    const params = new URLSearchParams(window.location.search);
    const form = document.getElementById('routeForm');
    if (!form) return;

    // ── Restore last route result if user navigated away and came back ──
    const savedRoute = JSON.parse(localStorage.getItem(getUserKey('smarttraffic_last_route')) || 'null');
    if (savedRoute && savedRoute.result) {
        if (savedRoute.form) {
            if (savedRoute.form.source)           form.source.value = savedRoute.form.source;
            if (savedRoute.form.destination)      form.destination.value = savedRoute.form.destination;
            if (savedRoute.form.weather_condition) form.weather_condition.value = savedRoute.form.weather_condition;
            if (savedRoute.form.peak_hour_indicator !== undefined)
                form.peak_hour_indicator.checked = savedRoute.form.peak_hour_indicator === 1;
            if (savedRoute.form.festival_indicator !== undefined)
                form.festival_indicator.checked = savedRoute.form.festival_indicator === 1;
            // Silently refresh weather for the restored city
            if (savedRoute.form.source) {
                fetchCurrentWeather(savedRoute.form.source).then(wx => {
                    if (wx) form.weather_condition.value = wx;
                });
            }
        }
        lastRouteData = savedRoute.result;
        _showRouteResults(lastRouteData);
    }

    // URL params override saved source/dest (e.g. shared links)
    if (params.get('source')) form.source.value = params.get('source');
    if (params.get('dest'))   form.destination.value = params.get('dest');

    // Auto-detect location on page load only if source is still empty
    if (!form.source.value.trim()) {
        getCurrentLocation(({ city, lat, lon, source }) => {
            if (city && !form.source.value.trim()) {
                form.source.value = city;
                if (source === 'gps') showToast(`📍 Location detected: ${city}`, 'success', 2500);
                const wxPromise = (lat != null && lon != null)
                    ? fetchWeatherByCoords(lat, lon)
                    : fetchCurrentWeather(city);
                wxPromise.then(wx => {
                    if (wx) {
                        form.weather_condition.value = wx;
                        showToast(`☁️ Weather auto-set: ${wx}`, 'info', 2000);
                    }
                });
            }
        });
    }

    // Swap source ↔ destination
    document.getElementById('routeSwapBtn')?.addEventListener('click', () => {
        const src = form.source.value;
        form.source.value = form.destination.value;
        form.destination.value = src;
    });

    // Live location → auto-fill Source
    document.getElementById('routeLocBtn')?.addEventListener('click', () => {
        const btn = document.getElementById('routeLocBtn');
        if (btn) {
            btn.disabled = true;
            btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span>';
        }
        getCurrentLocation(({ city, lat, lon }) => {
            if (btn) {
                btn.disabled = false;
                btn.innerHTML = '<i class="bi bi-geo-alt-fill"></i>';
            }
            if (city) { form.source.value = city; showToast(`Location set to: ${city}`, 'success'); }
            // Only fetch weather if we have coordinates
            if (lat != null && lon != null) {
                fetchWeatherByCoords(lat, lon).then(wx => {
                    if (wx) { form.weather_condition.value = wx; showToast(`Weather set to: ${wx}`, 'info'); }
                });
            }
        });
    });

    // Weather auto-fill (manual button)
    document.getElementById('routeWeatherBtn')?.addEventListener('click', async () => {
        const city = form.source.value.trim() || 'Mumbai';
        const btn = document.getElementById('routeWeatherBtn');
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span>';
        showToast(`Fetching weather for "${city}"...`, 'info', 2000);
        const wx = await fetchCurrentWeather(city);
        btn.disabled = false;
        btn.innerHTML = '<i class="bi bi-cloud-sun"></i>';
        if (wx) { form.weather_condition.value = wx; showToast(`Weather set to: ${wx} ✓`, 'success'); }
    });

    // ── AUTO weather on blur ──────────────────────────────
    let wxTimer = null;
    const routeWxBtn = document.getElementById('routeWeatherBtn');

    async function autoRouteWeather(city) {
        if (!city) return;
        if (routeWxBtn) { routeWxBtn.innerHTML = '<span class="spinner-border spinner-border-sm"></span>'; }
        const wx = await fetchCurrentWeather(city);
        if (routeWxBtn) { routeWxBtn.innerHTML = '<i class="bi bi-cloud-sun"></i>'; }
        if (wx) {
            form.weather_condition.value = wx;
            showToast(`☁️ Weather auto-set to <strong>${wx}</strong> for ${city}`, 'info', 2500);
        }
    }

    form.source.addEventListener('blur', () => {
        clearTimeout(wxTimer);
        const city = form.source.value.trim();
        if (city) wxTimer = setTimeout(() => autoRouteWeather(city), 400);
    });

    form.destination.addEventListener('blur', () => {
        clearTimeout(wxTimer);
        const src  = form.source.value.trim();
        const dest = form.destination.value.trim();
        if (!src && dest) wxTimer = setTimeout(() => autoRouteWeather(dest), 400);
    });
    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        const btn = form.querySelector('button[type="submit"]');
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Finding routes...';

        try {
            const body = {
                source: form.source.value,
                destination: form.destination.value,
                weather_condition: form.weather_condition.value,
                peak_hour_indicator: form.peak_hour_indicator.checked ? 1 : 0,
                festival_indicator: form.festival_indicator.checked ? 1 : 0,
            };

            const data = await apiPost('/api/route/recommend', body);
            if (!data.success) {
                showToast(data.message || 'Route recommendation failed', 'danger');
                return;
            }

            lastRouteData = data.result;

            // Persist form + result so they survive page navigation
            localStorage.setItem(getUserKey('smarttraffic_last_route'), JSON.stringify({
                result: lastRouteData,
                form: body
            }));

            _showRouteResults(lastRouteData);
        } finally {
            btn.disabled = false;
            btn.innerHTML = '<i class="bi bi-signpost-split"></i> Find Best Route';
        }
    });

    document.getElementById('saveRouteBtn').addEventListener('click', async () => {
        if (!lastRouteData) return;
        const name = prompt('Enter a name for this route:', `${lastRouteData.source} to ${lastRouteData.destination}`);
        if (!name) return;

        const best = lastRouteData.routes.find(r => r.route_name === lastRouteData.recommended_route);
        const data = await apiPost('/api/route/save', {
            route_name: name,
            source: lastRouteData.source,
            destination: lastRouteData.destination,
            preferred_route: lastRouteData.recommended_route,
            source_lat: best?.source?.lat,
            source_lng: best?.source?.lng,
            dest_lat: best?.destination?.lat,
            dest_lng: best?.destination?.lng,
        });

        if (data.success) showToast('Route saved successfully!', 'success');
        else showToast(data.message || 'Failed to save route', 'danger');
    });
});



// ── Show route results (used by both submit and localStorage restore) ──
function _showRouteResults(data) {
    document.getElementById('routePlaceholder').classList.add('d-none');
    document.getElementById('routeResults').classList.remove('d-none');
    document.getElementById('saveRoutePanel').classList.remove('d-none');

    document.getElementById('recommendationAlert').innerHTML =
        `<i class="bi bi-check-circle me-2"></i><strong>${data.recommended_route}</strong> — ${data.explanation}`;

    renderRouteCards(data.routes, data.recommended_route);
    renderDirections(data.routes, data.recommended_route);
    renderRouteSuggestions(data.suggestions);
    renderRouteMap(data.routes, data.recommended_route);
}

function renderRouteCards(routes, recommended) {
    const container = document.getElementById('routeCards');
    container.innerHTML = routes.map(r => `
        <div class="col-md-4">
            <div class="card route-card h-100 ${r.route_name === recommended ? 'recommended' : ''}"
                 data-route="${r.route_name}" role="button">
                <div class="card-body">
                    <div class="d-flex justify-content-between align-items-start mb-2">
                        <h5 class="mb-0">${r.route_name}</h5>
                        ${r.route_name === recommended ? '<span class="badge bg-success">Best</span>' : ''}
                    </div>
                    <small class="text-muted d-block mb-2">${r.route_label}</small>
                    <hr>
                    <p class="mb-1"><strong>Congestion:</strong>
                        <span class="badge bg-${congestionClass(r.predicted_congestion)}">${r.predicted_congestion}</span></p>
                    <p class="mb-1"><strong>Risk Score:</strong> ${r.risk_score}</p>
                    <p class="mb-1"><strong>Difficulty:</strong> ${r.travel_difficulty}</p>
                    <p class="mb-1"><strong>Distance:</strong> ${r.distance_km} km</p>
                    <p class="mb-0"><strong>Est. Time:</strong> ${r.estimated_time_min} min</p>
                </div>
            </div>
        </div>
    `).join('');

    container.querySelectorAll('.route-card').forEach(card => {
        card.addEventListener('click', () => selectRoute(card.dataset.route));
    });
}

function renderDirections(routes, recommended) {
    const tabs = document.getElementById('directionTabs');
    const panels = document.getElementById('directionPanels');

    tabs.innerHTML = routes.map((r, i) => `
        <li class="nav-item" role="presentation">
            <button class="nav-link ${r.route_name === recommended ? 'active' : ''}"
                    id="tab-${i}" data-bs-toggle="pill" data-bs-target="#panel-${i}"
                    data-route="${r.route_name}" type="button" role="tab">
                <span class="route-color-dot" style="background:${routeColors[r.route_name]}"></span>
                ${r.route_name}
            </button>
        </li>
    `).join('');

    panels.innerHTML = routes.map((r, i) => `
        <div class="tab-pane fade ${r.route_name === recommended ? 'show active' : ''}"
             id="panel-${i}" role="tabpanel">
            <div class="direction-summary mb-3">
                <strong>${r.distance_km} km</strong> · <strong>${r.estimated_time_min} min</strong>
                · ${r.directions?.length || 0} steps
            </div>
            <ol class="direction-list mb-0">
                ${(r.directions || []).map((step, idx) => `
                    <li class="direction-step">
                        <div class="direction-step-icon">
                            <i class="bi ${directionIcon(step)}"></i>
                        </div>
                        <div class="direction-step-body">
                            <div class="direction-instruction">${step.instruction}</div>
                            ${step.distance_km > 0 ? `<small class="text-muted">${step.distance_km} km · ~${step.duration_min} min</small>` : ''}
                        </div>
                    </li>
                `).join('')}
            </ol>
        </div>
    `).join('');

    tabs.querySelectorAll('[data-route]').forEach(tab => {
        tab.addEventListener('shown.bs.tab', () => highlightRoute(tab.dataset.route));
        tab.addEventListener('click', () => selectRoute(tab.dataset.route));
    });
}

function directionIcon(step) {
    const t = step?.maneuver?.type;
    const m = step?.maneuver?.modifier;
    if (t === 'depart') return 'bi-play-fill';
    if (t === 'arrive') return 'bi-flag-fill';
    if (t === 'roundabout' || t === 'rotary' || t === 'roundabout turn') return 'bi-arrow-repeat';
    if (t === 'merge') return 'bi-intersect';
    if (t === 'fork') return 'bi-signpost-split';
    if (t === 'on ramp') return 'bi-box-arrow-in-up-right';
    if (t === 'off ramp') return 'bi-box-arrow-down-right';
    if (t === 'uturn') return 'bi-arrow-90deg-left';
    if (t === 'turn') {
        if (m && m.includes('left')) return 'bi-arrow-90deg-left';
        if (m && m.includes('right')) return 'bi-arrow-90deg-right';
        return 'bi-arrow-up';
    }
    if (t === 'continue') return 'bi-arrow-up';
    return 'bi-arrow-up';
}

function selectRoute(routeName) {
    highlightRoute(routeName);
    showStepsOnMap(routeName);
    initNavUI();
    setNavRoute(routeName);

    const tab = document.querySelector(`#directionTabs [data-route="${routeName}"]`);
    if (tab) bootstrap.Tab.getOrCreateInstance(tab).show();

    document.querySelectorAll('.route-card').forEach(card => {
        card.classList.toggle('active-route', card.dataset.route === routeName);
    });
}

function initNavUI() {
    const banner = document.getElementById('navBanner');
    if (!banner) return;

    if (banner.dataset.bound === '1') return;
    banner.dataset.bound = '1';

    document.getElementById('navPrev')?.addEventListener('click', () => navMove(-1));
    document.getElementById('navNext')?.addEventListener('click', () => navMove(1));
}

function navMove(delta) {
    if (!navState.steps.length) return;
    navState.idx = Math.max(0, Math.min(navState.steps.length - 1, navState.idx + delta));
    navRender();
    navFocusCurrent();
}

function setNavRoute(routeName) {
    if (!lastRouteData?.routes) return;
    const r = lastRouteData.routes.find(x => x.route_name === routeName);
    if (!r) return;

    // Use the same "important" filter as markers.
    const steps = (r.directions || []).filter((s, idx) => {
        const t = s?.maneuver?.type;
        if (idx === 0) return true;
        if (idx === (r.directions.length - 1)) return true;
        return ['turn', 'fork', 'merge', 'roundabout', 'rotary', 'roundabout turn', 'on ramp', 'off ramp', 'end of road'].includes(t);
    }).filter(s => !!s.latlng);

    navState.routeName = routeName;
    navState.steps = steps;
    navState.idx = 0;

    const banner = document.getElementById('navBanner');
    if (banner) banner.classList.toggle('d-none', steps.length === 0);

    navRender();
    navFocusCurrent();
}

function navRender() {
    const banner = document.getElementById('navBanner');
    if (!banner) return;
    const primary = document.getElementById('navPrimary');
    const secondary = document.getElementById('navSecondary');

    const step = navState.steps[navState.idx];
    if (!step) {
        primary.textContent = '-';
        secondary.textContent = '';
        return;
    }

    primary.textContent = step.instruction || '-';
    const next = navState.steps[navState.idx + 1];
    secondary.textContent = next ? `Then: ${next.instruction}` : '';
}

function navFocusCurrent() {
    if (!routeMap) return;
    const step = navState.steps[navState.idx];
    if (!step?.latlng) return;
    routeMap.setView(step.latlng, Math.max(routeMap.getZoom(), 14), { animate: true });
}

function clearStepLayers() {
    if (!routeMap) return;
    stepLayers.forEach(layer => routeMap.removeLayer(layer));
    stepLayers = [];
}

function clearRouteMap() {
    if (!routeMap) return;
    routeLayers.forEach(layer => routeMap.removeLayer(layer));
    routeLayers = [];
    clearStepLayers();
}

function renderRouteMap(routes, recommended) {
    if (!routes.length) return;

    const first = routes[0];
    const center = [first.source.lat, first.source.lng];

    requestAnimationFrame(() => {
        if (!routeMap) {
            routeMap = L.map('routeMap', { scrollWheelZoom: true }).setView(center, 10);
            L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                attribution: '&copy; OpenStreetMap contributors',
                maxZoom: 18,
            }).addTo(routeMap);
        } else {
            clearRouteMap();
        }

        const sourceIcon = L.divIcon({
            className: 'route-marker route-marker-source',
            html: '<i class="bi bi-geo-alt-fill"></i>',
            iconSize: [28, 28],
            iconAnchor: [14, 28],
        });
        const destIcon = L.divIcon({
            className: 'route-marker route-marker-dest',
            html: '<i class="bi bi-flag-fill"></i>',
            iconSize: [28, 28],
            iconAnchor: [14, 28],
        });

        routes.forEach(r => {
            const latlngs = r.waypoints.map(w => [w[0], w[1]]);
            const isBest = r.route_name === recommended;
            const polyline = L.polyline(latlngs, {
                color: routeColors[r.route_name] || '#333',
                weight: isBest ? 6 : 3,
                opacity: isBest ? 0.95 : 0.45,
                dashArray: isBest ? null : '8 6',
            }).addTo(routeMap);
            polyline.bindPopup(
                `<b>${r.route_name}</b><br>${r.route_label}<br>` +
                `Congestion: ${r.predicted_congestion}<br>` +
                `Distance: ${r.distance_km} km · ${r.estimated_time_min} min`
            );
            polyline.routeName = r.route_name;
            routeLayers.push(polyline);
        });

        const sourceMarker = L.marker([first.source.lat, first.source.lng], { icon: sourceIcon })
            .addTo(routeMap).bindPopup(`<b>Start:</b> ${first.source.name}`);
        const destMarker = L.marker([first.destination.lat, first.destination.lng], { icon: destIcon })
            .addTo(routeMap).bindPopup(`<b>Destination:</b> ${first.destination.name}`);
        routeLayers.push(sourceMarker, destMarker);

        const bounds = L.latLngBounds(
            routes.flatMap(r => r.waypoints.map(w => [w[0], w[1]]))
        );
        routeMap.fitBounds(bounds, { padding: [40, 40] });
        routeMap.invalidateSize();
        highlightRoute(recommended);
        showStepsOnMap(recommended);
    });
}

function highlightRoute(routeName) {
    if (!routeMap) return;

    document.querySelectorAll('.route-card').forEach(card => {
        card.classList.toggle('active-route', card.dataset.route === routeName);
    });

    routeLayers.forEach(layer => {
        if (!layer.routeName) return;
        const isActive = layer.routeName === routeName;
        layer.setStyle({
            weight: isActive ? 6 : 3,
            opacity: isActive ? 0.95 : 0.35,
            dashArray: isActive ? null : '8 6',
        });
        if (isActive) layer.bringToFront();
    });
}

function showStepsOnMap(routeName) {
    if (!routeMap || !lastRouteData?.routes) return;
    clearStepLayers();
    const r = lastRouteData.routes.find(x => x.route_name === routeName);
    if (!r?.directions?.length) return;

    const icon = L.divIcon({
        className: 'step-marker',
        html: '<i class="bi bi-arrow-right-circle-fill"></i>',
        iconSize: [22, 22],
        iconAnchor: [11, 11],
    });

    // Don't spam every micro-step: show only meaningful maneuvers + start/end.
    const important = r.directions.filter((s, idx) => {
        const t = s?.maneuver?.type;
        if (idx === 0) return true;
        if (idx === r.directions.length - 1) return true;
        return ['turn', 'fork', 'merge', 'roundabout', 'rotary', 'roundabout turn', 'on ramp', 'off ramp', 'end of road'].includes(t);
    });

    important.forEach((s, i) => {
        if (!s.latlng) return;
        const marker = L.marker(s.latlng, { icon })
            .addTo(routeMap)
            .bindPopup(`<b>Step ${i + 1}</b><br>${s.instruction}`);
        marker.on('click', () => {
            initNavUI();
            navState.routeName = routeName;
            navState.steps = important.filter(x => !!x.latlng);
            const idx = navState.steps.findIndex(x => x === s);
            navState.idx = idx >= 0 ? idx : 0;
            const banner = document.getElementById('navBanner');
            if (banner) banner.classList.remove('d-none');
            navRender();
        });
        stepLayers.push(marker);
    });
}

function renderRouteSuggestions(suggestions) {
    document.getElementById('routeSuggestions').innerHTML = suggestions
        .map(s => `<li class="mb-2"><i class="bi bi-lightbulb text-warning me-2"></i>${s}</li>`).join('');
}
