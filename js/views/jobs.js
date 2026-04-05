// js/views/jobs.js
import { getJobs, updateEstado } from '../sheets.js';

let _jobs = [];

export async function renderJobs() {
  _jobs = await getJobs();

  const nuevos      = _jobs.filter(j => j.estado === 'Nuevo');
  const postulados  = _jobs.filter(j => j.estado === 'Postulado');
  const descartados = _jobs.filter(j => j.estado === 'Descartado');

  return `
    <div class="tabs">
      <button class="tab-btn active" data-tab="nuevos">
        Nuevos <span class="tab-count">${nuevos.length}</span>
      </button>
      <button class="tab-btn" data-tab="postulados">
        Postulados <span class="tab-count">${postulados.length}</span>
      </button>
      <button class="tab-btn" data-tab="descartados">
        Descartados <span class="tab-count">${descartados.length}</span>
      </button>
    </div>

    <div id="tab-nuevos" class="tab-panel active">
      ${nuevos.length
        ? nuevos.map(renderJobCard).join('')
        : emptyState('Sin ofertas nuevas por revisar.')}
    </div>

    <div id="tab-postulados" class="tab-panel">
      ${postulados.length
        ? postulados.map(renderJobCard).join('')
        : emptyState('Todavía no te has postulado a ninguna oferta.')}
    </div>

    <div id="tab-descartados" class="tab-panel">
      ${descartados.length
        ? descartados.map(renderJobCard).join('')
        : emptyState('Sin ofertas descartadas.')}
    </div>

    ${renderFuentesInfo()}
  `;
}

function renderFuentesInfo() {
  return `
    <details class="fuentes-info">
      <summary>Fuentes del scraper</summary>
      <div class="fuentes-grid">
        <div class="fuente-group">
          <div class="fuente-group-title">Activas</div>
          <div class="fuente-row"><span class="fuente-badge" data-fuente="indeed">indeed.cl</span><span>Playwright — puede ser lento o bloquearse ocasionalmente</span></div>
          <div class="fuente-row"><span class="fuente-badge" data-fuente="computrabajo">computrabajo.cl</span><span>requests + BeautifulSoup</span></div>
          <div class="fuente-row"><span class="fuente-badge" data-fuente="empleospublicos">empleospublicos.cl</span><span>requests + BeautifulSoup — sector público</span></div>
          <div class="fuente-row"><span class="fuente-badge" data-fuente="ahumada">Farmacias Ahumada</span><span>requests + BeautifulSoup</span></div>
          <div class="fuente-row"><span class="fuente-badge" data-fuente="bne">bne.cl</span><span>Playwright — Bolsa Nacional de Empleo</span></div>
          <div class="fuente-row"><span class="fuente-badge" data-fuente="trabajando">Clínica Alemana</span><span>Playwright — portal trabajando.com</span></div>
          <div class="fuente-row"><span class="fuente-badge" data-fuente="trabajando">Bupa / RedSalud / Banmédica</span><span>Playwright — portal trabajando.com</span></div>
          <div class="fuente-row"><span class="fuente-badge" data-fuente="trabajando">Colmena / Sta. María / Salcobrand</span><span>Playwright — portal trabajando.com</span></div>
        </div>
        <div class="fuente-group">
          <div class="fuente-group-title">Bloqueadas</div>
          <div class="fuente-row blocked"><span class="fuente-badge">trabajando.com</span><span>SPA con Nuxt — bloquea navegadores headless</span></div>
          <div class="fuente-row blocked"><span class="fuente-badge">laborum.cl</span><span>SPA con React — API protegida, bloquea activamente</span></div>
        </div>
      </div>
    </details>
  `;
}

function emptyState(msg) {
  return `
    <div class="empty-state">
      <div class="empty-state-icon">—</div>
      <p>${msg}</p>
    </div>
  `;
}

function fuenteSlug(fuente = '') {
  return fuente.toLowerCase().replace(/[\s.]/g, '').replace('cl', '').replace('com', '');
}

function renderJobCard(job) {
  const slug    = fuenteSlug(job.fuente);
  const actions = renderActions(job);

  return `
    <div class="job-card" data-row="${job.rowIndex}">
      <div class="job-card-header">
        <div class="job-title">${escHtml(job.titulo)}</div>
        ${job.url
          ? `<a href="${escHtml(job.url)}" target="_blank" rel="noopener" class="job-link" title="Ver oferta">↗</a>`
          : ''}
      </div>
      <div class="job-empresa">${escHtml(job.empresa)}</div>
      <div class="job-meta">
        ${job.ubicacion  ? `<span class="job-meta-item">${escHtml(job.ubicacion)}</span><span class="job-meta-sep"></span>` : ''}
        ${job.fecha_publicacion ? `<span class="job-meta-item">${escHtml(job.fecha_publicacion)}</span><span class="job-meta-sep"></span>` : ''}
        <span class="fuente-badge" data-fuente="${slug}">${escHtml(job.fuente)}</span>
      </div>
      <div class="job-card-footer">
        <div></div>
        <div class="estado-actions">${actions}</div>
      </div>
    </div>
  `;
}

function renderActions(job) {
  if (job.estado === 'Nuevo') {
    return `
      <button class="btn-postular"  data-row="${job.rowIndex}" data-action="Postulado">Postular</button>
      <button class="btn-descartar" data-row="${job.rowIndex}" data-action="Descartado">Descartar</button>
    `;
  }
  if (job.estado === 'Postulado') {
    return `
      <button class="btn-descartar" data-row="${job.rowIndex}" data-action="Descartado">Descartar</button>
    `;
  }
  if (job.estado === 'Descartado') {
    return `
      <button class="btn-restaurar" data-row="${job.rowIndex}" data-action="Nuevo">Restaurar</button>
    `;
  }
  return '';
}

function escHtml(str = '') {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

export function bindJobs() {
  // ── Tab switching ─────────────────────────────────────────────────────────
  document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const tab = btn.dataset.tab;
      document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
      btn.classList.add('active');
      document.getElementById('tab-' + tab).classList.add('active');
    });
  });

  // ── Estado action buttons ─────────────────────────────────────────────────
  document.querySelectorAll('[data-action]').forEach(btn => {
    btn.addEventListener('click', async () => {
      const rowIndex  = parseInt(btn.dataset.row);
      const newEstado = btn.dataset.action;

      btn.disabled = true;

      const ok = await updateEstado(rowIndex, newEstado);
      if (ok) {
        // Update local state and re-render
        const job = _jobs.find(j => j.rowIndex === rowIndex);
        if (job) job.estado = newEstado;

        const main = document.getElementById('main');
        const activeTab = document.querySelector('.tab-btn.active')?.dataset.tab || 'nuevos';
        main.innerHTML = await renderJobs();
        bindJobs();

        // Restore active tab
        const newTab = document.querySelector(`[data-tab="${activeTab}"]`);
        if (newTab) {
          document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
          document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
          newTab.classList.add('active');
          document.getElementById('tab-' + activeTab)?.classList.add('active');
        }
      } else {
        btn.disabled = false;
      }
    });
  });
}
