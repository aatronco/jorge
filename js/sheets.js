// js/sheets.js
import { getToken, renewToken, logout } from './auth.js';

const BASE  = 'https://sheets.googleapis.com/v4/spreadsheets';
const SHEET = 'Ofertas';

function getSpreadsheetId() {
  return localStorage.getItem('spreadsheet_id');
}

export function saveSpreadsheetId(id) {
  localStorage.setItem('spreadsheet_id', id.trim());
}

function showToast(msg, isError = false) {
  const el = document.createElement('div');
  el.className = 'toast' + (isError ? ' error' : '');
  el.textContent = msg;
  document.body.appendChild(el);
  setTimeout(() => el.remove(), 3500);
}

async function request(url, options = {}) {
  let token = getToken();
  const doFetch = (t) => fetch(url, {
    ...options,
    headers: {
      'Authorization': `Bearer ${t}`,
      'Content-Type': 'application/json',
      ...(options.headers || {}),
    },
  });

  let res = await doFetch(token);

  if (res.status === 401) {
    try {
      await renewToken();
      token = getToken();
      res = await doFetch(token);
    } catch {
      logout();
      return null;
    }
  }

  if (res.status === 403) { showToast('Sin acceso a la hoja. Verifica permisos.', true); return null; }
  if (res.status === 429) { showToast('Límite de Google Sheets alcanzado. Intenta en un minuto.', true); return null; }
  if (!res.ok) { showToast('Error de conexión.', true); return null; }

  return res.json();
}

export async function validateSpreadsheet(id) {
  const url = `${BASE}/${id}/values/${encodeURIComponent(SHEET + '!A1:H1')}`;
  const res = await fetch(url, {
    headers: { Authorization: `Bearer ${getToken()}` },
  });
  return res.ok;
}

export async function getJobs() {
  const id  = getSpreadsheetId();
  const url = `${BASE}/${id}/values/${encodeURIComponent(SHEET + '!A2:H')}`;
  const data = await request(url);
  if (!data?.values) return [];
  return data.values.map((row, i) => rowToJob(row, i + 2)); // +2: row 1 is header, array is 0-based
}

function rowToJob([titulo='', empresa='', ubicacion='', fecha_publicacion='', descripcion='', url='', fuente='', estado='Nuevo'] = [], rowIndex) {
  return { rowIndex, titulo, empresa, ubicacion, fecha_publicacion, descripcion, url, fuente, estado };
}

export async function updateEstado(rowIndex, estado) {
  const id    = getSpreadsheetId();
  const range = encodeURIComponent(`${SHEET}!H${rowIndex}`);
  const res = await request(`${BASE}/${id}/values/${range}?valueInputOption=RAW`, {
    method: 'PUT',
    body: JSON.stringify({ values: [[estado]] }),
  });
  if (res) showToast('Estado actualizado');
  return res;
}
