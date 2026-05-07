import Cookies from 'js-cookie';

export const API_BASE_URL = 'https://medsycn.vercel.app';

export function getAuthHeaders() {
  const token = Cookies.get('medsync_token');
  return {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`
  };
}

export function getToken() {
  return Cookies.get('medsync_token') || null;
}

export function getUser() {
  const raw = Cookies.get('medsync_user');
  if (raw) {
    try {
      return JSON.parse(raw);
    } catch {
      return null;
    }
  }
  return null;
}
