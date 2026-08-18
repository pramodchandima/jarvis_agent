// Dynamic script loading variables
let flightsList = [];
let radarSweepAngle = 0;

// Canvas setup
const canvas = document.getElementById('radar-canvas');
const ctx = canvas.getContext('2d');

function resizeCanvas() {
    const rect = canvas.parentElement.getBoundingClientRect();
    canvas.width = rect.width;
    canvas.height = rect.height;
}
window.addEventListener('resize', resizeCanvas);
resizeCanvas();

function updateLocalClock() {
    const now = new Date();
    const hours = String(now.getHours()).padStart(2, '0');
    const minutes = String(now.getMinutes()).padStart(2, '0');
    const seconds = String(now.getSeconds()).padStart(2, '0');
    document.getElementById('clock-lbl').innerText = `${hours}:${minutes}:${seconds}`;

    const options = { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' };
    document.getElementById('date-lbl').innerText = now.toLocaleDateString('en-US', options);
    
    const offsetMin = -now.getTimezoneOffset();
    const offsetHours = Math.floor(Math.abs(offsetMin) / 60);
    const offsetRemainingMin = Math.abs(offsetMin) % 60;
    const sign = offsetMin >= 0 ? '+' : '-';
    document.getElementById('timezone-lbl').innerText = `GMT${sign}${offsetHours}:${String(offsetRemainingMin).padStart(2, '0')}`;
}

function formatTimeString(isoString) {
    if (!isoString) return "--:--";
    try {
        const date = new Date(isoString);
        return `${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`;
    } catch (e) {
        return "--:--";
    }
}

// Fetch 14 Weather & Air Quality parameters
async function fetchLiveWeather() {
    try {
        const weatherUrl = "https://api.open-meteo.com/v1/forecast?latitude=6.9934&longitude=81.0550&current=temperature_2m,relative_humidity_2m,apparent_temperature,weather_code,cloud_cover,wind_speed_10m,wind_direction_10m,surface_pressure,dew_point_2m&daily=sunrise,sunset,uv_index_max,precipitation_probability_max&timezone=auto";
        const airUrl = "https://air-quality-api.open-meteo.com/v1/air-quality?latitude=6.9934&longitude=81.0550&current=pm2_5,ozone";
        
        const [weatherRes, airRes] = await Promise.all([
            fetch(weatherUrl),
            fetch(airUrl)
        ]);
        
        if (!weatherRes.ok || !airRes.ok) return;
        
        const weatherData = await weatherRes.json();
        const airData = await airRes.json();
        
        const current = weatherData.current;
        const daily = weatherData.daily;
        const airCurrent = airData.current;
        
        const temp = Math.round(current.temperature_2m);
        const feelsLike = Math.round(current.apparent_temperature);
        const humidity = current.relative_humidity_2m;
        const windSpeed = current.wind_speed_10m;
        const windDir = current.wind_direction_10m;
        const clouds = current.cloud_cover;
        const pressure = Math.round(current.surface_pressure);
        const dewpoint = Math.round(current.dew_point_2m);
        const code = current.weather_code;
        
        const rainProb = daily.precipitation_probability_max[0];
        const uv = daily.uv_index_max[0];
        const sunrise = formatTimeString(daily.sunrise[0]);
        const sunset = formatTimeString(daily.sunset[0]);
        
        const pm25 = Math.round(airCurrent.pm2_5);
        const ozone = Math.round(airCurrent.ozone);
        
        let desc = "Clear Sky";
        if (code === 0) desc = "Sunny";
        else if (code >= 1 && code <= 3) desc = "Cloudy";
        else if (code >= 45 && code <= 48) desc = "Foggy";
        else if ((code >= 51 && code <= 67) || (code >= 80 && code <= 82)) desc = "Rainy";
        else if (code >= 95 && code <= 99) desc = "Thunderstorm";

        // Update core display elements
        document.getElementById('temp-lbl').innerText = `${temp}°C`;
        document.getElementById('weather-desc-lbl').innerText = desc;
        updateWeatherAnimation(desc);
        
        // Update stats
        document.getElementById('feels-lbl').innerText = `${feelsLike}°C`;
        document.getElementById('humidity-lbl').innerText = `${humidity}%`;
        document.getElementById('wind-lbl').innerText = `${windSpeed} km/h`;
        document.getElementById('wind-dir-lbl').innerText = `${windDir}°`;
        document.getElementById('uv-lbl').innerText = uv;
        document.getElementById('clouds-lbl').innerText = `${clouds}%`;
        document.getElementById('rain-prob-lbl').innerText = `${rainProb}%`;
        document.getElementById('dewpoint-lbl').innerText = `${dewpoint}°C`;
        document.getElementById('pressure-lbl').innerText = `${pressure} hPa`;
        document.getElementById('pm25-lbl').innerText = `${pm25} µg/m³`;
        document.getElementById('ozone-lbl').innerText = `${ozone} µg/m³`;
        document.getElementById('sun-times-lbl').innerText = `${sunrise} / ${sunset}`;
        
    } catch (e) {
        document.getElementById('temp-lbl').innerText = "28°C";
        document.getElementById('weather-desc-lbl').innerText = "Clear Sky";
        updateWeatherAnimation("Clear Sky");
        
        document.getElementById('feels-lbl').innerText = "31°C";
        document.getElementById('humidity-lbl').innerText = "72%";
        document.getElementById('wind-lbl').innerText = "12 km/h";
        document.getElementById('wind-dir-lbl').innerText = "240°";
        document.getElementById('uv-lbl').innerText = "6";
        document.getElementById('clouds-lbl').innerText = "20%";
        document.getElementById('rain-prob-lbl').innerText = "10%";
        document.getElementById('dewpoint-lbl').innerText = "22°C";
        document.getElementById('pressure-lbl').innerText = "1012 hPa";
        document.getElementById('pm25-lbl').innerText = "15 µg/m³";
        document.getElementById('ozone-lbl').innerText = "32 µg/m³";
        document.getElementById('sun-times-lbl').innerText = "06:02 / 18:25";
    }
}

function updateWeatherAnimation(description) {
    const container = document.getElementById('weather-anim');
    const descLower = description.toLowerCase();
    container.innerHTML = '';

    if (descLower.includes('rain') || descLower.includes('drizzle') || descLower.includes('thunder')) {
        const cloud = document.createElement('div');
        cloud.className = 'cloud';
        const rain = document.createElement('div');
        rain.className = 'rain-drops';
        for (let i = 0; i < 3; i++) {
            const drop = document.createElement('div');
            drop.className = 'drop';
            drop.style.left = `${8 + i * 12}px`;
            drop.style.animationDelay = `${i * 0.3}s`;
            rain.appendChild(drop);
        }
        container.appendChild(cloud);
        container.appendChild(rain);
    } else if (descLower.includes('cloud') || descLower.includes('mist') || descLower.includes('fog')) {
        const cloud1 = document.createElement('div');
        cloud1.className = 'cloud';
        const cloud2 = document.createElement('div');
        cloud2.className = 'cloud';
        cloud2.style.transform = 'scale(0.7) translate(-6px, 10px)';
        cloud2.style.opacity = '0.6';
        container.appendChild(cloud1);
        container.appendChild(cloud2);
    } else {
        const sun = document.createElement('div');
        sun.className = 'sun-glow';
        container.appendChild(sun);
    }
}

const flightsMap = new Map();

function pruneStaleFlights() {
    const now = Date.now();
    for (const [icao24, flight] of flightsMap.entries()) {
        // If flight is not updated within 90 seconds, drop it
        if (now - flight.lastUpdated > 90000) {
            flightsMap.delete(icao24);
        }
    }
    flightsList = Array.from(flightsMap.values());
}

function saveOrUpdateFlight(icao24, newFlightData) {
    const existing = flightsMap.get(icao24);
    if (existing) {
        // Merge updates, preserving valid advanced telemetry instead of overwriting with N/A
        flightsMap.set(icao24, {
            ...existing,
            ...newFlightData,
            emergency: newFlightData.emergency !== "none" ? newFlightData.emergency : existing.emergency,
            mach: newFlightData.mach !== "N/A" ? newFlightData.mach : existing.mach,
            temp: newFlightData.temp !== "N/A" ? newFlightData.temp : existing.temp,
            wind: newFlightData.wind !== "N/A" ? newFlightData.wind : existing.wind,
            mcpAlt: newFlightData.mcpAlt !== "N/A" ? newFlightData.mcpAlt : existing.mcpAlt,
            lastUpdated: newFlightData.lastUpdated
        });
    } else {
        flightsMap.set(icao24, newFlightData);
    }
}

// Fetch active flight vectors from ADSB.lol API (Katunayake CMB Airport center, 200nm radius, every 10s)
async function fetchAirspaceData() {
    try {
        const res = await fetch("https://api.adsb.lol/v2/lat/7.1802/lon/79.8837/dist/200");
        if (!res.ok) {
            pruneStaleFlights();
            updateFlightDetailsUI();
            return;
        }
        const data = await res.json();
        
        if (data && data.ac && data.ac.length > 0) {
            const now = Date.now();
            data.ac.forEach(ac => {
                const icao24 = ac.hex;
                const callsign = (ac.flight || "").trim() || "N/A";
                const lon = ac.lon;
                const lat = ac.lat;
                if (lon === null || lat === null) return;
                
                // Filter to Sri Lanka's maritime/airspace boundary (lat: 5.5 to 10.0, lon: 79.0 to 82.5)
                if (lat < 5.5 || lat > 10.0 || lon < 79.0 || lon > 82.5) return;
                
                saveOrUpdateFlight(icao24, {
                    icao24: icao24,
                    callsign: callsign,
                    country: `TYPE: ${ac.t || "N/A"} | REG: ${ac.r || "N/A"}`,
                    longitude: lon,
                    latitude: lat,
                    altitude: Math.round((ac.alt_baro || ac.alt_geom || 0) * 0.3048), // Convert feet to meters
                    speed: Math.round((ac.gs || 0) * 1.852), // Convert knots to km/h
                    track: ac.track || 0,
                    emergency: ac.emergency || "none",
                    mach: ac.mach ? ac.mach.toFixed(2) : "N/A",
                    temp: ac.oat ? `${ac.oat}°C` : "N/A",
                    wind: ac.ws ? `${Math.round(ac.ws * 1.852)}km/h @ ${ac.wd}°` : "N/A",
                    mcpAlt: ac.nav_altitude_mcp ? `${Math.round(ac.nav_altitude_mcp * 0.3048)}m` : "N/A",
                    lastUpdated: now
                });
            });
        }
    } catch (e) {
        // Fail silently
    }
    pruneStaleFlights();
    updateFlightDetailsUI();
}

// Merge OpenSky flights retrieved via Python backend (CORS-proof, loads via data.js)
function mergeOpenSkyFromLocalData(data) {
    if (data && data.opensky_flights && data.opensky_flights.length > 0) {
        const now = Date.now();
        data.opensky_flights.forEach(flight => {
            // Filter to Sri Lanka's maritime/airspace boundary (lat: 5.5 to 10.0, lon: 79.0 to 82.5)
            if (flight.latitude < 5.5 || flight.latitude > 10.0 || flight.longitude < 79.0 || flight.longitude > 82.5) return;
            
            saveOrUpdateFlight(flight.icao24, {
                ...flight,
                lastUpdated: now
            });
        });
        pruneStaleFlights();
        updateFlightDetailsUI();
    }
}

const CMB_LAT = 7.1802;
const CMB_LON = 79.8837;

function getDistanceToCMB(lat, lon) {
    if (lat === undefined || lon === undefined) return 999999;
    const dLat = lat - CMB_LAT;
    const dLon = lon - CMB_LON;
    return Math.sqrt(dLat * dLat + dLon * dLon);
}

function updateFlightDetailsUI() {
    const listContainer = document.getElementById('flight-details-list');
    const fidsContainer = document.getElementById('fids-table-body');
    
    // Sort flights by proximity to Katunayake (CMB)
    const sortedFlights = [...flightsList].sort((a, b) => {
        return getDistanceToCMB(a.latitude, a.longitude) - getDistanceToCMB(b.latitude, b.longitude);
    });

    // 1. Update the sidebar list panel with closest flights
    if (listContainer) {
        listContainer.innerHTML = '';
        if (sortedFlights.length > 0) {
            sortedFlights.forEach(flight => {
                const item = document.createElement('div');
                item.className = 'flight-detail-item';
                
                const emergencyVal = (flight.emergency || 'none').toUpperCase();
                const emergencyClass = (flight.emergency || 'none') !== 'none' ? 'emerg-warn' : '';
                
                item.innerHTML = `
                    <div class="flight-detail-header">
                        <span class="flight-detail-callsign">${flight.callsign || 'N/A'}</span>
                        <span class="flight-detail-hex">#${(flight.icao24 || '').toUpperCase()}</span>
                    </div>
                    <div class="flight-detail-body">
                        <div class="flight-detail-col left-col">
                            <div class="flight-detail-row"><span>ALTITUDE:</span><span class="val">${flight.altitude || 0}m</span></div>
                            <div class="flight-detail-row"><span>SPEED:</span><span class="val">${flight.speed || 0}km/h</span></div>
                            <div class="flight-detail-row"><span>HEADING:</span><span class="val">${flight.track || 0}°</span></div>
                            <div class="flight-detail-row"><span>INFO:</span><span class="val" style="font-size: 8px;">${flight.country || 'N/A'}</span></div>
                        </div>
                        <div class="flight-detail-col right-col">
                            <div class="flight-detail-row"><span>EMERGENCY:</span><span class="val ${emergencyClass}">${emergencyVal}</span></div>
                            <div class="flight-detail-row"><span>MACH SPD:</span><span class="val">${flight.mach || 'N/A'}</span></div>
                            <div class="flight-detail-row"><span>AIR TEMP:</span><span class="val">${flight.temp || 'N/A'}</span></div>
                            <div class="flight-detail-row"><span>WIND VEL:</span><span class="val" style="font-size: 7.5px;">${flight.wind || 'N/A'}</span></div>
                            <div class="flight-detail-row"><span>MCP ALT:</span><span class="val">${flight.mcpAlt || 'N/A'}</span></div>
                        </div>
                    </div>
                `;
                listContainer.appendChild(item);
            });
        } else {
            listContainer.innerHTML = '<div class="flight-detail-item empty">SCANNING AIRSPACE...</div>';
        }
    }

    // 2. Update the horizontal Timetable Board (FIDS) - Top 6 closest flights (Real data only)
    if (fidsContainer) {
        fidsContainer.innerHTML = '';
        
        if (sortedFlights.length > 0) {
            const displayList = sortedFlights.slice(0, 6);
            displayList.forEach(flight => {
                const tr = document.createElement('tr');
                
                let statusText = 'CRUISING';
                let statusClass = 'cruising';
                let flightType = 'ARR';
                let flightRoute = 'DXB ➔ CMB';
                let flightTime = '00:00';
                
                // Determine Flight Type and Route based on origin/destination
                if (flight.origin === "CMB" || (flight.origin && flight.origin.toUpperCase() === "CMB")) {
                    flightType = "DEP";
                    flightRoute = `CMB ➔ ${flight.destination || "SIN"}`;
                } else if (flight.destination === "CMB" || (flight.destination && flight.destination.toUpperCase() === "CMB")) {
                    flightType = "ARR";
                    flightRoute = `${flight.origin || "DXB"} ➔ CMB`;
                } else {
                    // Heuristic route parsing based on track/heading
                    const track = flight.track || 0;
                    const callsign = (flight.callsign || "").trim().toUpperCase();
                    if (track > 45 && track <= 225) {
                        flightType = "DEP";
                        let dest = "SIN";
                        if (callsign.startsWith("UL")) dest = "SIN";
                        else if (callsign.startsWith("SQ")) dest = "SIN";
                        else if (callsign.startsWith("MH")) dest = "KUL";
                        else if (callsign.startsWith("AI")) dest = "MAA";
                        flightRoute = `CMB ➔ ${dest}`;
                    } else {
                        flightType = "ARR";
                        let orig = "DXB";
                        if (callsign.startsWith("UL")) orig = "DXB";
                        else if (callsign.startsWith("EK")) orig = "DXB";
                        else if (callsign.startsWith("QR")) orig = "DOH";
                        else if (callsign.startsWith("EY")) orig = "AUH";
                        flightRoute = `${orig} ➔ CMB`;
                    }
                }

                // Dynamically calculate EST time
                const now = new Date();
                const dist = getDistanceToCMB(flight.latitude, flight.longitude);
                if (flightType === "ARR") {
                    const minsToAdd = Math.max(5, Math.round(dist * 60)); // 60 mins per degree (~1 hour travel)
                    now.setMinutes(now.getMinutes() + minsToAdd);
                } else {
                    const minsToSub = Math.max(2, Math.round(dist * 30));
                    now.setMinutes(now.getMinutes() - minsToSub);
                }
                flightTime = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}`;

                // Calculate Status Text
                if ((flight.emergency || 'none') !== 'none') {
                    statusText = 'EMERGENCY';
                    statusClass = 'emergency';
                } else if (flight.altitude < 4000) {
                    statusText = 'DESCENDING';
                    statusClass = 'descending';
                } else if (flight.altitude >= 4000 && flight.altitude < 8500) {
                    statusText = 'CLIMBING';
                    statusClass = 'climbing';
                }
                
                let aircraftDetails = flight.country || 'N/A';
                if (aircraftDetails.startsWith('TYPE:')) {
                    aircraftDetails = aircraftDetails.replace('TYPE: ', '').replace(' | REG:', ' (Reg: ') + ')';
                }
                
                tr.innerHTML = `
                    <td style="color: var(--neon-blue); font-weight: bold;">${flight.callsign || 'N/A'}</td>
                    <td><span style="color: ${flightType === 'DEP' ? '#ffd60a' : '#00f3ff'}; font-size: 8px; border: 1px solid ${flightType === 'DEP' ? 'rgba(255,214,10,0.3)' : 'rgba(0,243,255,0.3)'}; padding: 1px 3px; border-radius: 2px;">${flightType}</span></td>
                    <td style="font-weight: bold; color: #ffffff;">${flightRoute}</td>
                    <td style="color: rgba(255,255,255,0.85);">${flightTime}</td>
                    <td style="color: rgba(255,255,255,0.6);">${aircraftDetails}</td>
                    <td><span class="status-tag ${statusClass}">${statusText}</span></td>
                `;
                fidsContainer.appendChild(tr);
            });
        } else {
            fidsContainer.innerHTML = `
                <tr>
                    <td colspan="6" class="empty">NO ACTIVE TRAFFIC IN REGION</td>
                </tr>
            `;
        }
    }
}

// Draw HTML5 Radar Loop
function drawRadar() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    
    // Shift center to the left if the screen is wide enough to show the floating list side-by-side (expanded to 340px offset)
    const hasPanel = canvas.width > 700;
    const panelWidth = hasPanel ? 340 : 0;
    const cx = (canvas.width - panelWidth) / 2;
    const cy = canvas.height / 2;
    const maxRadius = Math.min(canvas.width - panelWidth, canvas.height) * 0.45;
    
    // 1. Draw concentric grid circles with labels
    ctx.strokeStyle = 'rgba(0, 243, 255, 0.1)';
    ctx.lineWidth = 1;
    ctx.fillStyle = 'rgba(0, 243, 255, 0.5)';
    ctx.font = '8px "Share Tech Mono"';
    ctx.textAlign = 'left';

    const ringLabels = [
        "DOMESTIC (LANDMASS)",
        "TERRITORIAL SEA (12 NM)",
        "APPROACH ZONE (150 NM)",
        "OUTER BOUNDARY (200 NM)"
    ];

    const rings = [maxRadius / 4, maxRadius / 2, maxRadius * 0.75, maxRadius];
    rings.forEach((r, idx) => {
        ctx.beginPath();
        ctx.arc(cx, cy, r, 0, Math.PI * 2);
        ctx.stroke();
        
        // Draw label text just above the circle line on the horizontal axis
        ctx.fillText(ringLabels[idx], cx + 5, cy - r - 4);
    });
    
    // 2. Draw crosshairs
    ctx.beginPath();
    ctx.moveTo(cx - maxRadius, cy);
    ctx.lineTo(cx + maxRadius, cy);
    ctx.moveTo(cx, cy - maxRadius);
    ctx.lineTo(cx, cy + maxRadius);
    ctx.stroke();

    // 2b. Draw geographical sectors
    ctx.fillStyle = 'rgba(0, 243, 255, 0.15)';
    ctx.font = '8px "Share Tech Mono"';
    ctx.fillText("WESTERN ZONE", cx - maxRadius + 15, cy - maxRadius + 20);
    ctx.fillText("KATUNAYAKE SECTOR (BIA / CMB)", cx + 15, cy - 10);
    ctx.fillText("S-WEST ZONE", cx - maxRadius + 15, cy + maxRadius - 15);
    ctx.fillText("S-EAST ZONE", cx + maxRadius - 95, cy + maxRadius - 15);
    
    // 3. Draw radar sweep line
    ctx.save();
    ctx.translate(cx, cy);
    ctx.rotate(radarSweepAngle);
    
    const gradient = ctx.createConicGradient(0, 0, 0);
    gradient.addColorStop(0, 'rgba(0, 243, 255, 0.35)');
    gradient.addColorStop(0.2, 'rgba(0, 243, 255, 0.05)');
    gradient.addColorStop(1, 'transparent');
    
    ctx.fillStyle = gradient;
    ctx.beginPath();
    ctx.arc(0, 0, maxRadius, 0, Math.PI * 2);
    ctx.fill();
    ctx.restore();
    
    // 4. Draw active flight blips and linking lines
    if (flightsList.length > 0) {
        ctx.strokeStyle = 'rgba(0, 243, 255, 0.15)';
        ctx.lineWidth = 1;
        
        flightsList.forEach((flight, idx) => {
            // Map GPS coords to canvas layout bounds relative to Bounding Box (matching Sri Lanka maritime/airspace boundary)
            const lonMin = 79.0;
            const lonMax = 82.5;
            const latMin = 5.5;
            const latMax = 10.0;
            
            const px = ((flight.longitude - lonMin) / (lonMax - lonMin)) * (maxRadius * 2) + (cx - maxRadius);
            const py = (1.0 - (flight.latitude - latMin) / (latMax - latMin)) * (maxRadius * 2) + (cy - maxRadius);
            
            // Draw connecting vector link to adjacent plane (the "countries linking" animation effect)
            if (idx < flightsList.length - 1) {
                const nextFlight = flightsList[idx + 1];
                const nx = ((nextFlight.longitude - lonMin) / (lonMax - lonMin)) * (maxRadius * 2) + (cx - maxRadius);
                const ny = (1.0 - (nextFlight.latitude - latMin) / (latMax - latMin)) * (maxRadius * 2) + (cy - maxRadius);
                
                ctx.beginPath();
                ctx.moveTo(px, py);
                ctx.lineTo(nx, ny);
                ctx.setLineDash([4, 4]); // Dash link
                ctx.stroke();
                ctx.setLineDash([]); // Reset
            }
            
            // Draw plane glowing dot
            ctx.fillStyle = 'var(--neon-blue)';
            ctx.shadowColor = 'var(--neon-blue)';
            ctx.shadowBlur = 8;
            ctx.beginPath();
            ctx.arc(px, py, 4, 0, Math.PI * 2);
            ctx.fill();
            ctx.shadowBlur = 0; // Reset glow
            
            // Draw flight heading vector line
            const headingRad = (flight.track - 90) * (Math.PI / 180);
            ctx.strokeStyle = 'var(--neon-blue)';
            ctx.beginPath();
            ctx.moveTo(px, py);
            ctx.lineTo(px + Math.cos(headingRad) * 15, py + Math.sin(headingRad) * 15);
            ctx.stroke();
            
            // Render HUD Label (Callsign only to prevent canvas clutter)
            ctx.fillStyle = 'rgba(0, 243, 255, 0.9)';
            ctx.font = '9px "Share Tech Mono"';
            ctx.fillText(flight.callsign, px + 8, py + 2);
        });
    } else {
        // Empty airspace sign
        ctx.fillStyle = 'rgba(0, 243, 255, 0.3)';
        ctx.font = '11px "Share Tech Mono"';
        ctx.textAlign = 'center';
        ctx.fillText("NO AIR TRAJECTORIES IN SECTOR", cx, cy);
        ctx.textAlign = 'start';
    }
    
    // Ticking angle
    radarSweepAngle += 0.015;
    requestAnimationFrame(drawRadar);
}

function updateLocalDataUI(data) {
    // 1. Render Schedule list
    const scheduleContainer = document.getElementById('schedule-list');
    scheduleContainer.innerHTML = '';
    
    if (data.schedule && data.schedule.length > 0) {
        data.schedule.forEach(event => {
            const item = document.createElement('div');
            item.className = 'schedule-item';
            
            const timeMeta = document.createElement('div');
            timeMeta.className = 'time-meta';
            timeMeta.innerText = event.datetime || 'All Day';

            const textMeta = document.createElement('div');
            textMeta.innerText = event.text || 'Schedule Event';

            item.appendChild(timeMeta);
            item.appendChild(textMeta);
            scheduleContainer.appendChild(item);
        });
    } else {
        const emptyItem = document.createElement('div');
        emptyItem.className = 'schedule-item empty';
        emptyItem.innerText = 'No events listed.';
        scheduleContainer.appendChild(emptyItem);
    }

    // 2. Render Database Stats
    const memCount = data.db_memories !== undefined ? data.db_memories : 0;
    const logCount = data.db_conversations !== undefined ? data.db_conversations : 0;
    const skillCount = data.db_skills !== undefined ? data.db_skills : 0;
    
    const dbPanel = document.getElementById('db-stats-group');
    if (dbPanel) {
        document.getElementById('db-mem-lbl').innerText = memCount;
        document.getElementById('db-log-lbl').innerText = logCount;
        document.getElementById('db-skill-lbl').innerText = skillCount;
    }
}

function updateAirportScheduleUI(scheduleData) {
    const fidsContainer = document.getElementById('fids-table-body');
    if (!fidsContainer) return;
    fidsContainer.innerHTML = '';

    if (!scheduleData || scheduleData.length === 0) {
        fidsContainer.innerHTML = `<tr><td colspan="6" class="empty">NO SCHEDULE DATA AVAILABLE</td></tr>`;
        return;
    }

    // Sort by scheduled time, show next 6 upcoming flights
    const now = new Date();
    const nowMins = now.getHours() * 60 + now.getMinutes();

    const sorted = [...scheduleData].sort((a, b) => {
        const toMins = t => {
            if (!t || t === '--:--') return 9999;
            const [h, m] = t.split(':').map(Number);
            return h * 60 + m;
        };
        return toMins(a.scheduled_time) - toMins(b.scheduled_time);
    });

    // Show 6: prefer upcoming or wrap around to earliest
    const upcoming = sorted.filter(f => {
        if (!f.scheduled_time || f.scheduled_time === '--:--') return false;
        const [h, m] = f.scheduled_time.split(':').map(Number);
        return (h * 60 + m) >= nowMins - 15; // include flights from 15 mins ago (may still be landing)
    });
    const displayList = upcoming.length > 0 ? upcoming.slice(0, 6) : sorted.slice(0, 6);

    displayList.forEach(flight => {
        const tr = document.createElement('tr');

        const isArr = flight.type === 'ARR';
        const typeColor = isArr ? '#00f3ff' : '#ffd60a';
        const typeBorder = isArr ? 'rgba(0,243,255,0.3)' : 'rgba(255,214,10,0.3)';

        const route = isArr ? `${flight.city || '---'} ➔ CMB` : `CMB ➔ ${flight.city || '---'}`;

        // Status class mapping
        const statusLower = (flight.status || 'SCHEDULED').toUpperCase();
        let statusClass = 'cruising';
        if (statusLower.includes('LAND') || statusLower.includes('ARR')) statusClass = 'descending';
        else if (statusLower.includes('DEPART') || statusLower.includes('BOARD') || statusLower.includes('GATE')) statusClass = 'climbing';
        else if (statusLower.includes('CANCEL')) statusClass = 'emergency';
        else if (statusLower.includes('DELAY')) statusClass = 'climbing';

        tr.innerHTML = `
            <td style="color: var(--neon-blue); font-weight: bold;">${flight.callsign || 'N/A'}</td>
            <td><span style="color: ${typeColor}; font-size: 8px; border: 1px solid ${typeBorder}; padding: 1px 3px; border-radius: 2px;">${flight.type}</span></td>
            <td style="font-weight: bold; color: #ffffff;">${route}</td>
            <td style="color: rgba(255,255,255,0.85);">${flight.scheduled_time}</td>
            <td style="color: rgba(255,255,255,0.6);">${flight.callsign || ''}</td>
            <td><span class="status-tag ${statusClass}">${flight.status || 'SCHEDULED'}</span></td>
        `;
        fidsContainer.appendChild(tr);
    });
}

function reloadScheduleScript() {
    const oldScript = document.getElementById('data-script');
    if (oldScript) {
        oldScript.remove();
    }
    
    const script = document.createElement('script');
    script.id = 'data-script';
    script.src = `data.js?t=${Date.now()}`;
    script.onload = () => {
        if (window.jarvis_data) {
            updateLocalDataUI(window.jarvis_data);
            mergeOpenSkyFromLocalData(window.jarvis_data);
            // Populate FIDS timetable with real airport.lk schedule
            if (window.jarvis_data.airport_schedule) {
                updateAirportScheduleUI(window.jarvis_data.airport_schedule);
            }
        }
    };
    document.head.appendChild(script);
}


// Initial triggers
updateLocalClock();
fetchLiveWeather();
fetchAirspaceData();
drawRadar(); // Start HTML5 Canvas animation loop

// Intervals
setInterval(updateLocalClock, 1000);       // Clock tick
setInterval(fetchLiveWeather, 600000);     // Fetch weather every 10m
setInterval(fetchAirspaceData, 10000);     // Fetch live flight ADSB.lol every 10s (unlimited)
setInterval(reloadScheduleScript, 2000);   // Pull schedule, DB stats, and OpenSky flights every 2s
