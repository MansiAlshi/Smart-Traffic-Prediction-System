let allHistory = [];

async function loadHistory() {
    const tbody = document.getElementById('historyTable');
    try {
        const data = await apiGet('/api/route/history');
        if (!data.success) {
            tbody.innerHTML = `<tr><td colspan="10" class="text-center text-danger">${data.message || 'Failed to load history'}</td></tr>`;
            return;
        }
        allHistory = data.history || [];
        renderHistory(allHistory);
    } catch {
        tbody.innerHTML = '<tr><td colspan="10" class="text-center text-danger">Failed to load travel history</td></tr>';
    }
}

function renderHistory(items) {
    const tbody = document.getElementById('historyTable');
    if (!items.length) {
        tbody.innerHTML = '<tr><td colspan="10" class="text-center text-muted">No travel history yet. Use Route Recommendation to plan a trip.</td></tr>';
        return;
    }
    tbody.innerHTML = items.map(h => `
        <tr>
            <td>${formatDateTime(h.travel_date)}</td>
            <td>${h.source_location}</td>
            <td>${h.destination_location}</td>
            <td>${h.route_name || '-'}</td>
            <td><span class="badge bg-${congestionClass(h.predicted_congestion)}">${h.predicted_congestion || '-'}</span></td>
            <td>${h.risk_score ?? '-'}</td>
            <td>${h.travel_difficulty || '-'}</td>
            <td>${h.distance_km ? h.distance_km + ' km' : '-'}</td>
            <td>${h.estimated_time_min ? h.estimated_time_min + ' min' : '-'}</td>
            <td>
                <button class="btn btn-sm btn-outline-danger" onclick="deleteHistory(${h.history_id})">Delete</button>
            </td>
        </tr>
    `).join('');
}

function filterHistory() {
    const search = document.getElementById('historySearch')?.value.toLowerCase() || '';
    const filter = document.getElementById('historyFilter')?.value || '';
    const filtered = allHistory.filter(h => {
        const matchText = !search ||
            h.source_location.toLowerCase().includes(search) ||
            h.destination_location.toLowerCase().includes(search);
        const matchCong = !filter || h.predicted_congestion === filter;
        return matchText && matchCong;
    });
    renderHistory(filtered);
}

async function loadSavedRoutes() {
    const tbody = document.getElementById('savedRoutesTable');
    try {
        const data = await apiGet('/api/route/saved');
        if (!data.success) {
            tbody.innerHTML = `<tr><td colspan="5" class="text-center text-danger">${data.message || 'Failed to load saved routes'}</td></tr>`;
            return;
        }
        if (!data.routes.length) {
            tbody.innerHTML = '<tr><td colspan="5" class="text-center text-muted">No saved routes yet. Save a route from the Routes page.</td></tr>';
            return;
        }

        tbody.innerHTML = data.routes.map(r => `
            <tr>
                <td>${r.route_name}</td>
                <td>${r.source_location}</td>
                <td>${r.destination_location}</td>
                <td>${r.preferred_route}</td>
                <td>
                    <a href="/route-recommendation?source=${encodeURIComponent(r.source_location)}&dest=${encodeURIComponent(r.destination_location)}"
                       class="btn btn-sm btn-outline-primary">Use</a>
                    <button class="btn btn-sm btn-outline-secondary" onclick="copyRoute('${r.source_location}', '${r.destination_location}')" title="Copy route info">
                        <i class="bi bi-clipboard"></i> Copy
                    </button>
                    <button class="btn btn-sm btn-outline-danger" onclick="deleteRoute(${r.route_id})">Delete</button>
                </td>
            </tr>
        `).join('');
    } catch {
        tbody.innerHTML = '<tr><td colspan="5" class="text-center text-danger">Failed to load saved routes</td></tr>';
    }
}

function copyRoute(source, destination) {
    const text = `Source: ${source}\nDestination: ${destination}`;
    navigator.clipboard.writeText(text)
        .then(() => showToast('Route copied to clipboard!', 'success'))
        .catch(() => prompt('Copy this route info:', text));
}

async function deleteRoute(routeId) {
    if (!confirm('Delete this saved route?')) return;
    const res = await fetch(`/api/route/saved/${routeId}`, { method: 'DELETE' });
    const data = await res.json();
    if (data.success) { showToast('Route deleted.', 'success'); loadSavedRoutes(); }
    else showToast(data.message || 'Failed to delete route.', 'danger');
}

async function deleteHistory(historyId) {
    if (!confirm('Delete this history item?')) return;
    const res = await fetch(`/api/route/history/${historyId}`, { method: 'DELETE' });
    const data = await res.json();
    if (data.success) { showToast('History item deleted.', 'success'); loadHistory(); }
    else showToast(data.message || 'Failed to delete.', 'danger');
}

async function clearHistory() {
    if (!confirm('Clear ALL travel history?')) return;
    const res = await fetch('/api/route/history', { method: 'DELETE' });
    const data = await res.json();
    if (data.success) { showToast('All history cleared.', 'success'); loadHistory(); }
    else showToast(data.message || 'Failed to clear history.', 'danger');
}

function exportHistoryPdf() {
    const table = document.getElementById('historyTableEl');
    if (!table) return;

    // Build simple print page
    const rows = [...table.querySelectorAll('tr')].map(tr =>
        `<tr>${[...tr.querySelectorAll('th,td')].map(cell =>
            `<td style="border:1px solid #ccc;padding:6px 10px;font-size:12px">${cell.innerText}</td>`
        ).join('')}</tr>`
    ).join('');

    const win = window.open('', '_blank');
    win.document.write(`
        <html><head><title>Travel History - SmartTraffic AI</title></head>
        <body>
            <h2 style="font-family:sans-serif">Travel History Report</h2>
            <p style="font-family:sans-serif;color:#666">Generated: ${new Date().toLocaleString()}</p>
            <table style="border-collapse:collapse;width:100%;font-family:sans-serif">${rows}</table>
        </body></html>
    `);
    win.document.close();
    win.print();
}

document.addEventListener('DOMContentLoaded', () => {
    loadHistory();
    loadSavedRoutes();

    document.getElementById('clearHistoryBtn')?.addEventListener('click', clearHistory);
    document.getElementById('exportPdfBtn')?.addEventListener('click', exportHistoryPdf);
    document.getElementById('historySearch')?.addEventListener('input', filterHistory);
    document.getElementById('historyFilter')?.addEventListener('change', filterHistory);

    const params = new URLSearchParams(window.location.search);
    if (params.get('source') && params.get('dest')) {
        window.location.href = `/route-recommendation?source=${params.get('source')}&dest=${params.get('dest')}`;
    }
});
