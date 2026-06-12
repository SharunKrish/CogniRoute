const auth = {
  currentUser: null,

  async loadMe() {
    if (!api.getAccessToken()) return null;
    try {
      const user = await api.get('/auth/me/');
      this.currentUser = user;
      this.updateHeaderUI();
      return user;
    } catch (e) {
      console.warn('Failed to load user info:', e);
      api.clearTokens();
      this.currentUser = null;
      this.updateHeaderUI();
      return null;
    }
  },

  updateHeaderUI() {
    const userSection = document.getElementById('header-user-section');
    if (this.currentUser) {
      userSection.style.display = 'flex';
      document.getElementById('user-display-name').textContent = `${this.currentUser.username} (${this.currentUser.role})`;
      document.getElementById('user-badge').textContent = this.currentUser.username[0].toUpperCase();
    } else {
      userSection.style.display = 'none';
    }
  },

  async login(username, password) {
    try {
      const data = await api.post('/auth/login/', { username, password });
      api.setTokens(data.access, data.refresh);
      await this.loadMe();
      showToast('Welcome back, ' + username + '!', 'success');
      
      // Connect websocket after login
      websocket.connect();
      
      window.location.hash = '#dashboard';
      return true;
    } catch (err) {
      console.error('Login failed:', err);
      const detail = err.errors?.detail || 'Invalid credentials. Please try again.';
      showToast(detail, 'error');
      return false;
    }
  },

  async register(username, email, password, role) {
    try {
      await api.post('/auth/register/', { username, email, password, role });
      showToast('Registration successful! Please login.', 'success');
      return true;
    } catch (err) {
      console.error('Registration failed:', err);
      let message = 'Registration failed. Check inputs.';
      if (err.errors) {
        message = Object.entries(err.errors)
          .map(([key, val]) => `${key}: ${Array.isArray(val) ? val.join(', ') : val}`)
          .join('\n');
      }
      showToast(message, 'error');
      return false;
    }
  },

  logout() {
    api.clearTokens();
    this.currentUser = null;
    this.updateHeaderUI();
    websocket.disconnect();
    showToast('Logged out successfully.', 'info');
    window.location.hash = '#login';
  },

  renderLoginView(container) {
    container.innerHTML = `
      <div class="login-wrapper">
        <div class="glass-card login-card">
          <h2 id="auth-title">Agent Portal Login</h2>
          <p id="auth-desc">Access the CogniRoute routing workflow panel</p>
          
          <form id="auth-form">
            <div class="form-group">
              <label for="username">Username</label>
              <input type="text" id="username" class="form-control" placeholder="E.g., admin_user" required>
            </div>
            
            <div class="form-group" id="email-group" style="display: none;">
              <label for="email">Email Address</label>
              <input type="email" id="email" class="form-control" placeholder="E.g., agent@cognifyr.co">
            </div>

            <div class="form-group">
              <label for="password">Password</label>
              <input type="password" id="password" class="form-control" placeholder="••••••••" required>
            </div>

            <div class="form-group" id="role-group" style="display: none;">
              <label for="role">Assigned Role</label>
              <select id="role" class="form-control">
                <option value="agent">Support Agent</option>
                <option value="admin">System Administrator</option>
              </select>
            </div>

            <button type="submit" id="auth-submit-btn" class="btn btn-primary" style="width: 100%; margin-top: 0.5rem;">
              Sign In
            </button>
          </form>

          <div style="text-align: center; margin-top: 1.25rem; font-size: 0.875rem; color: var(--text-secondary);">
            <span id="auth-toggle-msg">First time here?</span>
            <a href="#" id="auth-toggle-link" style="color: var(--accent-blue); text-decoration: none; font-weight: 550; margin-left: 0.25rem;">Create account</a>
          </div>
        </div>
      </div>
    `;

    // Hook up UI triggers
    const form = document.getElementById('auth-form');
    const toggleLink = document.getElementById('auth-toggle-link');
    const title = document.getElementById('auth-title');
    const desc = document.getElementById('auth-desc');
    const emailGroup = document.getElementById('email-group');
    const roleGroup = document.getElementById('role-group');
    const submitBtn = document.getElementById('auth-submit-btn');
    const toggleMsg = document.getElementById('auth-toggle-msg');

    let isRegisterMode = false;

    toggleLink.addEventListener('click', (e) => {
      e.preventDefault();
      isRegisterMode = !isRegisterMode;
      if (isRegisterMode) {
        title.textContent = 'Create Agent Account';
        desc.textContent = 'Register a new credentials login for CogniRoute';
        emailGroup.style.display = 'block';
        roleGroup.style.display = 'block';
        submitBtn.textContent = 'Register Account';
        toggleMsg.textContent = 'Already have an account?';
        toggleLink.textContent = 'Sign In';
      } else {
        title.textContent = 'Agent Portal Login';
        desc.textContent = 'Access the CogniRoute routing workflow panel';
        emailGroup.style.display = 'none';
        roleGroup.style.display = 'none';
        submitBtn.textContent = 'Sign In';
        toggleMsg.textContent = 'First time here?';
        toggleLink.textContent = 'Create account';
      }
    });

    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      const username = document.getElementById('username').value.trim();
      const password = document.getElementById('password').value;

      if (isRegisterMode) {
        const email = document.getElementById('email').value.trim();
        const role = document.getElementById('role').value;
        const success = await this.register(username, email, password, role);
        if (success) {
          // Switch back to login mode automatically
          toggleLink.click();
        }
      } else {
        await this.login(username, password);
      }
    });
  }
};

// Bind logout button click
document.getElementById('logout-btn').addEventListener('click', (e) => {
  e.preventDefault();
  auth.logout();
});
