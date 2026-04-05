// js/auth.js
import { CLIENT_ID, SPREADSHEET_SCOPE } from './config.js';
import { initRouter } from './router.js';

let tokenClient;
let accessToken = sessionStorage.getItem('gsi_token') || null;

export function getToken() { return accessToken; }

export function isLoggedIn() { return !!accessToken; }

export function logout() {
  accessToken = null;
  sessionStorage.removeItem('gsi_token');
  location.hash = '#/login';
}

let _renewalPromise = null;
export async function renewToken() {
  if (_renewalPromise) return _renewalPromise;
  _renewalPromise = new Promise((resolve, reject) => {
    window._tokenResolve = (v) => { _renewalPromise = null; resolve(v); };
    window._tokenReject  = (e) => { _renewalPromise = null; reject(e); };
    tokenClient.requestAccessToken({ prompt: '' });
  });
  return _renewalPromise;
}

export function initAuth() {
  const ready = () => {
    tokenClient = google.accounts.oauth2.initTokenClient({
      client_id: CLIENT_ID,
      scope: SPREADSHEET_SCOPE,
      callback: (resp) => {
        if (resp.error) {
          if (window._tokenReject) { window._tokenReject(resp.error); window._tokenReject = null; }
          logout();
          return;
        }
        accessToken = resp.access_token;
        sessionStorage.setItem('gsi_token', accessToken);
        if (window._tokenResolve) { window._tokenResolve(); window._tokenResolve = null; }
        if (location.hash === '#/login' || location.hash === '') {
          location.hash = '#/jobs';
        }
      },
    });
    initRouter();
  };

  if (typeof google !== 'undefined') {
    ready();
  } else {
    window.addEventListener('load', () => {
      if (typeof google !== 'undefined') ready();
    });
  }
}

export function triggerLogin() {
  tokenClient.requestAccessToken({ prompt: 'select_account' });
}

// Bootstrap
initAuth();
