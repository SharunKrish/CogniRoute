const CONFIG = {
  // In production, set these to your Render backend URL
  API_BASE_URL: '',  // Empty = same-origin (for local dev)
  WS_BASE_URL: '',   // Empty = auto-detect from window.location

  // Override for production deployment
  init() {
    // Detect if we are running in production on Vercel
    if (window.location.hostname !== 'localhost' && window.location.hostname !== '127.0.0.1') {
      // Replace with your Render URL (e.g., https://cogniroute-api.onrender.com)
      this.API_BASE_URL = 'https://cogniroute-api.onrender.com';
      this.WS_BASE_URL = 'wss://cogniroute-api.onrender.com';
    }
  }
};
CONFIG.init();
