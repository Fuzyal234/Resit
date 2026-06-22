'use strict';

// Character counter for encrypt textarea
(function () {
    const msg = document.getElementById('message');
    const counter = document.getElementById('charCounter');
    if (!msg || !counter) return;

    function update() {
        const n = msg.value.length;
        counter.textContent = n.toLocaleString() + ' / 10,000 characters';
        counter.style.color = n > 9500 ? '#ef4444' : n > 8000 ? '#f59e0b' : '';
    }
    msg.addEventListener('input', update);
    update();
}());

// Copy-to-clipboard helper (no external libraries)
function copyField(id, btn) {
    const el = document.getElementById(id);
    if (!el) return;
    navigator.clipboard.writeText(el.value).then(function () {
        const orig = btn.textContent;
        btn.textContent = 'Copied!';
        btn.disabled = true;
        setTimeout(function () {
            btn.textContent = orig;
            btn.disabled = false;
        }, 2000);
    }).catch(function () {
        el.select();
        document.execCommand('copy');
    });
}

// Scroll to result panel after form submission
(function () {
    const panel = document.getElementById('resultPanel') ||
                  document.querySelector('.result-panel');
    if (panel) {
        panel.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
}());
