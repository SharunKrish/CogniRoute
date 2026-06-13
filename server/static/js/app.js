// SPA Routing & Global App State
const appRouter = {
  mainContainer: null,

  async init() {
    this.mainContainer = document.getElementById('main-content');
    
    // Bind hash changes
    window.addEventListener('hashchange', () => this.route());
    
    // Fetch initial auth state
    const user = await auth.loadMe();
    
    if (user) {
      // Setup live socket updates
      websocket.connect();
    }
    
    // Initial route trigger
    this.route();
  },

  async route() {
    const hash = window.location.hash;
    const token = api.getAccessToken();

    // Check login state
    if (!token && hash !== '#login') {
      window.location.hash = '#login';
      return;
    }

    if (token && (hash === '#login' || hash === '')) {
      window.location.hash = '#dashboard';
      return;
    }

    // Route views
    if (hash === '#login') {
      dashboard.stopPolling();
      auth.renderLoginView(this.mainContainer);
    } else if (hash === '#dashboard' || hash === '') {
      dashboard.render(this.mainContainer);
    } else if (hash.startsWith('#request/')) {
      dashboard.stopPolling();
      const parts = hash.split('/');
      const id = parts[1];
      if (id) {
        detail.loadRequest(id);
      } else {
        window.location.hash = '#dashboard';
      }
    } else {
      window.location.hash = '#dashboard';
    }
  }
};

// Global Toast System
function showToast(message, type = 'info') {
  const container = document.getElementById('toast-container');
  if (!container) return;

  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  
  let icon = 'ℹ️';
  if (type === 'success') icon = '✅';
  if (type === 'error') icon = '⚠️';

  toast.innerHTML = `
    <span>${icon}</span>
    <span style="font-size: 0.9rem; font-weight: 500;">${message}</span>
  `;

  container.appendChild(toast);

  // Auto remove toast
  setTimeout(() => {
    toast.style.opacity = '0';
    setTimeout(() => {
      toast.remove();
    }, 300);
  }, 4000);
}

// Start App when DOM is ready
window.addEventListener('DOMContentLoaded', () => {
  appRouter.init();
});
