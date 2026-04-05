// js/views/setup.js
import { saveSpreadsheetId, validateSpreadsheet } from '../sheets.js';

export function renderSetup() {
  return `
    <div class="setup-wrap">
      <h1 class="setup-title">Configuración</h1>
      <p class="setup-subtitle">Conecta tu hoja de Google y configura el acceso a GitHub.</p>

      <div class="setup-section" id="section-sheet">
        <div class="setup-section-title">1 · Google Sheet</div>
        <div class="field">
          <label>ID de la hoja</label>
          <input id="sheet-id-input" type="text"
            placeholder="1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgVE2upms"
            autocomplete="off" spellcheck="false">
          <div class="setup-hint">
            Es la parte de la URL entre <code>/spreadsheets/d/</code> y <code>/edit</code>.
            La hoja debe tener una pestaña llamada <code>Ofertas</code>.
          </div>
          <div class="setup-error" id="sheet-error"></div>
        </div>
        <button class="btn btn-primary btn-sm" id="sheet-save-btn">Conectar hoja</button>
      </div>

      <div class="setup-section" id="section-pat" style="opacity:.4;pointer-events:none">
        <div class="setup-section-title">2 · GitHub Personal Access Token</div>
        <div class="field">
          <label>Token (PAT)</label>
          <input id="pat-input" type="password"
            placeholder="ghp_xxxxxxxxxxxxxxxxxxxx"
            autocomplete="off" spellcheck="false">
          <div class="setup-hint">
            Necesario para el botón "Actualizar". Crea un token en
            <code>GitHub → Settings → Developer settings → Personal access tokens</code>
            con el scope <code>workflow</code>. Se guarda solo en tu navegador.
          </div>
          <div class="setup-error" id="pat-error"></div>
        </div>
        <div style="display:flex;gap:8px;align-items:center">
          <button class="btn btn-primary btn-sm" id="pat-save-btn">Guardar y continuar</button>
          <button class="btn btn-secondary btn-sm" id="pat-skip-btn">Omitir por ahora</button>
        </div>
      </div>
    </div>
  `;
}

export function bindSetup() {
  // ── Step 1: Sheet ─────────────────────────────────────────────────────────
  document.getElementById('sheet-save-btn').addEventListener('click', async () => {
    const input  = document.getElementById('sheet-id-input').value.trim();
    const errEl  = document.getElementById('sheet-error');
    const btn    = document.getElementById('sheet-save-btn');
    errEl.style.display = 'none';

    if (!input) {
      errEl.style.display = 'block';
      errEl.textContent = 'Pega el ID de la hoja.';
      return;
    }

    btn.disabled = true;
    btn.textContent = 'Verificando...';
    saveSpreadsheetId(input);

    const ok = await validateSpreadsheet(input);
    if (ok) {
      // Unlock step 2
      const section2 = document.getElementById('section-pat');
      section2.style.opacity = '1';
      section2.style.pointerEvents = 'auto';
      section2.style.animation = 'rise .3s cubic-bezier(.4,0,.2,1) both';
      btn.disabled = false;
      btn.textContent = 'Conectado ✓';
      btn.style.background = '#166534';
      document.getElementById('sheet-id-input').disabled = true;
    } else {
      errEl.style.display = 'block';
      errEl.textContent = 'No se pudo acceder. Verifica el ID y que hayas compartido la hoja con tu cuenta.';
      btn.disabled = false;
      btn.textContent = 'Conectar hoja';
    }
  });

  // ── Step 2: PAT ───────────────────────────────────────────────────────────
  document.getElementById('pat-save-btn').addEventListener('click', () => {
    const pat   = document.getElementById('pat-input').value.trim();
    const errEl = document.getElementById('pat-error');

    if (!pat) {
      errEl.style.display = 'block';
      errEl.textContent = 'Pega tu token de GitHub.';
      return;
    }

    localStorage.setItem('github_pat', pat);
    location.hash = '#/jobs';
  });

  document.getElementById('pat-skip-btn').addEventListener('click', () => {
    location.hash = '#/jobs';
  });
}
