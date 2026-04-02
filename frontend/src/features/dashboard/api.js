import { API_URL } from './constants';
import { parseMessage } from './utils';

export async function authFetch(url, token, sessionExpiresAt, onSessionExpired, options = {}) {
  if (sessionExpiresAt && new Date(sessionExpiresAt).getTime() <= Date.now()) {
    onSessionExpired();
    throw new Error('Phiên đăng nhập đã hết hạn.');
  }

  const headers = { ...options.headers };
  if (token) headers.Authorization = `Bearer ${token}`;
  const response = await fetch(url, { ...options, headers });

  if (response.status === 401) {
    onSessionExpired();
    throw new Error('Phiên đăng nhập đã hết hạn.');
  }

  return response;
}

export async function requestJson(url, token, sessionExpiresAt, onSessionExpired, options = {}) {
  const response = await authFetch(url, token, sessionExpiresAt, onSessionExpired, options);
  let payload = null;
  try {
    payload = await response.json();
  } catch {
    payload = null;
  }
  if (!response.ok) throw new Error(parseMessage(payload, 'Yêu cầu không thành công.'));
  return payload;
}

export async function loginRequest(username, password) {
  const response = await fetch(`${API_URL}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  });

  let payload = null;
  try {
    payload = await response.json();
  } catch {
    payload = null;
  }

  if (!response.ok) {
    throw new Error(parseMessage(payload, 'Đăng nhập không thành công.'));
  }

  return payload;
}
