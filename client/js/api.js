const api = {
  getAccessToken() {
    return localStorage.getItem('access_token');
  },
  
  getRefreshToken() {
    return localStorage.getItem('refresh_token');
  },
  
  setTokens(access, refresh) {
    localStorage.setItem('access_token', access);
    if (refresh) {
      localStorage.setItem('refresh_token', refresh);
    }
  },
  
  clearTokens() {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
  },

  async request(endpoint, options = {}) {
    const url = endpoint.startsWith('http') ? endpoint : `${CONFIG.API_BASE_URL}/api${endpoint}`;
    
    // Add Authorization header
    const token = this.getAccessToken();
    const headers = {
      'Content-Type': 'application/json',
      ...options.headers,
    };
    
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
    
    const config = {
      ...options,
      headers,
    };
    
    try {
      let response = await fetch(url, config);
      
      // Token expiration / 401 handling
      if (response.status === 401 && this.getRefreshToken()) {
        console.warn('Access token expired, attempting refresh...');
        const refreshed = await this.refreshToken();
        if (refreshed) {
          // Retry request with new token
          headers['Authorization'] = `Bearer ${this.getAccessToken()}`;
          response = await fetch(url, config);
        } else {
          // Refresh failed, logout
          this.clearTokens();
          window.location.hash = '#login';
          return null;
        }
      }
      
      return response;
    } catch (error) {
      console.error('API request error:', error);
      throw error;
    }
  },

  async refreshToken() {
    const refresh = this.getRefreshToken();
    if (!refresh) return false;
    
    try {
      const response = await fetch(`${CONFIG.API_BASE_URL}/api/auth/refresh/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh })
      });
      
      if (response.ok) {
        const data = await response.json();
        this.setTokens(data.access, data.refresh);
        console.log('Access token refreshed successfully.');
        return true;
      }
      return false;
    } catch (e) {
      console.error('Error refreshing token:', e);
      return false;
    }
  },

  async get(endpoint) {
    const res = await this.request(endpoint, { method: 'GET' });
    if (!res) return null;
    if (!res.ok) throw new Error(`GET ${endpoint} failed: ${res.statusText}`);
    return res.json();
  },

  async post(endpoint, data) {
    const res = await this.request(endpoint, {
      method: 'POST',
      body: JSON.stringify(data)
    });
    if (!res) return null;
    if (!res.ok) {
      const errData = await res.json().catch(() => ({}));
      const err = new Error(`POST ${endpoint} failed`);
      err.errors = errData;
      throw err;
    }
    return res.json();
  },

  async patch(endpoint, data) {
    const res = await this.request(endpoint, {
      method: 'PATCH',
      body: JSON.stringify(data)
    });
    if (!res) return null;
    if (!res.ok) {
      const errData = await res.json().catch(() => ({}));
      const err = new Error(`PATCH ${endpoint} failed`);
      err.errors = errData;
      throw err;
    }
    return res.json();
  }
};
