/* ── ADDITIONS for dossier.html <script> block ────────────────────────
   1. Add this helper near the other helpers (initials, seededPct, etc).
   2. Replace the `casesHTML` block inside renderCard() with the version
      further below, and call `attachIpcLookups(cases)` after the card
      is injected into the DOM (see call site at the bottom).
*/

// ── IPC SECTION LOOKUP ────────────────────────────────────────────
// Collects every section code referenced across this MP's cases and
// resolves them in a single batch call, instead of one fetch per case.
function extractAllSectionCodes(cases) {
    const codes = new Set();
    cases.forEach(c => {
      if (!c.ipc_sections) return;
      c.ipc_sections.split(/[,/]| and /).forEach(s => {
        const trimmed = s.trim();
        if (trimmed) codes.add(trimmed);
      });
    });
    return Array.from(codes);
  }
  
  async function fetchIpcDescriptions(codes) {
    if (codes.length === 0) return { sections: {}, not_found: [] };
    try {
      const res = await fetch(`${API_BASE}/ipc?sections=${encodeURIComponent(codes.join(','))}`);
      if (!res.ok) throw new Error(`IPC lookup failed: ${res.status}`);
      return await res.json();
    } catch (err) {
      console.warn('IPC section lookup failed, showing cases without descriptions:', err);
      return { sections: {}, not_found: codes };
    }
  }
  
  // Renders each ipc_sections code as a small pill. Click toggles its
  // plain-English description inline (no extra fetch — data already loaded).
  function renderIpcPills(rawSectionsString, lookup) {
    if (!rawSectionsString) return '';
    const codes = rawSectionsString.split(/[,/]| and /).map(s => s.trim()).filter(Boolean);
    return `<div class="ipc-pill-row">
      ${codes.map(code => {
        const entry = lookup[code.toUpperCase()];
        const safeId = `ipc-${code.replace(/[^a-zA-Z0-9]/g, '')}-${Math.random().toString(36).slice(2, 7)}`;
        return `
          <div class="ipc-pill-wrap">
            <button type="button" class="ipc-pill" data-target="${safeId}"
              title="${entry ? entry.section_title : 'Description unavailable'}">
              §${code}
            </button>
            <div class="ipc-desc" id="${safeId}" hidden>
              ${entry
                ? `<strong>${entry.section_title}</strong><p>${entry.section_desc}</p>`
                : `<em>No description on file for section ${code}.</em>`}
            </div>
          </div>`;
      }).join('')}
    </div>`;
  }
  
  function attachIpcPillToggles() {
    document.querySelectorAll('.ipc-pill').forEach(btn => {
      btn.addEventListener('click', () => {
        const target = document.getElementById(btn.dataset.target);
        if (target) target.hidden = !target.hidden;
      });
    });
  }
  
  /* ── REPLACEMENT for casesHTML block inside renderCard() ──────────── */
  // (this version is async-aware — see call-site note below)
  async function buildCasesHTML(cases) {
    if (cases.length === 0) {
      return `
        <div class="cases-section animate-in stagger-4">
          <div class="section-title">// criminal record</div>
          <div class="clean-record">
            <span style="color:#5ec97a">✓</span> No pending cases declared in 2024 ECI affidavit.
          </div>
        </div>`;
    }
  
    const allCodes = extractAllSectionCodes(cases);
    const { sections: lookup } = await fetchIpcDescriptions(allCodes);
  
    return `
      <div class="cases-section animate-in stagger-4">
        <div class="section-title">// pending cases</div>
        ${cases.map((c, i) => `
          <div class="case-item">
            <span class="case-num">#${c.serial_no || i + 1}</span>
            <div class="case-text">
              ${c.ipc_sections ? `<strong>IPC:</strong> ${c.ipc_sections}` : ''}
              ${c.other_acts   ? ` &nbsp;|&nbsp; ${c.other_acts}` : ''}
              ${c.court        ? `<br><span style="color:#6a6258;font-size:11px">${c.court}</span>` : ''}
              ${c.charge_date  ? `<span style="color:#6a6258;font-size:11px"> · ${c.charge_date}</span>` : ''}
              ${c.is_serious   ? `<br><span style="color:#e85050;font-size:10px;font-family:'Share Tech Mono',monospace">⚠ SERIOUS</span>` : ''}
              ${renderIpcPills(c.ipc_sections, lookup)}
            </div>
          </div>`).join('')}
      </div>`;
  }
  
  /* ── CALL SITE CHANGE in renderCard() ──────────────────────────────
     renderCard() currently builds `casesHTML` synchronously and then does
     one big innerHTML write. Since the IPC lookup is async, either:
  
     Option A (simplest): make renderCard() itself `async`, and do:
         const casesHTML = await buildCasesHTML(cases);
     right before the big `document.getElementById('card-content').innerHTML = ...`
     write — then call `await renderCard(mp)` from init().
  
     Option B (no signature changes): render the card first with a
     "Loading case details..." placeholder for casesHTML, inject it, then
     separately call buildCasesHTML(cases) and patch just the
     .cases-section element once it resolves:
  
         document.querySelector('.cases-section').outerHTML = await buildCasesHTML(cases);
  
     Either way, call `attachIpcPillToggles()` right after the cases HTML
     is in the DOM, so the click handlers bind to the new buttons.
  */
  
  /* ── CSS additions (add to the <style> block) ──────────────────────
  .ipc-pill-row{display:flex;flex-wrap:wrap;gap:6px;margin-top:8px}
  .ipc-pill{font-family:'Share Tech Mono',monospace;font-size:10px;letter-spacing:1px;
    color:#c8a84b;background:rgba(200,168,75,0.08);border:1px solid rgba(200,168,75,0.4);
    border-radius:3px;padding:3px 7px;cursor:pointer}
  .ipc-pill:hover{background:rgba(200,168,75,0.18)}
  .ipc-desc{margin-top:6px;padding:8px 10px;border-left:2px solid rgba(200,168,75,0.4);
    background:rgba(200,168,75,0.04);font-size:12px;color:#c0b8a8;line-height:1.5}
  .ipc-desc strong{color:#e8e0cc;font-size:12px}
  .ipc-desc p{margin-top:4px}
  */