/* ==========================================================================
   Sentinel AI - Frontend JS Dashboard Logic
   ========================================================================== */

document.addEventListener('DOMContentLoaded', () => {
    // ----------------------------------------------------
    // Element Selectors
    // ----------------------------------------------------
    const video = document.getElementById('webcam');
    const canvas = document.getElementById('annotated-canvas');
    const ctx = canvas.getContext('2d');
    const placeholder = document.getElementById('canvas-placeholder');
    const systemToggleBtn = document.getElementById('system-toggle-btn');
    const resetBtn = document.getElementById('reset-btn');
    const saveSettingsBtn = document.getElementById('save-settings-btn');
    const clearLogsBtn = document.getElementById('clear-logs-btn');
    
    // Sliders
    const earSlider = document.getElementById('ear-thresh-slider');
    const marSlider = document.getElementById('mar-thresh-slider');
    const earThreshVal = document.getElementById('ear-thresh-val');
    const marThreshVal = document.getElementById('mar-thresh-val');
    
    // Audio toggles
    const soundToggle = document.getElementById('sound-alert-toggle');
    const voiceToggle = document.getElementById('voice-alert-toggle');
    
    // Header Info
    const connDot = document.getElementById('connection-status-dot');
    const connText = document.getElementById('connection-status-text');
    const sessionTimerEl = document.getElementById('session-timer');
    const themeToggleBtn = document.getElementById('theme-toggle-btn');
    
    // Metrics
    const fatigueVal = document.getElementById('fatigue-score-value');
    const fatigueRing = document.getElementById('fatigue-ring');
    const fatigueStatus = document.getElementById('fatigue-status');
    const earVal = document.getElementById('ear-val');
    const earProgress = document.getElementById('ear-progress');
    const earStatus = document.getElementById('ear-status');
    const marVal = document.getElementById('mar-val');
    const marProgress = document.getElementById('mar-progress');
    const marStatus = document.getElementById('mar-status');
    const yawVal = document.getElementById('yaw-val');
    const pitchVal = document.getElementById('pitch-val');
    const rollVal = document.getElementById('roll-val');
    const poseStatus = document.getElementById('pose-status');
    const phoneVal = document.getElementById('phone-val');
    const phoneProgress = document.getElementById('phone-progress');
    const phoneStatus = document.getElementById('phone-status');
    
    // Widgets to toggle classes
    const earWidget = document.getElementById('ear-widget');
    const marWidget = document.getElementById('mar-widget');
    const poseWidget = document.getElementById('pose-widget');
    const phoneWidget = document.getElementById('phone-widget');
    
    // Alerts and Logs
    const overlayAlert = document.getElementById('overlay-alert');
    const alertTitle = document.getElementById('alert-title');
    const alertDesc = document.getElementById('alert-desc');
    const logStream = document.getElementById('log-stream');
    const systemStatusInd = document.getElementById('system-status-indicator');
    const fpsCounter = document.getElementById('fps-counter');

    // ----------------------------------------------------
    // State Variables
    // ----------------------------------------------------
    let socket = null;
    let isMonitoring = false;
    let localStream = null;
    let frameTimeout = null;
    let isProcessing = false;
    let sessionStartTime = null;
    let sessionTimerInterval = null;
    
    // Siren Auto-Mute State
    let sirenStartTime = 0;
    let isSirenMuted = false;
    
    // FPS stats
    let lastFrameTime = performance.now();
    let frameCount = 0;
    let currentFps = 0;

    // Web Audio API & Speech Synthesis
    let audioCtx = null;
    let alarmInterval = null;
    let lastSpokenTime = 0;

    // ----------------------------------------------------
    // Initialization: Chart.js Setup
    // ----------------------------------------------------
    const chartCtx = document.getElementById('realtime-chart').getContext('2d');
    const maxDataPoints = 40;
    const chartLabels = Array(maxDataPoints).fill('');
    const earDataset = Array(maxDataPoints).fill(0.25);
    const marDataset = Array(maxDataPoints).fill(0.15);
    const earThreshDataset = Array(maxDataPoints).fill(0.22);
    const marThreshDataset = Array(maxDataPoints).fill(0.50);

    const realtimeChart = new Chart(chartCtx, {
        type: 'line',
        data: {
            labels: chartLabels,
            datasets: [
                {
                    label: 'EAR (Eyes)',
                    data: earDataset,
                    borderColor: '#00f2fe',
                    backgroundColor: 'rgba(0, 242, 254, 0.05)',
                    borderWidth: 2,
                    tension: 0.3,
                    pointRadius: 0,
                    fill: true
                },
                {
                    label: 'EAR Threshold',
                    data: earThreshDataset,
                    borderColor: 'rgba(255, 77, 77, 0.6)',
                    borderWidth: 1.5,
                    borderDash: [5, 5],
                    pointRadius: 0,
                    fill: false
                },
                {
                    label: 'MAR (Mouth/Yawn)',
                    data: marDataset,
                    borderColor: '#ff9f43',
                    backgroundColor: 'rgba(255, 159, 67, 0.05)',
                    borderWidth: 2,
                    tension: 0.3,
                    pointRadius: 0,
                    fill: true
                },
                {
                    label: 'MAR Threshold',
                    data: marThreshDataset,
                    borderColor: 'rgba(255, 159, 67, 0.6)',
                    borderWidth: 1.5,
                    borderDash: [5, 5],
                    pointRadius: 0,
                    fill: false
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'top',
                    labels: {
                        color: 'rgba(255, 255, 255, 0.7)',
                        font: { size: 10, family: 'Inter' }
                    }
                }
            },
            scales: {
                x: {
                    grid: { display: false }
                },
                y: {
                    min: 0.0,
                    max: 0.8,
                    ticks: { color: 'rgba(255, 255, 255, 0.6)', font: { size: 10 } },
                    grid: { color: 'rgba(255, 255, 255, 0.05)' }
                }
            }
        }
    });

    // ----------------------------------------------------
    // Theme Switcher & Slider Bindings
    // ----------------------------------------------------
    themeToggleBtn.addEventListener('click', () => {
        const body = document.body;
        const icon = themeToggleBtn.querySelector('i');
        if (body.classList.contains('dark-mode')) {
            body.classList.remove('dark-mode');
            body.classList.add('light-mode');
            icon.className = 'fa-solid fa-sun';
            
            // Update chart settings for light mode
            realtimeChart.options.plugins.legend.labels.color = '#1f2937';
            realtimeChart.options.scales.y.ticks.color = '#4b5563';
            realtimeChart.options.scales.y.grid.color = 'rgba(0, 0, 0, 0.05)';
        } else {
            body.classList.remove('light-mode');
            body.classList.add('dark-mode');
            icon.className = 'fa-solid fa-moon';
            
            // Update chart settings for dark mode
            realtimeChart.options.plugins.legend.labels.color = 'rgba(255, 255, 255, 0.7)';
            realtimeChart.options.scales.y.ticks.color = 'rgba(255, 255, 255, 0.6)';
            realtimeChart.options.scales.y.grid.color = 'rgba(255, 255, 255, 0.05)';
        }
        realtimeChart.update();
    });

    // Slider inputs
    earSlider.addEventListener('input', (e) => {
        earThreshVal.textContent = parseFloat(e.target.value).toFixed(2);
    });

    marSlider.addEventListener('input', (e) => {
        marThreshVal.textContent = parseFloat(e.target.value).toFixed(2);
    });

    // ----------------------------------------------------
    // Helper Functions
    // ----------------------------------------------------
    function appendLog(message, type = 'info') {
        const entry = document.createElement('div');
        entry.className = `log-entry ${type}`;
        
        const timestamp = new Date().toLocaleTimeString();
        entry.innerHTML = `<span class="log-time">[${timestamp}]</span> ${message}`;
        
        logStream.appendChild(entry);
        logStream.scrollTop = logStream.scrollHeight;
    }
    
    clearLogsBtn.addEventListener('click', () => {
        logStream.innerHTML = '';
        appendLog('Logs cleared.', 'system-msg');
    });

    function setFatigueRing(percentage) {
        const radius = fatigueRing.r.baseVal.value;
        const circumference = 2 * Math.PI * radius;
        const offset = circumference - (percentage / 100) * circumference;
        fatigueRing.style.strokeDashoffset = offset;
        fatigueVal.textContent = `${percentage}%`;

        // Shift color based on severity
        if (percentage < 30) {
            fatigueRing.style.stroke = 'var(--cyan)';
            fatigueStatus.textContent = 'Focused & Safe';
            fatigueStatus.style.color = 'var(--cyan)';
        } else if (percentage < 60) {
            fatigueRing.style.stroke = 'var(--amber)';
            fatigueStatus.textContent = 'Mild Fatigue Detected';
            fatigueStatus.style.color = 'var(--amber)';
        } else {
            fatigueRing.style.stroke = 'var(--red)';
            fatigueStatus.textContent = 'CRITICAL SLEEP WARNING!';
            fatigueStatus.style.color = 'var(--red)';
        }
    }

    // ----------------------------------------------------
    // Sound Siren Alarm & Voice Warn (Web Audio API)
    // ----------------------------------------------------
    function playBeep(frequency, duration, type = 'sine', volume = 0.1) {
        if (!soundToggle.checked) return;
        try {
            if (!audioCtx) {
                audioCtx = new (window.AudioContext || window.webkitAudioContext)();
            }
            if (audioCtx.state === 'suspended') {
                audioCtx.resume();
            }
            const osc = audioCtx.createOscillator();
            const gain = audioCtx.createGain();
            
            osc.type = type;
            osc.frequency.setValueAtTime(frequency, audioCtx.currentTime);
            gain.gain.setValueAtTime(volume, audioCtx.currentTime);
            gain.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + duration);
            
            osc.connect(gain);
            gain.connect(audioCtx.destination);
            osc.start();
            osc.stop(audioCtx.currentTime + duration);
        } catch (e) {
            console.error("Audio playback error:", e);
        }
    }

    function playSiren() {
        if (!soundToggle.checked) {
            stopSiren();
            return;
        }
        
        if (alarmInterval) {
            // Check if we need to auto-mute the sound after 5-6 seconds of continuous siren
            const elapsed = Date.now() - sirenStartTime;
            if (elapsed > 5500) {
                if (!isSirenMuted) {
                    isSirenMuted = true;
                    appendLog("Siren auto-silenced after 5 seconds to prevent distraction noise.", "info");
                }
            }
            return;
        }

        sirenStartTime = Date.now();
        isSirenMuted = false;
        appendLog("ALERT: Siren sounding client-side!", "critical");
        
        alarmInterval = setInterval(() => {
            if (isSirenMuted) return; // Silent while muted, but keep running to track alert duration
            try {
                if (!audioCtx) {
                    audioCtx = new (window.AudioContext || window.webkitAudioContext)();
                }
                if (audioCtx.state === 'suspended') {
                    audioCtx.resume();
                }
                const osc = audioCtx.createOscillator();
                const gain = audioCtx.createGain();
                
                osc.type = 'sawtooth';
                // Pulsing high-low frequency siren
                osc.frequency.setValueAtTime(800, audioCtx.currentTime);
                osc.frequency.linearRampToValueAtTime(400, audioCtx.currentTime + 0.4);
                
                gain.gain.setValueAtTime(0.12, audioCtx.currentTime);
                gain.gain.exponentialRampToValueAtTime(0.01, audioCtx.currentTime + 0.4);
                
                osc.connect(gain);
                gain.connect(audioCtx.destination);
                osc.start();
                osc.stop(audioCtx.currentTime + 0.4);
            } catch (err) {
                console.error("Siren beep error:", err);
            }
        }, 450);
    }

    function stopSiren() {
        if (alarmInterval) {
            clearInterval(alarmInterval);
            alarmInterval = null;
            appendLog("Siren alarm deactivated.", "info");
        }
        sirenStartTime = 0;
        isSirenMuted = false;
    }

    function speakVoiceWarning(message) {
        if (!voiceToggle.checked) return;
        const now = Date.now();
        // Throttle speech to once every 6 seconds to avoid echo/spam
        if (now - lastSpokenTime > 6000) {
            lastSpokenTime = now;
            appendLog(`Speaking Warning: "${message}"`, "warn");
            const utterance = new SpeechSynthesisUtterance(message);
            utterance.rate = 1.0;
            utterance.pitch = 0.95;
            window.speechSynthesis.speak(utterance);
        }
    }

    // ----------------------------------------------------
    // Socket.IO Connection Setup
    // ----------------------------------------------------
    function initSocket() {
        socket = io();

        socket.on('connect', () => {
            connDot.className = 'dot blinking green-dot';
            connText.textContent = 'Server Connected';
            appendLog('WebSocket connected successfully.', 'system-msg');
        });

        socket.on('disconnect', () => {
            connDot.className = 'dot blinking red-dot';
            connText.textContent = 'Server Disconnected';
            appendLog('WebSocket disconnected.', 'critical');
            stopMonitoring();
        });

        socket.on('processed_result', (data) => {
            isProcessing = false;
            if (!isMonitoring) return;
            
            // FPS check
            const now = performance.now();
            frameCount++;
            if (now - lastFrameTime >= 1000) {
                currentFps = Math.round((frameCount * 1000) / (now - lastFrameTime));
                fpsCounter.textContent = `FPS: ${currentFps}`;
                frameCount = 0;
                lastFrameTime = now;
            }

            // Draw processed annotated frame to main canvas
            if (data.image) {
                const img = new Image();
                img.onload = () => {
                    ctx.clearRect(0, 0, canvas.width, canvas.height);
                    ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
                };
                img.src = data.image;
            }

            // Process detection statistics
            if (data.stats) {
                updateDashboardStats(data.stats);
            }
        });
    }

    // ----------------------------------------------------
    // Update Dashboard Metrics and Styles
    // ----------------------------------------------------
    let lastDrowsy = false;
    let lastYawn = false;
    let lastDistracted = false;
    let lastPhone = false;

    function updateDashboardStats(stats) {
        // EAR Update
        earVal.textContent = stats.ear.toFixed(3);
        const earPct = Math.min(100, Math.max(0, stats.ear * 250));
        earProgress.style.width = `${earPct}%`;

        // MAR Update
        marVal.textContent = stats.mar.toFixed(3);
        const marPct = Math.min(100, Math.max(0, stats.mar * 150));
        marProgress.style.width = `${marPct}%`;

        // Head Pose
        yawVal.textContent = `${stats.head_yaw.toFixed(1)}°`;
        pitchVal.textContent = `${stats.head_pitch.toFixed(1)}°`;
        rollVal.textContent = `${stats.head_roll.toFixed(1)}°`;

        // Phone
        const phoneActive = stats.phone_detected;
        phoneVal.textContent = phoneActive ? 'ALERT' : 'CLEARED';
        phoneProgress.style.width = phoneActive ? '100%' : '0%';
        phoneProgress.style.backgroundColor = phoneActive ? 'var(--red)' : 'var(--cyan)';

        // Fatigue circle
        setFatigueRing(stats.fatigue_score);

        // --- Alert Status & Visuals ---
        let alertActive = false;
        let activeStatusText = "Active & Calibrated";
        let statusClass = "status-active";

        // Eye state colors
        if (stats.ear < stats.ear_thresh) {
            earWidget.classList.add('widget-warn');
            earStatus.textContent = "Eyes Drooping";
            earStatus.style.color = "var(--amber)";
        } else {
            earWidget.classList.remove('widget-warn', 'widget-alert');
            earStatus.textContent = "Eyes Open";
            earStatus.style.color = "var(--text-secondary)";
        }

        // Drowsiness Alert
        if (stats.drowsy) {
            earWidget.classList.remove('widget-warn');
            earWidget.classList.add('widget-alert');
            earStatus.textContent = "SLEEP ALERT!";
            earStatus.style.color = "var(--red)";
            alertActive = true;
            activeStatusText = "DROWSINESS ALARM!";
            statusClass = "status-alert";
            
            if (!lastDrowsy) {
                appendLog("WARNING: Eyes closed for too long! Drowsiness detected.", "critical");
                lastDrowsy = true;
            }
            speakVoiceWarning("Wake up! Please focus on driving.");
            playSiren();
        } else {
            lastDrowsy = false;
        }

        // Yawning Alert
        if (stats.yawning) {
            marWidget.classList.add('widget-alert');
            marStatus.textContent = "YAWNING DETECTED!";
            marStatus.style.color = "var(--red)";
            
            if (!lastYawn) {
                appendLog("Warning: Excessive yawning detected.", "warn");
                lastYawn = true;
                playBeep(480, 0.15, 'sine', 0.15);
                setTimeout(() => playBeep(480, 0.15, 'sine', 0.15), 180);
            }
            // Increase fatigue but no siren for yawning alone unless it is critical
            if (!alertActive) {
                activeStatusText = "Warning: Yawning Detected";
                statusClass = "status-warn";
            }
            speakVoiceWarning("Yawning detected. You might need a rest.");
        } else {
            marWidget.classList.remove('widget-alert');
            marStatus.textContent = "Mouth Normal";
            marStatus.style.color = "var(--text-secondary)";
            lastYawn = false;
        }

        // Head pose distracted state
        const lookingAway = Math.abs(stats.head_yaw) > 20 || Math.abs(stats.head_pitch) > 15;
        if (lookingAway) {
            poseWidget.classList.add('widget-warn');
            poseStatus.textContent = "Looking Away";
            poseStatus.style.color = "var(--amber)";
        } else {
            poseWidget.classList.remove('widget-warn', 'widget-alert');
            poseStatus.textContent = "Looking Center";
            poseStatus.style.color = "var(--text-secondary)";
        }

        if (stats.distracted) {
            poseWidget.classList.remove('widget-warn');
            poseWidget.classList.add('widget-alert');
            poseStatus.textContent = "DISTRACTED ALERT!";
            poseStatus.style.color = "var(--red)";
            alertActive = true;
            if (!lastDistracted) {
                appendLog("WARNING: Driver distracted (looking away from road)!", "critical");
                lastDistracted = true;
            }
            if (!stats.drowsy) { // prioritise eye closure voice
                speakVoiceWarning("Please keep your eyes on the road.");
            }
            playSiren();
        } else {
            lastDistracted = false;
        }

        // Phone Alert
        if (stats.phone_alert) {
            phoneWidget.classList.add('widget-alert');
            phoneStatus.textContent = "PHONE IN HAND!";
            phoneStatus.style.color = "var(--red)";
            alertActive = true;
            
            if (!lastPhone) {
                appendLog("WARNING: Mobile phone usage detected!", "critical");
                lastPhone = true;
            }
            speakVoiceWarning("Warning! Do not use your phone while driving.");
            playSiren();
        } else {
            phoneWidget.classList.remove('widget-alert');
            phoneStatus.textContent = stats.phone_detected ? "Phone Present" : "No Phone Detected";
            phoneStatus.style.color = stats.phone_detected ? "var(--amber)" : "var(--text-secondary)";
            lastPhone = false;
        }

        // Turn off siren if no critical alerts are active
        if (!stats.drowsy && !stats.distracted && !stats.phone_alert) {
            stopSiren();
            window.speechSynthesis.cancel(); // Mute/cancel the voice speech immediately
        }

        // Update system status text panel
        systemStatusInd.className = `system-status-indicator ${statusClass}`;
        systemStatusInd.innerHTML = `<i class="fa-solid fa-circle-info"></i> ${activeStatusText}`;

        // Canvas overlay warning banner
        if (alertActive) {
            overlayAlert.classList.add('active');
            alertTitle.textContent = stats.status_message;
            if (stats.drowsy) {
                alertDesc.textContent = "Sustained Eye Closure: Please Open Eyes!";
            } else if (stats.phone_alert) {
                alertDesc.textContent = "Cell Phone Usage is Forbidden While Driving!";
            } else {
                alertDesc.textContent = "Keep Your Eyes Focused Straight Ahead!";
            }
        } else {
            overlayAlert.classList.remove('active');
        }

        // Update Chart.js scrolling line
        updateRealtimeChart(stats.ear, stats.ear_thresh, stats.mar, stats.mar_thresh);
    }

    function updateRealtimeChart(ear, earThresh, mar, marThresh) {
        // Shift datasets
        earDataset.shift();
        earDataset.push(ear);
        
        earThreshDataset.shift();
        earThreshDataset.push(earThresh);

        marDataset.shift();
        marDataset.push(mar);

        marThreshDataset.shift();
        marThreshDataset.push(marThresh);

        realtimeChart.update('none'); // Update without animation for rendering efficiency
    }

    // ----------------------------------------------------
    // System Controls and APIs
    // ----------------------------------------------------
    async function startMonitoring() {
        if (isMonitoring) return;

        appendLog("Initializing local camera...", "info");
        try {
            // Request user webcam
            localStream = await navigator.mediaDevices.getUserMedia({
                video: {
                    width: 640,
                    height: 480,
                    frameRate: { ideal: 12, max: 15 }
                }
            });
            
            video.srcObject = localStream;
            video.play();
            
            // Wait for video metadata to load
            video.onloadedmetadata = () => {
                isMonitoring = true;
                placeholder.style.display = 'none';
                canvas.style.display = 'block';
                
                // Toggle Button styling
                systemToggleBtn.innerHTML = '<i class="fa-solid fa-stop"></i> Stop Monitoring';
                systemToggleBtn.className = 'btn btn-primary btn-block running';
                
                appendLog("Camera started. Capturing frames...", "success");

                // Start backend monitoring session via Flask POST
                fetch('/api/control', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ action: 'start' })
                });

                // Start Frame Loop
                isProcessing = false;
                sendNextFrame();
                
                // Session timer
                sessionStartTime = Date.now();
                sessionTimerInterval = setInterval(updateSessionTimer, 1000);
            };
        } catch (err) {
            appendLog(`Camera access denied or failed: ${err.message}`, "critical");
            console.error(err);
        }
    }

    function stopMonitoring() {
        if (!isMonitoring) return;

        isMonitoring = false;
        
        // Stop camera tracks
        if (localStream) {
            localStream.getTracks().forEach(track => track.stop());
            localStream = null;
        }

        // Stop timers
        if (frameTimeout) {
            cancelAnimationFrame(frameTimeout);
            clearTimeout(frameTimeout);
            frameTimeout = null;
        }
        isProcessing = false;
        if (sessionTimerInterval) {
            clearInterval(sessionTimerInterval);
            sessionTimerInterval = null;
        }

        stopSiren();

        // Notify backend stop
        fetch('/api/control', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ action: 'stop' })
        });

        // Restore canvas placeholder UI
        canvas.style.display = 'none';
        placeholder.style.display = 'flex';
        overlayAlert.classList.remove('active');
        
        systemToggleBtn.innerHTML = '<i class="fa-solid fa-power-off"></i> Start Monitoring';
        systemToggleBtn.className = 'btn btn-primary btn-block';
        
        systemStatusInd.className = "system-status-indicator";
        systemStatusInd.innerHTML = '<i class="fa-solid fa-circle-info"></i> System is Idle';
        
        appendLog("Monitoring stopped. Camera feed closed.", "info");
    }

    const offscreenCanvas = document.createElement('canvas');
    offscreenCanvas.width = 640;
    offscreenCanvas.height = 480;
    const offscreenCtx = offscreenCanvas.getContext('2d');

    function sendNextFrame() {
        if (!isMonitoring || !socket || !socket.connected) return;

        if (isProcessing) {
            frameTimeout = requestAnimationFrame(sendNextFrame);
            return;
        }

        isProcessing = true;

        try {
            offscreenCtx.drawImage(video, 0, 0, 640, 480);
            // Lower JPEG quality to 0.45 for speed and network performance
            const base64Data = offscreenCanvas.toDataURL('image/jpeg', 0.45);
            socket.emit('process_frame', base64Data);
        } catch (e) {
            console.error("Frame capture error:", e);
            isProcessing = false;
        }

        frameTimeout = setTimeout(() => {
            frameTimeout = requestAnimationFrame(sendNextFrame);
        }, 40);
    }

    function updateSessionTimer() {
        const diff = Date.now() - sessionStartTime;
        const secs = Math.floor((diff / 1000) % 60);
        const mins = Math.floor((diff / (1000 * 60)) % 60);
        const hours = Math.floor((diff / (1000 * 60 * 60)) % 24);
        
        const pad = (num) => String(num).padStart(2, '0');
        sessionTimerEl.textContent = `${pad(hours)}:${pad(mins)}:${pad(secs)}`;
    }

    // Toggle button bind
    systemToggleBtn.addEventListener('click', () => {
        if (isMonitoring) {
            stopMonitoring();
        } else {
            // Trigger audio context activation on user gesture
            if (!audioCtx) {
                audioCtx = new (window.AudioContext || window.webkitAudioContext)();
            }
            startMonitoring();
        }
    });

    // Reset button
    resetBtn.addEventListener('click', () => {
        appendLog("Resetting dashboard metrics...", "info");
        fetch('/api/control', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ action: 'reset' })
        }).then(() => {
            setFatigueRing(0);
            earVal.textContent = "0.00";
            marVal.textContent = "0.00";
            yawVal.textContent = "0.0°";
            pitchVal.textContent = "0.0°";
            rollVal.textContent = "0.0°";
            phoneVal.textContent = "CLEARED";
            
            earDataset.fill(0.25);
            marDataset.fill(0.15);
            realtimeChart.update();
            appendLog("Metrics and alarms reset completed.", "success");
        });
    });

    // Save Settings button
    saveSettingsBtn.addEventListener('click', () => {
        const ear = parseFloat(earSlider.value);
        const mar = parseFloat(marSlider.value);

        appendLog(`Applying settings: EAR=${ear}, MAR=${mar}`, "info");

        fetch('/api/control', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                action: 'update_settings',
                ear_thresh: ear,
                mar_thresh: mar
            })
        }).then(res => res.json()).then(data => {
            appendLog("Settings updated successfully on server.", "success");
        }).catch(err => {
            appendLog(`Settings update failed: ${err.message}`, "critical");
        });
    });

    // Clean shut down on window unload
    window.addEventListener('beforeunload', () => {
        stopMonitoring();
    });

    // Start Socket connection
    initSocket();
});
