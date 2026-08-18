// ============================================================
// JARVIS — shared.js
// Shared utilities for dashboard.js and space_dashboard.js
// ============================================================

// -----------------------------------------------------------
// WORLD VECTOR MAP DATA
// Simplified cyberpunk-style continent outlines (Lon, Lat pairs)
// -----------------------------------------------------------
const WORLD_VECTORS = [
    // North America
    [ [-168, 65], [-120, 60], [-80, 70], [-60, 50], [-80, 25], [-100, 20], [-110, 10], [-90, 15], [-80, 9], [-80, 20], [-120, 35], [-125, 48], [-168, 65] ],
    // South America
    [ [-80, 9], [-50, -5], [-35, -7], [-70, -55], [-75, -50], [-70, -20], [-80, -5], [-80, 9] ],
    // Africa / Europe / Asia
    [ [-15, 65], [10, 60], [30, 70], [60, 75], [100, 75], [170, 70], [140, 35], [110, 15], [80, 10], [50, 12], [40, 25], [32, 30], [20, 10], [15, -34], [30, -30], [40, -15], [50, 12], [30, 30], [10, 35], [-15, 20], [-15, 65] ],
    // Greenland
    [ [-60, 75], [-40, 70], [-30, 80], [-60, 80], [-60, 75] ],
    // Australia
    [ [115, -20], [145, -15], [150, -35], [115, -33], [113, -25], [115, -20] ]
];

// -----------------------------------------------------------
// GPS → CANVAS PIXEL CONVERSION
// Maps a geographic coordinate to an (x, y) pixel on a canvas.
// -----------------------------------------------------------
function gpsToPixels(lon, lat, canvas) {
    if (!canvas) return { x: 0, y: 0 };
    const margin = 20;
    const px = ((lon + 180) / 360) * (canvas.width - margin * 2) + margin;
    const py = (1.0 - (lat + 90) / 180) * (canvas.height - margin * 2) + margin;
    return { x: px, y: py };
}

// -----------------------------------------------------------
// DRAW WORLD MAP
// Renders cyberpunk vector continent outlines on a given canvas context.
// -----------------------------------------------------------
function drawWorldMap(ctx, canvas) {
    ctx.strokeStyle = 'rgba(0, 243, 255, 0.15)';
    ctx.lineWidth = 1.2;
    ctx.fillStyle = 'rgba(0, 243, 255, 0.015)';
    WORLD_VECTORS.forEach(polygon => {
        ctx.beginPath();
        polygon.forEach((pt, idx) => {
            const pos = gpsToPixels(pt[0], pt[1], canvas);
            if (idx === 0) ctx.moveTo(pos.x, pos.y);
            else ctx.lineTo(pos.x, pos.y);
        });
        ctx.stroke();
        ctx.fill();
    });
}

// -----------------------------------------------------------
// DRAW GRID AND AXES
// Renders lat/lon grid lines and axis labels on a given canvas context.
// -----------------------------------------------------------
function drawGridAndAxes(ctx, canvas) {
    ctx.strokeStyle = 'rgba(0, 243, 255, 0.04)';
    ctx.lineWidth = 1;

    // Longitude lines (vertical, -180 to 180, step 30)
    for (let lon = -180; lon <= 180; lon += 30) {
        const p1 = gpsToPixels(lon, -90, canvas);
        const p2 = gpsToPixels(lon, 90, canvas);
        ctx.beginPath();
        ctx.moveTo(p1.x, p1.y);
        ctx.lineTo(p2.x, p2.y);
        ctx.stroke();

        if (lon % 60 === 0) {
            ctx.fillStyle = 'rgba(0, 243, 255, 0.35)';
            ctx.font = '8px "Share Tech Mono"';
            ctx.textAlign = 'center';
            const label = lon === 0 ? '0°' : lon > 0 ? `${lon}°E` : `${Math.abs(lon)}°W`;
            ctx.fillText(label, p1.x, canvas.height - 4);
        }
    }

    // Latitude lines (horizontal, -90 to 90, step 30)
    for (let lat = -90; lat <= 90; lat += 30) {
        const p1 = gpsToPixels(-180, lat, canvas);
        const p2 = gpsToPixels(180, lat, canvas);
        ctx.beginPath();
        ctx.moveTo(p1.x, p1.y);
        ctx.lineTo(p2.x, p2.y);
        ctx.stroke();

        if (lat % 30 === 0 && lat !== -90 && lat !== 90) {
            ctx.fillStyle = 'rgba(0, 243, 255, 0.35)';
            ctx.font = '8px "Share Tech Mono"';
            ctx.textAlign = 'left';
            const label = lat === 0 ? '0°' : lat > 0 ? `${lat}°N` : `${Math.abs(lat)}°S`;
            ctx.fillText(label, 4, p1.y - 2);
        }
    }
}

// -----------------------------------------------------------
// FORMAT TIME STRING
// Converts an ISO datetime string to a local HH:MM display string.
// e.g. "2026-08-18T14:30:00" → "14:30"
// -----------------------------------------------------------
function formatTimeString(isoString) {
    if (!isoString) return '--:--';
    try {
        const date = new Date(isoString);
        return `${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`;
    } catch (e) {
        return '--:--';
    }
}

// -----------------------------------------------------------
// FORMAT EPOCH TO UTC STRING
// Converts a Unix timestamp in milliseconds to a readable UTC string.
// e.g. 1724000000000 → "08/18 14:23 UTC"
// -----------------------------------------------------------
function formatEpochToUTC(ms) {
    if (!ms) return '--';
    const d = new Date(ms);
    const mm = String(d.getUTCMonth() + 1).padStart(2, '0');
    const dd = String(d.getUTCDate()).padStart(2, '0');
    const hh = String(d.getUTCHours()).padStart(2, '0');
    const min = String(d.getUTCMinutes()).padStart(2, '0');
    return `${mm}/${dd} ${hh}:${min} UTC`;
}

// -----------------------------------------------------------
// PARSE FLIGHT ROUTE
// Heuristically determines the origin → destination route for a flight.
// Used by both the radar sidebar panel and FIDS timetable.
// -----------------------------------------------------------
function parseFlightRoute(flight) {
    const origin = (flight.origin || '').toUpperCase();
    const dest = (flight.destination || '').toUpperCase();
    const callsign = (flight.callsign || '').trim().toUpperCase();
    const track = flight.track || 0;

    if (origin === 'CMB') {
        return { type: 'DEP', route: `CMB ➔ ${dest || 'SIN'}` };
    }
    if (dest === 'CMB') {
        return { type: 'ARR', route: `${origin || 'DXB'} ➔ CMB` };
    }

    // Heuristic: heading roughly east/south = departing, heading north/west = arriving
    if (track > 45 && track <= 225) {
        let destination = 'SIN';
        if (callsign.startsWith('UL') || callsign.startsWith('SQ')) destination = 'SIN';
        else if (callsign.startsWith('MH')) destination = 'KUL';
        else if (callsign.startsWith('AI')) destination = 'MAA';
        return { type: 'DEP', route: `CMB ➔ ${destination}` };
    } else {
        let origin = 'DXB';
        if (callsign.startsWith('UL') || callsign.startsWith('EK')) origin = 'DXB';
        else if (callsign.startsWith('QR')) origin = 'DOH';
        else if (callsign.startsWith('EY')) origin = 'AUH';
        return { type: 'ARR', route: `${origin} ➔ CMB` };
    }
}

// -----------------------------------------------------------
// CRYPTO TICKER UPDATE
// Populates ticker element values from a prices object.
// Applies .up / .down CSS classes based on previous value.
// -----------------------------------------------------------
function updateCryptoTicker(prices) {
    const map = {
        'btc': 't-btc', 'eth': 't-eth', 'bnb': 't-bnb',
        'sol': 't-sol', 'xrp': 't-xrp', 'doge': 't-doge',
        'gold': 't-gold', 'oil': 't-oil', 'lkr': 't-lkr', 'eur': 't-eur'
    };
    Object.entries(map).forEach(([key, id]) => {
        const el = document.getElementById(id);
        if (!el) return;
        const val = prices[key];
        if (val === undefined || val === null) return;
        const prev = parseFloat(el.dataset.prev || val);
        el.dataset.prev = val;
        const numVal = parseFloat(val);
        if (isNaN(numVal)) { el.innerText = val; return; }
        el.innerText = numVal > 1000
            ? `$${numVal.toLocaleString('en-US', { maximumFractionDigits: 0 })}`
            : numVal > 1
            ? `$${numVal.toFixed(2)}`
            : `$${numVal.toFixed(4)}`;
        el.className = 'tick-price' + (numVal > prev ? ' up' : numVal < prev ? ' down' : '');
    });
}

// -----------------------------------------------------------
// SCRIPT POLLER
// Generic helper to reload a JS data file on an interval.
// Both dashboards use this pattern for data.js and space_data.js.
//
// Usage:
//   startScriptPoller('data.js', 'data-script', (data) => {...}, 2000);
// -----------------------------------------------------------
function startScriptPoller(src, scriptId, onLoad, intervalMs) {
    function reload() {
        const old = document.getElementById(scriptId);
        if (old) old.remove();
        const script = document.createElement('script');
        script.id = scriptId;
        script.src = `${src}?t=${Date.now()}`;
        script.onload = onLoad;
        document.head.appendChild(script);
    }
    reload(); // Immediate first load
    return setInterval(reload, intervalMs);
}
