const heatmapMaps = {};

async function initHeatmap(containerId) {
    const el = document.getElementById(containerId);
    if (!el) return;

    const map = L.map(containerId).setView([22.5, 79.0], 5);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; OpenStreetMap'
    }).addTo(map);

    heatmapMaps[containerId] = map;

    const legend = L.control({ position: 'bottomright' });
    legend.onAdd = () => {
        const div = L.DomUtil.create('div', 'heatmap-legend');
        div.innerHTML = '<strong>Congestion</strong><br>' +
            '<i class="legend-low"></i> Low<br>' +
            '<i class="legend-medium"></i> Medium<br>' +
            '<i class="legend-high"></i> High';
        return div;
    };
    legend.addTo(map);

    const data = await apiGet('/api/analytics/heatmap');
    if (!data.success) return;

    const colorMap = { Low: '#198754', Medium: '#ffc107', High: '#dc3545' };
    const radiusMap = { Low: 8000, Medium: 12000, High: 16000 };

    data.heatmap.forEach(point => {
        L.circle([point.lat, point.lng], {
            color: colorMap[point.congestion],
            fillColor: colorMap[point.congestion],
            fillOpacity: 0.45,
            radius: radiusMap[point.congestion],
            weight: 1
        }).addTo(map).bindPopup(
            `<b>${point.city}</b><br>Hour: ${point.hour}:00<br>Congestion: ${point.congestion}`
        );
    });
}
