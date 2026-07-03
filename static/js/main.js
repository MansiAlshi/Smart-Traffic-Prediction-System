document.addEventListener('DOMContentLoaded', () => {
    // ── Logout ─────────────────────────────────────────────
    const logoutBtn = document.getElementById('logoutBtn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', async () => {
            await fetch('/api/auth/logout', { method: 'POST' });
            window.location.href = '/login';
        });
    }

    // ── Dark mode ───────────────────────────────────────────
    const darkToggle = document.getElementById('darkModeToggle');
    const darkIcon   = document.getElementById('darkModeIcon');
    function applyDark(on) {
        document.body.classList.toggle('dark-mode', on);
        if (darkIcon) darkIcon.className = on ? 'bi bi-sun-fill' : 'bi bi-moon-fill';
        localStorage.setItem('darkMode', on ? '1' : '');
    }
    if (localStorage.getItem('darkMode') === '1') applyDark(true);
    if (darkToggle) darkToggle.addEventListener('click', () => applyDark(!document.body.classList.contains('dark-mode')));

    // ── Active nav highlight ────────────────────────────────
    const path = window.location.pathname;
    document.querySelectorAll('.navbar-nav .nav-link').forEach(link => {
        const href = link.getAttribute('href');
        if (!href) return;
        if ((href === '/' && path === '/') || (href !== '/' && path.startsWith(href))) {
            link.classList.add('active-nav');
        }
    });

    // ── Prediction count badge ──────────────────────────────
    const predLink = document.querySelector('.navbar-nav .nav-link[href="/prediction"]');
    if (predLink) {
        fetch('/api/predict/count').then(r => r.json()).then(data => {
            if (data.success && data.count > 0) {
                const badge = document.createElement('span');
                badge.className = 'badge bg-light text-primary ms-1';
                badge.textContent = data.count;
                predLink.appendChild(badge);
            }
        }).catch(() => {});
    }
});

// ══════════════════════════════════════════════════════════
//  TOAST NOTIFICATION SYSTEM
// ══════════════════════════════════════════════════════════
function showToast(message, type = 'success', duration = 3500) {
    let container = document.getElementById('toastContainer');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toastContainer';
        document.body.appendChild(container);
    }
    const icons = {
        success: 'bi-check-circle-fill',
        danger:  'bi-x-circle-fill',
        warning: 'bi-exclamation-triangle-fill',
        info:    'bi-info-circle-fill'
    };
    const toast = document.createElement('div');
    toast.className = `toast-item toast-${type}`;
    toast.innerHTML = `<i class="bi ${icons[type] || icons.info} me-2"></i><span>${message}</span>
                       <button class="toast-close">&times;</button>`;
    container.appendChild(toast);
    requestAnimationFrame(() => toast.classList.add('show'));
    const dismiss = () => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 350);
    };
    toast.querySelector('.toast-close').addEventListener('click', dismiss);
    setTimeout(dismiss, duration);
}

// ══════════════════════════════════════════════════════════
//  WEATHER  (via our own backend — works for all cities incl. small towns)
// ══════════════════════════════════════════════════════════
async function fetchCurrentWeather(cityName) {
    if (!cityName) return null;

    function mapCode(code) {
        if (code === 0) return 'Clear';
        if (code <= 3) return 'Cloudy';
        if (code <= 48) return 'Fog';
        if (code <= 67) return 'Rain';
        if (code <= 77) return 'Cloudy';
        if (code <= 82) return 'Rain';
        if (code <= 94) return 'Cloudy';
        return 'Storm';
    }

    // 1. Direct browser fetch to wttr.in (excellent Indian support & detailed descriptions)
    try {
        const res = await fetch(`https://wttr.in/${encodeURIComponent(cityName)}?format=j1`);
        if (res.ok) {
            const data = await res.json();
            if (data.current_condition && data.current_condition.length > 0) {
                const code = parseInt(data.current_condition[0].weatherCode);
                const desc = data.current_condition[0].weatherDesc?.[0]?.value || '';
                window._lastWeatherDesc = desc;

                const lowerDesc = desc.toLowerCase();
                if (lowerDesc.includes('rain') || lowerDesc.includes('drizzle') || lowerDesc.includes('shower')) return 'Rain';
                if (lowerDesc.includes('thunder') || lowerDesc.includes('storm')) return 'Storm';
                if (lowerDesc.includes('fog') || lowerDesc.includes('mist')) return 'Fog';
                if (lowerDesc.includes('cloud') || lowerDesc.includes('overcast')) return 'Cloudy';
                if (lowerDesc.includes('haze') || lowerDesc.includes('dust') || lowerDesc.includes('smoke')) return 'Haze';
                if (lowerDesc.includes('clear') || lowerDesc.includes('sunny')) return 'Clear';

                return mapCode(code);
            }
        }
    } catch (e) {
        console.warn('wttr.in client fetch failed, trying Open-Meteo client geocoding...', e);
    }

    // 2. Direct browser fetch to Open-Meteo (CORS-friendly fallback)
    try {
        const geoRes = await fetch(`https://geocoding-api.open-meteo.com/v1/search?name=${encodeURIComponent(cityName)}&count=1&language=en&format=json`);
        if (geoRes.ok) {
            const geoData = await geoRes.json();
            if (geoData.results && geoData.results.length > 0) {
                const { latitude: lat, longitude: lon } = geoData.results[0];
                const wxRes = await fetch(`https://api.open-meteo.com/v1/forecast?latitude=${lat}&longitude=${lon}&current=weather_code`);
                if (wxRes.ok) {
                    const wxData = await wxRes.json();
                    const code = wxData.current?.weather_code ?? 0;
                    window._lastWeatherDesc = `Live (WMO code ${code})`;
                    return mapCode(code);
                }
            }
        }
    } catch (e) {
        console.warn('Open-Meteo client fetch failed, trying backend proxy...', e);
    }

    // 3. Backend proxy fallback (uses server-side HTTP calls)
    try {
        const res = await fetch(`/api/analytics/weather?city=${encodeURIComponent(cityName)}`);
        if (res.ok) {
            const data = await res.json();
            if (data.success) {
                window._lastWeatherDesc = data.description || data.weather;
                return data.weather;
            }
        }
    } catch (e) {
        console.warn('Backend proxy fetch failed, using local season fallback...', e);
    }

    // 4. Seasonal guess (absolute last resort fallback)
    const month = new Date().getMonth() + 1;
    window._lastWeatherDesc = 'Season typical';
    if (month >= 6 && month <= 9) return 'Cloudy'; // More neutral default than always Rain
    return 'Clear';
}

// For coords-based fetch (used by live location button)
async function fetchWeatherByCoords(lat, lon) {
    // Reverse-geocode to city, then use our backend
    try {
        const res = await fetch(
            `https://nominatim.openstreetmap.org/reverse?lat=${lat}&lon=${lon}&format=json`,
            { headers: { 'Accept-Language': 'en' } }
        );
        const data = await res.json();
        const city = data.address?.city || data.address?.town || data.address?.village || data.address?.county || '';
        if (city) return await fetchCurrentWeather(city);
        // If reverse-geocode fails, call backend with coords directly
        const wxRes = await fetch(`/api/analytics/weather?city=Mumbai`); // safe default
        const wxData = await wxRes.json();
        return wxData.success ? wxData.weather : null;
    } catch { return null; }
}

// ══════════════════════════════════════════════════════════
//  LIVE LOCATION (Geolocation + Nominatim reverse geocode)
// ══════════════════════════════════════════════════════════
function getCurrentLocation(callback) {
    if (!navigator.geolocation) {
        showToast('Geolocation is not supported by your browser', 'warning');
        // Fallback: try IP-based location
        _ipLocationFallback(callback);
        return;
    }
    showToast('Detecting your location...', 'info', 2000);
    navigator.geolocation.getCurrentPosition(
        async pos => {
            const { latitude: lat, longitude: lon } = pos.coords;
            try {
                const res = await fetch(
                    `https://nominatim.openstreetmap.org/reverse?lat=${lat}&lon=${lon}&format=json`,
                    { headers: { 'Accept-Language': 'en' } }
                );
                const data = await res.json();
                const city = data.address?.city
                    || data.address?.town
                    || data.address?.village
                    || data.address?.county
                    || '';
                if (city) {
                    callback({ city, lat, lon });
                } else {
                    // Nominatim returned no city name — try IP fallback
                    showToast('GPS found but city name unclear. Trying IP location...', 'info', 2000);
                    _ipLocationFallback(callback);
                }
            } catch {
                // Nominatim failed — try IP fallback
                showToast('Reverse geocode failed. Trying IP location...', 'info', 2000);
                _ipLocationFallback(callback);
            }
        },
        (err) => {
            let msg = 'Location access denied.';
            if (err.code === 1) msg = 'Location permission denied. Trying IP-based location...';
            else if (err.code === 2) msg = 'Location unavailable. Trying IP-based location...';
            else if (err.code === 3) msg = 'Location timed out. Trying IP-based location...';
            showToast(msg, 'warning', 3000);
            // Fallback to IP-based geolocation
            _ipLocationFallback(callback);
        },
        { timeout: 10000, maximumAge: 60000, enableHighAccuracy: false }
    );
}

// IP-based geolocation fallback (no browser permission needed)
async function _ipLocationFallback(callback) {
    try {
        const res = await fetch('https://ipapi.co/json/');
        if (res.ok) {
            const data = await res.json();
            const city = data.city || data.region || '';
            const lat  = data.latitude  || null;
            const lon  = data.longitude || null;
            if (city) {
                showToast(`Location detected via IP: ${city}`, 'info', 2500);
                callback({ city, lat, lon });
                return;
            }
        }
    } catch (e) {
        console.warn('IP location fallback failed:', e);
    }
    // All methods failed
    showToast('Could not detect location. Please enter it manually.', 'warning');
    callback({ city: '', lat: null, lon: null });
}

// ══════════════════════════════════════════════════════════
//  HELPERS
// ══════════════════════════════════════════════════════════
function congestionClass(level) {
    return { Low: 'success', Medium: 'warning', High: 'danger' }[level] || 'secondary';
}
function congestionBadgeClass(level) {
    return { Low: 'congestion-low', Medium: 'congestion-medium', High: 'congestion-high' }[level] || '';
}
async function apiGet(url) {
    const res = await fetch(url);
    return res.json();
}
async function apiPost(url, body) {
    const res = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
    });
    return res.json();
}
function formatPercent(val) { return (parseFloat(val) * 100).toFixed(1) + '%'; }
function formatDateTime(value) {
    if (!value) return '-';
    const d = new Date(String(value).replace(' ', 'T'));
    return isNaN(d.getTime()) ? value : d.toLocaleString();
}
