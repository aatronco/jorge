// js/router.js
import { isLoggedIn } from './auth.js';
import { renderLogin, bindLogin }   from './views/login.js';
import { renderSetup, bindSetup }   from './views/setup.js';
import { renderJobs, bindJobs }     from './views/jobs.js';

const main = () => document.getElementById('main');
const nav  = () => document.getElementById('topnav');

export function renderNav() {
  const n = nav();
  n.classList.remove('hidden');
  n.innerHTML = `
    <span class="brand">Jorge</span>
    <div style="display:flex;align-items:center;gap:8px">
      <button id="refresh-btn">↻ Actualizar</button>
      <button id="logout-btn">Cerrar sesión</button>
    </div>
  `;
  document.getElementById('logout-btn').addEventListener('click', () => {
    import('./auth.js').then(m => m.logout());
  });
  document.getElementById('refresh-btn').addEventListener('click', async () => {
    const btn = document.getElementById('refresh-btn');
    btn.disabled = true;
    btn.textContent = 'Iniciando...';
    const { triggerScraper } = await import('./github.js');
    const ok = await triggerScraper();
    if (ok) {
      showNavToast('Scraper iniciado en GitHub Actions');
    } else {
      showNavToast('Error al iniciar el scraper. Verifica tu PAT.', true);
    }
    btn.disabled = false;
    btn.textContent = '↻ Actualizar';
  });
}

function showNavToast(msg, isError = false) {
  const el = document.createElement('div');
  el.className = 'toast' + (isError ? ' error' : '');
  el.textContent = msg;
  document.body.appendChild(el);
  setTimeout(() => el.remove(), 3500);
}

async function route() {
  const hash = location.hash || '#/login';

  if (!isLoggedIn() && hash !== '#/login') {
    location.hash = '#/login';
    return;
  }

  const parts = hash.replace('#/', '').split('/');

  if (parts[0] === 'login' || !isLoggedIn()) {
    nav().classList.add('hidden');
    main().innerHTML = renderLogin();
    bindLogin();
    return;
  }

  if (parts[0] === 'setup') {
    nav().classList.add('hidden');
    main().innerHTML = renderSetup();
    bindSetup();
    return;
  }

  if (parts[0] === 'jobs' || parts[0] === '') {
    const spreadsheetId = localStorage.getItem('spreadsheet_id');
    if (!spreadsheetId) {
      location.hash = '#/setup';
      return;
    }
    renderNav();
    main().innerHTML = await renderJobs();
    bindJobs();
    return;
  }

  location.hash = '#/jobs';
}

export function initRouter() {
  window.addEventListener('hashchange', route);
  route();
}
