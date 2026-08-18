// ==============================
// ORBITAL TELEMETRY CORE — JS
// Handles: ISS, APOD, Crew, Space Weather, Earthquakes, Maritime, Crypto
// ==============================

// Canvas setup
const quakeCanvas = document.getElementById('quake-canvas');
const quakeCtx = quakeCanvas ? quakeCanvas.getContext('2d') : null;
const issCanvas = document.getElementById('iss-canvas');
const issCtx = issCanvas ? issCanvas.getContext('2d') : null;

let issPos = { lat: 0, lon: 0 };
let orbitalHistory = [];
let mapSweepAngle = 0;
let earthquakeMarkers = []; // Store for canvas drawing
let satelliteTles = {}; // Raw TLEs from backend
let propagatedSatellites = []; // Real-time coordinates
let satListThrottle = 0;

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

function resizeCanvases() {
    if (quakeCanvas && quakeCanvas.parentElement) {
        const rect = quakeCanvas.parentElement.getBoundingClientRect();
        quakeCanvas.width = Math.max(1, Math.floor(rect.width));
        quakeCanvas.height = Math.max(1, Math.floor(rect.height));
    }
    if (issCanvas && issCanvas.parentElement) {
        const rect = issCanvas.parentElement.getBoundingClientRect();
        issCanvas.width = Math.max(1, Math.floor(rect.width));
        issCanvas.height = Math.max(1, Math.floor(rect.height));
    }
}
window.addEventListener('resize', resizeCanvases, { passive: true });
if (quakeCanvas?.parentElement) new ResizeObserver(resizeCanvases).observe(quakeCanvas.parentElement);
if (issCanvas?.parentElement) new ResizeObserver(resizeCanvases).observe(issCanvas.parentElement);
resizeCanvases();

function gpsToPixels(lon, lat, canvas) {
    if (!canvas) return { x: 0, y: 0 };
    const margin = 20;
    const px = ((lon + 180) / 360) * (canvas.width - margin * 2) + margin;
    const py = (1.0 - (lat + 90) / 180) * (canvas.height - margin * 2) + margin;
    return { x: px, y: py };
}

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

function drawGridAndAxes(ctx, canvas) {
    ctx.strokeStyle = 'rgba(0, 243, 255, 0.04)';
    ctx.lineWidth = 1;
    
    // Draw longitude lines (-180 to 180, step 30)
    for (let lon = -180; lon <= 180; lon += 30) {
        const p1 = gpsToPixels(lon, -90, canvas);
        const p2 = gpsToPixels(lon, 90, canvas);
        ctx.beginPath();
        ctx.moveTo(p1.x, p1.y);
        ctx.lineTo(p2.x, p2.y);
        ctx.stroke();
        
        // Label longitude at bottom
        if (lon % 60 === 0) {
            ctx.fillStyle = 'rgba(0, 243, 255, 0.35)';
            ctx.font = '8px "Share Tech Mono"';
            ctx.textAlign = 'center';
            const label = lon === 0 ? '0°' : lon > 0 ? `${lon}°E` : `${Math.abs(lon)}°W`;
            ctx.fillText(label, p1.x, canvas.height - 4);
        }
    }
    
    // Draw latitude lines (-90 to 90, step 30)
    for (let lat = -90; lat <= 90; lat += 30) {
        const p1 = gpsToPixels(-180, lat, canvas);
        const p2 = gpsToPixels(180, lat, canvas);
        ctx.beginPath();
        ctx.moveTo(p1.x, p1.y);
        ctx.lineTo(p2.x, p2.y);
        ctx.stroke();
        
        // Label latitude along left edge
        if (lat % 30 === 0 && lat !== -90 && lat !== 90) {
            ctx.fillStyle = 'rgba(0, 243, 255, 0.35)';
            ctx.font = '8px "Share Tech Mono"';
            ctx.textAlign = 'left';
            const label = lat === 0 ? '0°' : lat > 0 ? `${lat}°N` : `${Math.abs(lat)}°S`;
            ctx.fillText(label, 4, p1.y - 2);
        }
    }
}

function drawQuakeMap() {
    if (!quakeCanvas || !quakeCtx) return;
    quakeCtx.clearRect(0, 0, quakeCanvas.width, quakeCanvas.height);

    drawGridAndAxes(quakeCtx, quakeCanvas);
    drawWorldMap(quakeCtx, quakeCanvas);

    // Draw earthquake markers on map
    earthquakeMarkers.forEach(eq => {
        const pos = gpsToPixels(eq.lon, eq.lat, quakeCanvas);
        const radius = Math.max(3, eq.mag * 2.5);
        const isMajor = eq.mag >= 6.0;
        const color = isMajor ? 'rgba(255, 59, 48,' : 'rgba(255, 149, 0,';
        
        // Ripple ring
        quakeCtx.strokeStyle = `${color}0.4)`;
        quakeCtx.lineWidth = 1;
        quakeCtx.beginPath();
        quakeCtx.arc(pos.x, pos.y, radius + 4, 0, Math.PI * 2);
        quakeCtx.stroke();
        
        // Core dot
        quakeCtx.fillStyle = `${color}0.9)`;
        quakeCtx.shadowColor = `${color}0.8)`;
        quakeCtx.shadowBlur = 8;
        quakeCtx.beginPath();
        quakeCtx.arc(pos.x, pos.y, radius, 0, Math.PI * 2);
        quakeCtx.fill();
        quakeCtx.shadowBlur = 0;
        
        // Magnitude label
        if (eq.mag >= 5.0) {
            quakeCtx.fillStyle = 'rgba(255,255,255,0.7)';
            quakeCtx.font = '8px "Share Tech Mono"';
            quakeCtx.fillText(`M${eq.mag.toFixed(1)}`, pos.x + radius + 2, pos.y + 3);
        }
    });

    requestAnimationFrame(drawQuakeMap);
}

function propagateSatellites() {
    if (typeof satellite === 'undefined') return;
    propagatedSatellites = [];
    const now = new Date();
    
    Object.entries(satelliteTles).forEach(([catnr, satData]) => {
        try {
            const satrec = satellite.twoline2satrec(satData.line1, satData.line2);
            const positionAndVelocity = satellite.propagate(satrec, now);
            const positionEci = positionAndVelocity.position;
            
            if (positionEci) {
                const gmst = satellite.gstime(now);
                const positionGd = satellite.eciToGeodetic(positionEci, gmst);
                
                const lonDeg = satellite.degreesLong(positionGd.longitude);
                const latDeg = satellite.degreesLat(positionGd.latitude);
                const altKm = positionGd.height;
                
                let velocityKmh = 27600; // fallback
                if (positionAndVelocity.velocity) {
                    const vel = positionAndVelocity.velocity;
                    const velKms = Math.sqrt(vel.x*vel.x + vel.y*vel.y + vel.z*vel.z);
                    velocityKmh = velKms * 3600;
                }
                
                propagatedSatellites.push({
                    catnr: catnr,
                    name: satData.name,
                    lat: latDeg,
                    lon: lonDeg,
                    alt: altKm,
                    vel: velocityKmh
                });
            }
        } catch (e) {
            console.error("Propagation error for satellite", catnr, e);
        }
    });
}

function renderSatelliteList() {
    const list = document.getElementById('satellite-list');
    if (!list) return;
    
    list.innerHTML = '';
    const frag = document.createDocumentFragment();
    
    propagatedSatellites.forEach(sat => {
        const item = document.createElement('div');
        item.className = 'sat-item';
        
        let color = 'var(--neon-blue)';
        if (sat.catnr === '20580') color = '#bf5af2';
        else if (sat.catnr === '48274') color = '#ffd60a';
        else if (sat.catnr === '33591') color = '#30d158';
        
        item.innerHTML = `
            <div class="sat-item-header" style="border-left: 2px solid ${color}; padding-left: 6px; display: flex; justify-content: space-between; align-items: center;">
                <span class="sat-name" style="color: ${color}; font-weight: bold; font-size: 9.5px;">${sat.name}</span>
                <span class="sat-badge" style="font-size: 7px; color: ${color}; border: 1px solid ${color}; padding: 1px 3px; border-radius: 2px;">ACTIVE</span>
            </div>
            <div class="sat-item-details" style="font-family: var(--font-mono); font-size: 8px; color: rgba(255,255,255,0.6); margin-top: 4px; display: grid; grid-template-columns: 1fr 1fr; gap: 4px;">
                <span>LAT: ${sat.lat.toFixed(2)}°</span>
                <span>LON: ${sat.lon.toFixed(2)}°</span>
                <span>ALT: ${Math.round(sat.alt)} km</span>
                <span>VEL: ${Math.round(sat.vel).toLocaleString()} km/h</span>
            </div>
        `;
        frag.appendChild(item);
    });
    
    if (propagatedSatellites.length === 0) {
        list.innerHTML = '<div class="sat-item empty">TRACKING ORBITAL PATHS...</div>';
    } else {
        list.appendChild(frag);
    }
}

function drawIssMap() {
    if (!issCanvas || !issCtx) return;
    issCtx.clearRect(0, 0, issCanvas.width, issCanvas.height);

    drawGridAndAxes(issCtx, issCanvas);
    drawWorldMap(issCtx, issCanvas);

    // Calculate real-time coordinates
    propagateSatellites();

    // Throttle DOM list updates to save CPU cycles
    satListThrottle++;
    if (satListThrottle >= 30) {
        renderSatelliteList();
        satListThrottle = 0;
    }

    // Draw orbital history for ISS
    const issProp = propagatedSatellites.find(s => s.catnr === '25544');
    if (issProp) {
        issPos.lat = issProp.lat;
        issPos.lon = issProp.lon;
        issPos.alt = issProp.alt;
        issPos.vel = issProp.vel;
        if (orbitalHistory.length === 0 ||
            Math.abs(orbitalHistory[orbitalHistory.length - 1].lon - issProp.lon) > 0.5) {
            orbitalHistory.push({ lat: issProp.lat, lon: issProp.lon });
            if (orbitalHistory.length > 50) orbitalHistory.shift();
        }
    }

    if (orbitalHistory.length > 1) {
        issCtx.strokeStyle = 'var(--neon-blue)';
        issCtx.lineWidth = 1.5;
        issCtx.setLineDash([4, 4]);
        issCtx.beginPath();
        orbitalHistory.forEach((pt, idx) => {
            const pos = gpsToPixels(pt.lon, pt.lat, issCanvas);
            if (idx === 0) issCtx.moveTo(pos.x, pos.y);
            else issCtx.lineTo(pos.x, pos.y);
        });
        issCtx.stroke();
        issCtx.setLineDash([]);
    }

    // Draw all propagated satellites on canvas
    propagatedSatellites.forEach(sat => {
        const target = gpsToPixels(sat.lon, sat.lat, issCanvas);
        
        let color = 'var(--neon-blue)';
        if (sat.catnr === '20580') color = '#bf5af2';
        else if (sat.catnr === '48274') color = '#ffd60a';
        else if (sat.catnr === '33591') color = '#30d158';

        // Custom crosshair/radar for ISS only
        if (sat.catnr === '25544') {
            issCtx.save();
            issCtx.translate(target.x, target.y);
            issCtx.rotate(mapSweepAngle);
            const grad = issCtx.createConicGradient(0, 0, 0);
            grad.addColorStop(0, 'rgba(0, 243, 255, 0.15)');
            grad.addColorStop(0.2, 'rgba(0, 243, 255, 0.02)');
            grad.addColorStop(1, 'transparent');
            issCtx.fillStyle = grad;
            issCtx.beginPath();
            issCtx.arc(0, 0, 45, 0, Math.PI * 2);
            issCtx.fill();
            issCtx.restore();

            issCtx.strokeStyle = 'rgba(0, 243, 255, 0.2)';
            issCtx.lineWidth = 1;
            issCtx.beginPath();
            issCtx.arc(target.x, target.y, 30, 0, Math.PI * 2);
            issCtx.stroke();

            // Crosshair
            issCtx.strokeStyle = color;
            issCtx.lineWidth = 1.2;
            const len = 4, dist = 5;
            issCtx.beginPath();
            issCtx.moveTo(target.x - dist, target.y - dist + len); issCtx.lineTo(target.x - dist, target.y - dist); issCtx.lineTo(target.x - dist + len, target.y - dist);
            issCtx.moveTo(target.x + dist, target.y - dist + len); issCtx.lineTo(target.x + dist, target.y - dist); issCtx.lineTo(target.x + dist - len, target.y - dist);
            issCtx.moveTo(target.x - dist, target.y + dist - len); issCtx.lineTo(target.x - dist, target.y + dist); issCtx.lineTo(target.x - dist + len, target.y + dist);
            issCtx.moveTo(target.x + dist, target.y + dist - len); issCtx.lineTo(target.x + dist, target.y + dist); issCtx.lineTo(target.x + dist - len, target.y + dist);
            issCtx.stroke();
        }

        // Target core dot
        issCtx.fillStyle = color;
        issCtx.shadowColor = color;
        issCtx.shadowBlur = 6;
        issCtx.beginPath();
        issCtx.arc(target.x, target.y, 4, 0, Math.PI * 2);
        issCtx.fill();
        issCtx.shadowBlur = 0;

        // Label name
        issCtx.fillStyle = 'rgba(255, 255, 255, 0.85)';
        issCtx.font = '8px "Share Tech Mono"';
        issCtx.fillText(sat.name, target.x + 8, target.y - 1);
    });

    mapSweepAngle += 0.02;
    requestAnimationFrame(drawIssMap);
}

// ==============================
// LOCAL DATA UI UPDATE
// ==============================
function updateLocalDataUI(data) {
    if (!data) return;

    // TLE Data Update
    if (data.tle) {
        satelliteTles = data.tle;
    }

    // ISS Telemetry metadata
    if (data.iss && data.iss.latitude !== undefined) {
        const iss = data.iss;
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
    
    // Sort by time descending (most recent first), take top 10
    const sorted = features
        .filter(f => f.properties.mag >= 4.0)
        .sort((a, b) => b.properties.time - a.properties.time)
        .slice(0, 10);
    
    const hasMajor = sorted.some(f => f.properties.mag >= 6.0);
    if (badge) badge.style.display = hasMajor ? 'flex' : 'none';
    
    // Update canvas earthquake markers (all 10 from the sorted list)
    earthquakeMarkers = sorted.map(f => ({
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
        
        // Format API epoch time (milliseconds) to readable UTC string
        const dateObj = new Date(p.time);
        const mm = String(dateObj.getUTCMonth() + 1).padStart(2, '0');
        const dd = String(dateObj.getUTCDate()).padStart(2, '0');
        const hh = String(dateObj.getUTCHours()).padStart(2, '0');
        const min = String(dateObj.getUTCMinutes()).padStart(2, '0');
        const timeStr = `${mm}/${dd} ${hh}:${min} UTC`;

        const item = document.createElement('div');
        item.className = 'quake-item';
        item.innerHTML = `
            <span class="quake-mag${isMajor ? ' major' : ''}">M${mag}</span>
            <span class="quake-place">${place}</span>
            <span class="quake-depth">DEPTH: ${depth} km | ${timeStr}</span>
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
drawQuakeMap();
drawIssMap();
setInterval(reloadSpaceScript, 3000);
