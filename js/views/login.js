// js/views/login.js
import { triggerLogin } from '../auth.js';

export function renderLogin() {
  document.getElementById('topnav').classList.add('hidden');

  return `
    <div style="
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      min-height: 82vh;
      gap: 0;
      text-align: center;
    ">
      <div style="
        font-size: 11px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 2.5px;
        color: var(--muted-2);
        margin-bottom: 18px;
      ">Búsqueda de trabajo</div>

      <h1 style="
        font-family: var(--font-serif);
        font-style: italic;
        font-size: clamp(52px, 8vw, 72px);
        font-weight: 400;
        letter-spacing: -1px;
        line-height: 1;
        color: var(--text);
        margin-bottom: 10px;
      ">Jorge</h1>

      <p style="
        color: var(--muted);
        font-size: 14px;
        font-weight: 300;
        letter-spacing: .02em;
        margin-bottom: 40px;
      ">Ofertas QF · Chile</p>

      <div style="
        width: 32px;
        height: 1px;
        background: var(--border-2);
        margin-bottom: 40px;
      "></div>

      <button class="btn btn-primary" id="login-btn" style="
        padding: 11px 32px;
        font-size: 14px;
        letter-spacing: .02em;
        font-weight: 400;
      ">
        Entrar con Google
      </button>
    </div>
  `;
}

export function bindLogin() {
  document.getElementById('login-btn')?.addEventListener('click', triggerLogin);
}
