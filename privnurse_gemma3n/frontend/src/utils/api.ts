import { isDemoModeError, showDemoModeAlert } from './demoMode';

export async function fetchWithAuth(endpoint: string, options: RequestInit = {}) {
  const token = localStorage.getItem('token');
  
  // Don't set Content-Type if body is FormData (let browser set it)
  const isFormData = options.body instanceof FormData;
  
  const headers: any = {
    'Authorization': `Bearer ${token}`,
    ...options.headers,
  };
  
  if (!isFormData) {
    headers['Content-Type'] = 'application/json';
  }

  const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}${endpoint}`, {
    ...options,
    headers,
  });

  if (response.status === 401) {
    // Token 過期或無效，可以在這裡處理登出邏輯
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    window.location.href = '/login';
    throw new Error('Unauthorized');
  }

  if (response.status === 403) {
    // Clone the response so we can read it without consuming the original
    const clonedResponse = response.clone();
    try {
      const data = await clonedResponse.json();
      if (isDemoModeError(data.detail)) {
        showDemoModeAlert(data.detail.message);
        throw new Error('Demo mode restriction');
      }
    } catch (e) {
      // If it's the demo mode error we threw, re-throw it
      if (e instanceof Error && e.message === 'Demo mode restriction') {
        throw e;
      }
      // Otherwise, continue with normal error handling
    }
  }

  return response;
}
