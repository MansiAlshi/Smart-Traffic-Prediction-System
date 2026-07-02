let probChart = null;
let predictionMap = null;
let predictionMapLayers = [];
let lastPredictionResult = null;   // stored for Compare A side

document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('predictionForm');
    if (!form) return;

    // Auto-fill date/time
    form.travel_date.value = new Date().toISOString().slice(0, 10);
    form.travel_time.value = new Date().toTimeString().slice(0, 5);

    // Swap source ↔ destination
    document.getElementById('swapBtn')?.addEventListener('click', () => {
        const tmp = form.source.value;
        form.source.value = form.destination.value;
        form.destination.value = tmp;
    });

    // Use current date & time
    document.getElementById('nowBtn')?.addEventListener('click', () => {
        form.travel_date.value = new Date().toISOString().slice(0, 10);
        form.travel_time.value = new Date().toTimeString().slice(0, 5);
    });

    // Live Location → auto-fill Source
    document.getElementById('locBtn')?.addEventListener('click', () => {
        getCurrentLocation(({ city, lat, lon }) => {
            if (city) {
                form.source.value = city;
                showToast(`Location set to: ${city}`, 'success');
            } else {
                showToast('Could not detect city name. Enter manually.', 'warning');
            }
            // Also auto-fill weather from coords
            fetchWeatherByCoords(lat, lon).then(wx => {
                if (wx) setWeatherSelect(form, wx);
            });
        });
    });

    // Weather auto-fill (manual button click)
    document.getElementById('weatherBtn')?.addEventListener('click', async (e) => {
        const btn = e.currentTarget;
        const city = form.source.value.trim() || 'Mumbai';
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span>';
        showToast(`Fetching weather for "${city}"...`, 'info', 2000);
        const wx = await fetchCurrentWeather(city);
        btn.disabled = false;
        btn.innerHTML = '<i class="bi bi-cloud-sun"></i>';
        if (wx) { setWeatherSelect(form, wx); showToast(`Weather set to: ${wx} ✓`, 'success'); }
    });

    // ── AUTO weather on blur ──────────────────────────────
    let weatherFetchTimer = null;
    const weatherBtn = document.getElementById('weatherBtn');

    async function autoFetchWeather(city) {
        if (!city) return;
        if (weatherBtn) { weatherBtn.innerHTML = '<span class="spinner-border spinner-border-sm"></span>'; }
        const wx = await fetchCurrentWeather(city);
        if (weatherBtn) { weatherBtn.innerHTML = '<i class="bi bi-cloud-sun"></i>'; }
        if (wx) {
            setWeatherSelect(form, wx);
            const desc = window._lastWeatherDesc || wx;
            showToast(`☁️ <strong>${wx}</strong> — ${desc} (auto-detected for ${city})`, 'info', 3000);
        }
    }

    // Source field — fetch weather when user leaves the field
    form.source.addEventListener('blur', () => {
        clearTimeout(weatherFetchTimer);
        const city = form.source.value.trim();
        if (city) weatherFetchTimer = setTimeout(() => autoFetchWeather(city), 400);
    });

    // Destination field — fetch weather only if source is empty
    form.destination.addEventListener('blur', () => {
        clearTimeout(weatherFetchTimer);
        const src  = form.source.value.trim();
        const dest = form.destination.value.trim();
        if (!src && dest) weatherFetchTimer = setTimeout(() => autoFetchWeather(dest), 400);
    });

    // Commute planner quick-use
    const saved = JSON.parse(localStorage.getItem('smarttraffic_commute') || 'null');
    if (saved) {
        document.getElementById('commuteCard').classList.remove('d-none');
        document.getElementById('commuteLabel').textContent = `${saved.home} → ${saved.work} at ${saved.time}`;
        document.getElementById('predictCommute').addEventListener('click', () => {
            form.source.value      = saved.home;
            form.destination.value = saved.work;
            form.travel_time.value = saved.time;
            form.road_type.value   = saved.road;
            form.travel_date.value = new Date().toISOString().slice(0, 10);
            form.dispatchEvent(new Event('submit'));
        });
    }

    // Main form submit
    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        const body = {
            source:             form.source.value.trim(),
            destination:        form.destination.value.trim(),
            weather_condition:  form.weather_condition.value,
            road_type:          form.road_type.value,
            travel_date:        form.travel_date.value,
            travel_time:        form.travel_time.value,
            festival_indicator: form.festival_indicator.checked ? 1 : 0,
        };
        const btn = form.querySelector('button[type="submit"]');
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Predicting...';
        try {
            const data = await apiPost('/api/predict', body);
            if (!data.success) {
                showToast(data.errors ? data.errors.join(', ') : (data.message || 'Prediction failed'), 'danger');
                return;
            }
            showPredictionResult(data.result);
        } finally {
            btn.disabled = false;
            btn.innerHTML = '<i class="bi bi-lightning-charge"></i> Predict Congestion';
        }
    });
});

function setWeatherSelect(form, weather) {
    const select = form.querySelector('[name="weather_condition"]');
    if (!select) return;
    // Use direct value assignment — most reliable cross-browser method
    select.value = weather;
    // Fallback: if the exact option text doesn't match, find closest
    if (select.value !== weather) {
        const opt = [...select.options].find(o => o.text.toLowerCase() === weather.toLowerCase());
        if (opt) opt.selected = true;
    }
}



function showPredictionResult(result) {
    document.getElementById('placeholderPanel').classList.add('d-none');
    document.getElementById('resultPanel').classList.remove('d-none');
    document.getElementById('suggestionsPanel').classList.remove('d-none');

    const badge = document.getElementById('congestionBadge');
    badge.textContent = result.predicted_congestion;
    badge.className = 'congestion-badge mb-2 ' + congestionBadgeClass(result.predicted_congestion);

    document.getElementById('confidenceScore').textContent = formatPercent(result.confidence_score);
    document.getElementById('trafficRisk').textContent = result.traffic_risk;
    document.getElementById('predId').textContent = result.prediction_id || '-';

    renderProbChart(result.probabilities);
    renderSuggestions(result);

    if (result.route) {
        const routeAlert = document.getElementById('predictionRouteAlert');
        routeAlert.classList.remove('d-none');
        routeAlert.innerHTML = `<i class="bi bi-signpost-split me-2"></i><strong>${result.route.recommended_route}</strong> — ` +
            `${result.route.distance_km} km · ~${result.route.estimated_time_min} min`;
        document.getElementById('routeMapPanel').classList.remove('d-none');
        renderPredictionMap(result.route);
    }
}

function renderProbChart(probabilities) {
    const labels = Object.keys(probabilities);
    const values = Object.values(probabilities);
    if (probChart) probChart.destroy();
    probChart = new Chart(document.getElementById('probChart'), {
        type: 'bar',
        data: {
            labels,
            datasets: [{ label: 'Probability', data: values, backgroundColor: ['#198754', '#ffc107', '#dc3545'] }]
        },
        options: {
            responsive: true,
            scales: { y: { max: 1, ticks: { callback: v => (v * 100) + '%' } } },
            plugins: { legend: { display: false } }
        }
    });
}

function clearPredictionMap() {
    if (!predictionMap) return;
    predictionMapLayers.forEach(l => predictionMap.removeLayer(l));
    predictionMapLayers = [];
}

function renderPredictionMap(route) {
    const center = [route.source.lat, route.source.lng];
    requestAnimationFrame(() => {
        if (!predictionMap) {
            predictionMap = L.map('predictionRouteMap').setView(center, 10);
            L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                attribution: '&copy; OpenStreetMap contributors', maxZoom: 18
            }).addTo(predictionMap);
        } else { clearPredictionMap(); }

        const latlngs = route.waypoints.map(w => [w[0], w[1]]);
        const poly = L.polyline(latlngs, { color: '#0d6efd', weight: 6, opacity: 0.9 }).addTo(predictionMap);
        poly.bindPopup(`<b>${route.recommended_route}</b><br>${route.source.name} → ${route.destination.name}<br>${route.distance_km} km · ${route.estimated_time_min} min`);
        predictionMapLayers.push(poly);
        predictionMapLayers.push(
            L.marker([route.source.lat, route.source.lng]).addTo(predictionMap).bindPopup(`<b>Start:</b> ${route.source.name}`),
            L.marker([route.destination.lat, route.destination.lng]).addTo(predictionMap).bindPopup(`<b>Destination:</b> ${route.destination.name}`)
        );
        predictionMap.fitBounds(L.latLngBounds(latlngs), { padding: [40, 40] });
        predictionMap.invalidateSize();
    });
}

function renderSuggestions(result) {
    const suggestions = [];
    if (result.route?.explanation) suggestions.push(result.route.explanation);
    if (result.predicted_congestion === 'High') {
        suggestions.push('Leave 15 minutes earlier to account for heavy congestion.');
        suggestions.push('Consider alternate routes with lower predicted traffic.');
    }
    if (result.traffic_risk === 'High') suggestions.push('High traffic risk — drive cautiously and maintain safe distance.');
    if (result.predicted_congestion === 'Medium') suggestions.push('Moderate traffic expected — plan a buffer of 10 minutes.');
    if (result.predicted_congestion === 'Low') suggestions.push('Traffic conditions look favorable — enjoy a smooth journey!');
    document.getElementById('suggestionsList').innerHTML = suggestions.map(s =>
        `<li class="list-group-item"><i class="bi bi-lightbulb text-warning me-2"></i>${s}</li>`
    ).join('');
}
