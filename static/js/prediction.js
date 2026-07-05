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

    // Restore last prediction result if user navigated away and came back
    const saved = JSON.parse(localStorage.getItem(getUserKey('smarttraffic_last_prediction')) || 'null');
    if (saved && saved.result) {
        // Restore form inputs
        if (saved.form) {
            if (saved.form.source) form.source.value = saved.form.source;
            if (saved.form.destination) form.destination.value = saved.form.destination;
            if (saved.form.weather_condition) form.weather_condition.value = saved.form.weather_condition;
            if (saved.form.road_type) form.road_type.value = saved.form.road_type;
            if (saved.form.travel_date) form.travel_date.value = saved.form.travel_date;
            if (saved.form.travel_time) form.travel_time.value = saved.form.travel_time;
            if (saved.form.festival_indicator !== undefined)
                form.festival_indicator.checked = saved.form.festival_indicator === 1;
            // Re-fetch live weather for the restored city (silently update, no toast)
            if (saved.form.source) {
                fetchCurrentWeather(saved.form.source).then(wx => { if (wx) setWeatherSelect(form, wx); }
                );
            }
        }
        // Restore result panel
        showPredictionResult(saved.result);
    }

    // Auto-detect location on page load if source is still empty
    if (!form.source.value.trim()) {
        getCurrentLocation(({ city, lat, lon, source }) => {
            if (city && !form.source.value.trim()) {
                form.source.value = city;
                // Only show toast for GPS — IP fallback already shows its own toast
                if (source === 'gps') showToast(`📍 Location detected: ${city}`, 'success', 2500);
                const wxPromise = (lat != null && lon != null)
                    ? fetchWeatherByCoords(lat, lon)
                    : fetchCurrentWeather(city);
                wxPromise.then(wx => {
                    if (wx) {
                        setWeatherSelect(form, wx);
                        showToast(`☁️ Weather auto-set: ${wx}`, 'info', 2000);
                    }
                });
            }
        });
    }

    // Live Location button → same as route.js
    const locBtn = document.getElementById('locBtn');
    if (locBtn) {
        locBtn.addEventListener('click', () => {
            locBtn.disabled = true;
            locBtn.innerHTML = '<span class="spinner-border spinner-border-sm"></span>';
            getCurrentLocation(({ city, lat, lon }) => {
                locBtn.disabled = false;
                locBtn.innerHTML = '<i class="bi bi-geo-alt-fill"></i>';
                if (city) {
                    form.source.value = city;
                    showToast(`📍 Location set to: ${city}`, 'success');
                } else {
                    showToast('Could not detect city. Please enter manually.', 'warning');
                }
                if (lat != null && lon != null) {
                    fetchWeatherByCoords(lat, lon).then(wx => { if (wx) setWeatherSelect(form, wx); });
                }
            });
        });
    }


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
        const src = form.source.value.trim();
        const dest = form.destination.value.trim();
        if (!src && dest) weatherFetchTimer = setTimeout(() => autoFetchWeather(dest), 400);
    });

    // Commute planner quick-use
    const savedCommute = JSON.parse(localStorage.getItem(getUserKey('smarttraffic_commute')) || 'null');
    if (savedCommute) {
        document.getElementById('commuteCard').classList.remove('d-none');
        document.getElementById('commuteLabel').textContent = `${savedCommute.home} → ${savedCommute.work} at ${savedCommute.time}`;
        document.getElementById('predictCommute').addEventListener('click', () => {
            form.source.value = savedCommute.home;
            form.destination.value = savedCommute.work;
            form.travel_time.value = savedCommute.time;
            form.road_type.value = savedCommute.road;
            form.travel_date.value = new Date().toISOString().slice(0, 10);
            form.dispatchEvent(new Event('submit'));
        });
    }

    // Main form submit
    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        const body = {
            source: form.source.value.trim(),
            destination: form.destination.value.trim(),
            weather_condition: form.weather_condition.value,
            road_type: form.road_type.value,
            travel_date: form.travel_date.value,
            travel_time: form.travel_time.value,
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
            // Save result + form inputs to localStorage so they persist across page navigation
            localStorage.setItem(getUserKey('smarttraffic_last_prediction'), JSON.stringify({
                result: data.result,
                form: body
            }));
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
    const order = ['Low', 'Medium', 'High'];
    const colorMap = {
        'Low': '#198754',    // Green
        'Medium': '#ffc107', // Yellow/Orange
        'High': '#dc3545'    // Red
    };

    const labels = order.filter(k => k in probabilities);
    const values = labels.map(k => probabilities[k]);
    const backgroundColors = labels.map(k => colorMap[k]);

    if (probChart) probChart.destroy();
    probChart = new Chart(document.getElementById('probChart'), {
        type: 'bar',
        data: {
            labels,
            datasets: [{ 
                label: 'Probability', 
                data: values, 
                backgroundColor: backgroundColors 
            }]
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
    const congestion = result.predicted_congestion;
    const risk = result.traffic_risk;

    // ── Overall congestion advice (based on the main prediction) ──
    if (congestion === 'High') {
        suggestions.push('🔴 <strong>Heavy congestion predicted</strong> — leave at least 15–20 minutes earlier than usual.');
        suggestions.push('Consider alternate routes or off-peak travel times to avoid delays.');
    } else if (congestion === 'Medium') {
        suggestions.push('🟡 <strong>Moderate congestion expected</strong> — plan a buffer of 10 minutes for your journey.');
    } else if (congestion === 'Low') {
        suggestions.push('🟢 <strong>Light traffic conditions</strong> — enjoy a smooth journey!');
    }

    // ── Risk-based advice ──
    if (risk === 'High') {
        suggestions.push('⚠️ High traffic risk detected — drive cautiously and maintain a safe following distance.');
    }

    // ── Route recommendation (separate scope — this is per-route, not overall) ──
    if (result.route?.explanation) {
        // Strip out any embedded "Predicted congestion: X" clause to avoid confusion
        // and re-state it clearly as route-level info
        suggestions.push(`🛣️ <strong>Best route:</strong> ${result.route.explanation}`);
    }

    document.getElementById('suggestionsList').innerHTML = suggestions.map(s =>
        `<li class="list-group-item"><i class="bi bi-lightbulb text-warning me-2"></i>${s}</li>`
    ).join('');
}

