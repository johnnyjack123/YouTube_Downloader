    var socket = io();
    // var cancelLink = document.getElementById('cancel-download');

// Progress
socket.on('progress', function (data) {
if (data.message) {
    document.getElementById('progress-text').textContent = data.message;
    return;
}

let percent = parseFloat(data.percent);
const fill = document.getElementById("progress-fill");
const text = document.getElementById("progress-text");

fill.style.width = percent + "%";
text.textContent = `Progress: ${data.percent} | Speed: ${data.speed} | ETA: ${data.eta}`;
});

// Cancel button
// Elemente laden
const startDownloadBtn = document.querySelector('.btn-download');
const cancelLink = document.getElementById('cancel-download');
const folderButton = document.getElementById('folder-button');
const settingsButton = document.getElementById('settings-button');

function refreshTooltips() {
    document.querySelectorAll('[data-bs-toggle="tooltip"]').forEach(el => {
        // bestehende Instanz löschen
        if (bootstrap.Tooltip.getInstance(el)) {
            bootstrap.Tooltip.getInstance(el).dispose();
        }
        // Tooltip neu aktivieren
        new bootstrap.Tooltip(el);
    });
}

// Funktion, die den UI-Status für laufende Downloads setzt
function updateDownloadUI(isDownloading) {
    if (isDownloading) {
        startDownloadBtn.value = "Add video to queue";

        folderButton.classList.add('disabled');
        folderButton.style.opacity = "0.5";
        folderButton.style.cursor = "not-allowed";
        folderButton.parentElement.setAttribute("data-bs-title", "Not available during download.");

        settingsButton.classList.add('disabled');
        settingsButton.style.opacity = "0.5";
        settingsButton.style.cursor = "not-allowed";
        settingsButton.parentElement.setAttribute("data-bs-title", "Not available during download.");
    } else {
        startDownloadBtn.value = "Start Download";

        folderButton.classList.remove('disabled');
        folderButton.style.opacity = "1";
        folderButton.style.cursor = "pointer";
        folderButton.title = "Choose download folder";
        folderButton.parentElement.setAttribute("data-bs-title", "Choose download folder");

        settingsButton.classList.remove('disabled');
        settingsButton.style.opacity = "1";
        settingsButton.style.cursor = "pointer";
        settingsButton.parentElement.setAttribute("data-bs-title", "Settings");
    }

    refreshTooltips();
}



// Socket-Event anpassen, das Cancel-Button anzeigt/versteckt
socket.on("cancel", function(state) {
    if (state === true) {
        cancelLink.style.display = "inline-block";
        updateDownloadUI(true);
    } else {
        cancelLink.style.display = "none";
        updateDownloadUI(false);
    }
});

// Falls Cancel/Resume Buttons (nach Abbruch) über Template kommen, überwache sie auch

const checkCancelResumeButtons = () => {
    const cancelBtn = document.querySelector('a[href="{{ url_for('cancel_download') }}"]');
    const resumeBtn = document.querySelector('a[href="{{ url_for('resume_download') }}"]');

    const anyVisible = (cancelBtn && cancelBtn.offsetParent !== null) ||
                       (resumeBtn && resumeBtn.offsetParent !== null);

    updateDownloadUI(anyVisible);
}

// Beobachte DOM-Änderungen in dem Bereich, wo Cancel/Resume Buttons sind

const buttonsContainer = document.querySelector('.d-flex.gap-2.mb-4');
if (buttonsContainer) {
    const observer = new MutationObserver(() => {
        checkCancelResumeButtons();
    });
    observer.observe(buttonsContainer, { childList: true, subtree: true });
    checkCancelResumeButtons(); // Initial aufrufen
}

    // Console
const consoleBox = document.getElementById("console");

const createMessage = (msg) => {
    if (Array.isArray(msg)) {
        msg.forEach(entry => addLine(entry));
    } else {
        addLine(msg);
    }
};

function addLine(data) {
    let timeStamp, message;

    // Wenn es ein Objekt ist (vom Python-emit)
    if (typeof data === "object" && data !== null) {
        timeStamp = data.time_stamp;
        message = data.message;
    } else {
        // Fallback (alte Daten ohne Zeitstempel)
        timeStamp = "";
        message = data;
    }

    const content = `
        <div class="text" title="${timeStamp}">
            <span>
                <strong class="console-text">[console]</strong>: ${message}
            </span>
        </div>
    `;
    consoleBox.innerHTML += content;

    // Autoscroll
    const consoleContainer = consoleBox.parentElement;
    consoleContainer.scrollTop = consoleContainer.scrollHeight;
}

socket.on("console", (msg) => {
    createMessage(msg);
});




    // Queue
    socket.on("queue", function(queue) {
let list = document.getElementById("queue");
list.innerHTML = "";
queue.forEach(videoName => {
    let li = document.createElement("li");

    // SVG Element erzeugen
    let svg = `
        <svg class="queue-icon" xmlns="http://www.w3.org/2000/svg"
             viewBox="0 0 24 24" fill="none"
             stroke="currentColor" stroke-width="2"
             stroke-linecap="round" stroke-linejoin="round">
            <path d="M2.5 17a24.12 24.12 0 0 1 0-10
                     2 2 0 0 1 1.4-1.4
                     49.56 49.56 0 0 1 16.2 0
                     A2 2 0 0 1 21.5 7
                     a24.12 24.12 0 0 1 0 10
                     2 2 0 0 1-1.4 1.4
                     49.55 49.55 0 0 1-16.2 0
                     A2 2 0 0 1 2.5 17"/>
            <path d="m10 15 5-3-5-3z"/>
        </svg>
    `;

    li.innerHTML = svg + videoName;
    list.appendChild(li);
});
});


    //mp3
    document.addEventListener("DOMContentLoaded", () => {
        const audioCheckbox = document.getElementById("audioCheckbox");
        const videoCheckbox = document.getElementById("videoCheckbox");
        const containerSelect = document.querySelector("select[name='video_container']");
        const videoQualitySelect = document.querySelector('select[name="video_quality"]');

        const form = document.querySelector('form');

        const mp3Option = document.createElement("option");
        mp3Option.value = "mp3";
        mp3Option.textContent = "mp3";

        function updateContainers() {
            if (audioCheckbox.checked && !videoCheckbox.checked) {
                // mp3 hinzufügen, falls nicht schon drin
                if (![...containerSelect.options].some(opt => opt.value === "mp3")) {
                    containerSelect.appendChild(mp3Option);
                }
            } else {
                // mp3 entfernen
                [...containerSelect.options].forEach(opt => {
                    if (opt.value === "mp3") opt.remove();
                });
            }
        }

        function checkCustomQuality(selectedQuality) {
        if (selectedQuality == "custom") {
            document.getElementById("custom_video_resolution_container").style.display = "inline";
            const hiddenInput = document.createElement('input');
            hiddenInput.type = 'hidden';
            hiddenInput.name = 'custom_resolution';
            hiddenInput.value = 'yes';
            hiddenInput.id = 'custom_resolution';

            form.appendChild(hiddenInput);

        } else {
            document.getElementById("custom_video_resolution_container").style.display = "none";
            const element = document.getElementById('custom_resolution');
            if (element) {
                element.remove();
            }
        }
    }

        // Initial check
        updateContainers();
        checkCustomQuality(videoQualitySelect.value);
        // Initialer Status
updateDownloadUI(cancelLink.style.display === "inline-block");

        // Event Listener
        audioCheckbox.addEventListener("change", updateContainers);
        videoCheckbox.addEventListener("change", updateContainers);

        // Listen to changes of the video quality select box
        videoQualitySelect.addEventListener('change', (event) => {
            checkCustomQuality(event.target.value);
        });
    });

    // Task list
    //var socket = io();

    var movingBullet = document.getElementById("moving-bullet");
    var lastWorkingIndex = -1;

    socket.on("update_tasks", function(tasks) {
        let list = document.getElementById("tasks");
        list.innerHTML = "";

        let workingIndex = -1;

        tasks.forEach((task, index) => {
            let li = document.createElement("li");
            li.className = "list-group-item";
            li.textContent = task.name;
            li.style.color = task.status === "done" ? "green" : "white";
            if (task.status === "done") li.style.textDecoration = "line-through";

            list.appendChild(li);

            if (task.status === "working") workingIndex = index;
        });

        if (workingIndex !== -1) {
            let li = list.children[workingIndex];
            let bulletOffsetX = 8;
            let bulletOffsetY = (li.offsetHeight - 12) / 2;

            // Bullet sichtbar machen
            movingBullet.style.opacity = 1;
            movingBullet.style.left = bulletOffsetX + "px";
            movingBullet.style.top = (li.offsetTop + bulletOffsetY) + "px";

            // Bounce nur starten, wenn Task wechselt
            if (workingIndex !== lastWorkingIndex) {
                movingBullet.classList.remove("bounce");
                void movingBullet.offsetWidth; // Force reflow
                movingBullet.classList.add("bounce");
            }

            lastWorkingIndex = workingIndex;
        } else {
            // Bullet sanft verschwinden lassen
            movingBullet.style.opacity = 0;
            movingBullet.classList.remove("bounce");
            lastWorkingIndex = -1;
        }
    });

    // current video
    socket.on("current_video", function(data) {
const titleEl = document.getElementById("video-title");

titleEl.textContent = data;
});