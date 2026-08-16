// ==============================
// ORBITAL TELEMETRY CORE — JS
// Handles: ISS, APOD, Crew, Space Weather, Earthquakes, Maritime, Crypto
// ==============================

// Canvas setup
const canvas = document.getElementById('orbit-canvas');
const ctx = canvas.getContext('2d');

let issPos = { lat: 0, lon: 0 };
let orbitalHistory = [];
let mapSweepAngle = 0;
let earthquakeMarkers = []; // Store for canvas drawing

// Cyberpunk simplified vector world map outline coordinates
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

function resizeCanvas() {
    const rect = canvas.parentElement.getBoundingClientRect();
    canvas.width = rect.width;
    canvas.height = rect.height;
}
window.addEventListener('resize', resizeCanvas, { passive: true });
resizeCanvas();

function gpsToPixels(lon, lat) {
    const margin = 25;
    const px = ((lon + 180) / 360) * (canvas.width - margin * 2) + margin;
    const py = (1.0 - (lat + 90) / 180) * (canvas.height - margin * 2) + margin;
    return { x: px, y: py };
}

function drawOrbitMap() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // 1. Draw grid
    ctx.strokeStyle = 'rgba(0, 243, 255, 0.05)';
    ctx.lineWidth = 1;
    for (let i = 0; i <= 18; i++) {
        const x = (canvas.width / 18) * i;
        ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, canvas.height); ctx.stroke();
    }
    for (let j = 0; j <= 10; j++) {
        const y = (canvas.height / 10) * j;
        ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(canvas.width, y); ctx.stroke();
    }

    // 2. Draw continents
    ctx.strokeStyle = 'rgba(0, 243, 255, 0.18)';
    ctx.lineWidth = 1.5;
    ctx.fillStyle = 'rgba(0, 243, 255, 0.02)';
    WORLD_VECTORS.forEach(polygon => {
        ctx.beginPath();
        polygon.forEach((pt, idx) => {
            const pos = gpsToPixels(pt[0], pt[1]);
            if (idx === 0) ctx.moveTo(pos.x, pos.y);
            else ctx.lineTo(pos.x, pos.y);
        });
        ctx.stroke();
        ctx.fill();
    });

    // 3. Draw earthquake markers on map
    earthquakeMarkers.forEach(eq => {
        const pos = gpsToPixels(eq.lon, eq.lat);
        const radius = Math.max(3, eq.mag * 2.5);
        const isMajor = eq.mag >= 6.0;
        const color = isMajor ? 'rgba(255, 59, 48,' : 'rgba(255, 149, 0,';
        
        // Ripple ring
        ctx.strokeStyle = `${color}0.4)`;
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.arc(pos.x, pos.y, radius + 4, 0, Math.PI * 2);
        ctx.stroke();
        
        // Core dot
        ctx.fillStyle = `${color}0.9)`;
        ctx.shadowColor = `${color}0.8)`;
        ctx.shadowBlur = 8;
        ctx.beginPath();
        ctx.arc(pos.x, pos.y, radius, 0, Math.PI * 2);
        ctx.fill();
        ctx.shadowBlur = 0;
        
        // Magnitude label
        if (eq.mag >= 5.0) {
            ctx.fillStyle = 'rgba(255,255,255,0.7)';
            ctx.font = '8px "Share Tech Mono"';
            ctx.fillText(`M${eq.mag.toFixed(1)}`, pos.x + radius + 2, pos.y + 3);
        }
    });

    // 4. Draw ISS orbital history path
    if (orbitalHistory.length > 1) {
        ctx.strokeStyle = 'var(--neon-blue)';
        ctx.lineWidth = 2;
        ctx.setLineDash([5, 5]);
        ctx.beginPath();
        orbitalHistory.forEach((pt, idx) => {
            const pos = gpsToPixels(pt.lon, pt.lat);
            if (idx === 0) ctx.moveTo(pos.x, pos.y);
            else ctx.lineTo(pos.x, pos.y);
        });
        ctx.stroke();
        ctx.setLineDash([]);
    }

    // 5. Draw ISS tracker + radar sweep
    const target = gpsToPixels(issPos.lon, issPos.lat);
    ctx.save();
    ctx.translate(target.x, target.y);
    ctx.rotate(mapSweepAngle);
    const grad = ctx.createConicGradient(0, 0, 0);
    grad.addColorStop(0, 'rgba(0, 243, 255, 0.2)');
    grad.addColorStop(0.2, 'rgba(0, 243, 255, 0.02)');
    grad.addColorStop(1, 'transparent');
    ctx.fillStyle = grad;
    ctx.beginPath();
    ctx.arc(0, 0, 60, 0, Math.PI * 2);
    ctx.fill();
    ctx.restore();

    ctx.strokeStyle = 'rgba(0, 243, 255, 0.25)';
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.arc(target.x, target.y, 45, 0, Math.PI * 2);
    ctx.stroke();

    // Crosshair
    ctx.strokeStyle = 'var(--neon-blue)';
    ctx.lineWidth = 1.5;
    const len = 6, dist = 8;
    ctx.beginPath();
    ctx.moveTo(target.x - dist, target.y - dist + len); ctx.lineTo(target.x - dist, target.y - dist); ctx.lineTo(target.x - dist + len, target.y - dist);
    ctx.moveTo(target.x + dist, target.y - dist + len); ctx.lineTo(target.x + dist, target.y - dist); ctx.lineTo(target.x + dist - len, target.y - dist);
    ctx.moveTo(target.x - dist, target.y + dist - len); ctx.lineTo(target.x - dist, target.y + dist); ctx.lineTo(target.x - dist + len, target.y + dist);
    ctx.moveTo(target.x + dist, target.y + dist - len); ctx.lineTo(target.x + dist, target.y + dist); ctx.lineTo(target.x + dist - len, target.y + dist);
    ctx.stroke();

    ctx.fillStyle = 'var(--neon-blue)';
    ctx.shadowColor = 'var(--neon-blue)';
    ctx.shadowBlur = 10;
    ctx.beginPath();
    ctx.arc(target.x, target.y, 4, 0, Math.PI * 2);
    ctx.fill();
    ctx.shadowBlur = 0;
    ctx.fillStyle = 'rgba(0, 243, 255, 0.9)';
    ctx.font = '10px "Share Tech Mono"';
    ctx.fillText("TGT: ISS (ZARYA)", target.x + 12, target.y - 4);
    ctx.fillStyle = 'rgba(255, 255, 255, 0.5)';
    ctx.fillText(`ALT: ${Math.round(issPos.alt || 420)}km | VEL: ${Math.round(issPos.vel || 27600)}km/h`, target.x + 12, target.y + 6);

    mapSweepAngle += 0.02;
    requestAnimationFrame(drawOrbitMap);
}

// ==============================
// LOCAL DATA UI UPDATE
// ==============================
function updateLocalDataUI(data) {
    if (!data) return;

    // ISS Telemetry
    if (data.iss && data.iss.latitude !== undefined) {
        const iss = data.iss;
        issPos.lat = iss.latitude;
        issPos.lon = iss.longitude;
        issPos.alt = iss.altitude;
        issPos.vel = iss.velocity;
        if (orbitalHistory.length === 0 ||
            Math.abs(orbitalHistory[orbitalHistory.length - 1].lon - iss.longitude) > 0.5) {
            orbitalHistory.push({ lat: iss.latitude, lon: iss.longitude });
            if (orbitalHistory.length > 50) orbitalHistory.shift();
        }
        document.getElementById('lat-lbl').innerText = `${iss.latitude.toFixed(4)}°`;
        document.getElementById('lon-lbl').innerText = `${iss.longitude.toFixed(4)}°`;
        document.getElementById('alt-lbl').innerText = `${iss.altitude.toFixed(2)} km`;
        document.getElementById('vel-lbl').innerText = `${Math.round(iss.velocity).toLocaleString()} km/h`;
        document.getElementById('phase-lbl').innerText = (iss.visibility || "daylight").toUpperCase();
        document.getElementById('solar-lat-lbl').innerText = `${(iss.solar_lat || 0).toFixed(2)}°`;
        document.getElementById('solar-lon-lbl').innerText = `${(iss.solar_lon || 0).toFixed(2)}°`;
    }

    // Crew Registry — use DocumentFragment to batch DOM writes
    if (data.astros && data.astros.people) {
        const list = document.getElementById('crew-list');
        const frag = document.createDocumentFragment();
        data.astros.people.forEach(p => {
            const item = document.createElement('div');
            item.className = 'crew-item';
            item.innerHTML = `<span class="crew-name">${p.name}</span><span class="crew-craft">${p.craft.toUpperCase()}</span>`;
            frag.appendChild(item);
        });
        list.innerHTML = '';
        list.appendChild(frag);
    }

    // Space Weather / NOAA
    if (data.space_weather) {
        const sw = data.space_weather;
        if (sw.wind) {
            const windEntry = Array.isArray(sw.wind) ? sw.wind[sw.wind.length - 1] : sw.wind;
            const spd = windEntry.proton_speed || windEntry.wind_speed || '--';
            document.getElementById('wind-speed-lbl').innerText = `${spd} km/s`;
        }
        if (sw.scales) {
            const cur = sw.scales['0'] || {};
            const gScale = cur.G ? `G${cur.G.Scale} - ${cur.G.Text || 'NORMAL'}` : 'G0 - NORMAL';
            const sScale = cur.S ? `S${cur.S.Scale} - ${cur.S.Text || 'NORMAL'}` : 'S0 - NORMAL';
            const rScale = cur.R ? `R${cur.R.Scale} - ${cur.R.Text || 'NORMAL'}` : 'R0 - NORMAL';
            const gEl = document.getElementById('geomagnetic-lbl');
            const sEl = document.getElementById('radiation-lbl');
            const rEl = document.getElementById('radio-lbl');
            gEl.innerText = gScale.toUpperCase();
            sEl.innerText = sScale.toUpperCase();
            rEl.innerText = rScale.toUpperCase();
            // Alert coloring
            [gEl, sEl, rEl].forEach(el => {
                if (el.innerText.includes('G0') || el.innerText.includes('S0') || el.innerText.includes('R0') || el.innerText.includes('NONE') || el.innerText.includes('NORMAL')) {
                    el.classList.remove('alert');
                } else {
                    el.classList.add('alert');
                }
            });
        }
    }

    // NASA APOD
    if (data.nasa) {
        const apod = data.nasa;
        const titleEl = document.getElementById('apod-title');
        const descEl = document.getElementById('apod-desc');
        const cpEl = document.getElementById('apod-copyright');
        if (titleEl) titleEl.innerText = apod.title || 'N/A';
        if (descEl) descEl.innerText = apod.explanation || '';
        if (cpEl) cpEl.innerText = apod.copyright ? `© ${apod.copyright}` : '';
    }

    // Earthquakes
    if (data.earthquakes && data.earthquakes.features) {
        renderEarthquakes(data.earthquakes.features);
    }

    // Crypto / Finance prices
    if (data.crypto) {
        updateCryptoTicker(data.crypto);
    }

    // Maritime
    if (data.maritime) {
        updateMaritime(data.maritime);
    }
}

// ==============================
// EARTHQUAKE RENDERING
// ==============================
function renderEarthquakes(features) {
    const list = document.getElementById('quake-list');
    const badge = document.getElementById('quake-alert-badge');
    
    // Sort by magnitude descending, take top 10
    const sorted = features
        .filter(f => f.properties.mag >= 4.0)
        .sort((a, b) => b.properties.mag - a.properties.mag)
        .slice(0, 10);
    
    const hasMajor = sorted.some(f => f.properties.mag >= 6.0);
    if (badge) badge.style.display = hasMajor ? 'flex' : 'none';
    
    // Update canvas earthquake markers (top 8 by mag)
    earthquakeMarkers = sorted.slice(0, 8).map(f => ({
        lat: f.geometry.coordinates[1],
        lon: f.geometry.coordinates[0],
        mag: f.properties.mag
    }));
    
    list.innerHTML = '';
    if (sorted.length === 0) {
        list.innerHTML = '<div class="quake-item empty">NO SIGNIFICANT EVENTS</div>';
        return;
    }
    const frag = document.createDocumentFragment();
    
    sorted.forEach(f => {
        const p = f.properties;
        const mag = p.mag.toFixed(1);
        const isMajor = p.mag >= 6.0;
        const place = p.place || 'Unknown Region';
        const depth = f.geometry.coordinates[2].toFixed(0);
        const item = document.createElement('div');
        item.className = 'quake-item';
        item.innerHTML = `
            <span class="quake-mag${isMajor ? ' major' : ''}">M${mag}</span>
            <span class="quake-place">${place}</span>
            <span class="quake-depth">DEPTH: ${depth} km</span>
        `;
        frag.appendChild(item);
    });
    list.innerHTML = '';
    list.appendChild(frag);
}

// ==============================
// CRYPTO TICKER UPDATE
// ==============================
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
        el.innerText = numVal > 1000 ? `$${numVal.toLocaleString('en-US', {maximumFractionDigits: 0})}` :
                       numVal > 1   ? `$${numVal.toFixed(2)}` : `$${numVal.toFixed(4)}`;
        el.className = 'tick-price' + (numVal > prev ? ' up' : numVal < prev ? ' down' : '');
    });
}

// ==============================
// MARITIME STATUS UPDATE
// ==============================
function updateMaritime(maritime) {
    if (maritime.vessel_count !== undefined) {
        document.getElementById('vessel-count-lbl').innerText = `${maritime.vessel_count.toLocaleString()} ACTIVE`;
    }
    if (maritime.piracy_zone) {
        document.getElementById('piracy-lbl').innerText = maritime.piracy_zone;
    }
    if (maritime.suez_status) {
        const el = document.getElementById('suez-lbl');
        el.innerText = maritime.suez_status;
        el.className = 'maritime-val' + (maritime.suez_status.toUpperCase().includes('CLOSED') ? ' alert' : ' text-neon');
    }
    if (maritime.malacca_status) {
        const el = document.getElementById('malacca-lbl');
        el.innerText = maritime.malacca_status;
        el.className = 'maritime-val' + (maritime.malacca_status.toUpperCase().includes('ALERT') ? ' alert' : ' text-neon');
    }
}

// ==============================
// DATA RELOAD
// ==============================
function reloadSpaceScript() {
    const oldScript = document.getElementById('data-script');
    if (oldScript) oldScript.remove();
    const script = document.createElement('script');
    script.id = 'data-script';
    script.src = `space_data.js?t=${Date.now()}`;
    script.onload = () => {
        if (window.space_data) updateLocalDataUI(window.space_data);
    };
    document.head.appendChild(script);
}

// ==============================
// LIVE TIME DISPLAY
// ==============================
function updateTimeDisplay() {
    const now = new Date();
    const utcStr = now.toUTCString().replace('GMT', 'UTC');
    const el = document.getElementById('timezone-lbl');
    if (el) el.innerText = now.toISOString().slice(0,19).replace('T', ' ') + ' UTC';
}
setInterval(updateTimeDisplay, 1000);
updateTimeDisplay();

// Initial Triggers
reloadSpaceScript();
drawOrbitMap();
setInterval(reloadSpaceScript, 3000);
