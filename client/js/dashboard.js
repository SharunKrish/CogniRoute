const dashboard = {
  requests: [],
  currentPage: 1,
  nextPageUrl: null,
  prevPageUrl: null,
  count: 0,
  
  filters: {
    status: '',
    priority: '',
    category: '',
    search: '',
  },

  async loadRequests(page = 1) {
    this.currentPage = page;
    let url = `/requests/?page=${page}`;
    
    if (this.filters.status) url += `&status=${this.filters.status}`;
    if (this.filters.priority) url += `&priority=${this.filters.priority}`;
    if (this.filters.category) url += `&category=${this.filters.category}`;
    if (this.filters.search) url += `&search=${encodeURIComponent(this.filters.search)}`;
    
    const tableBody = document.getElementById('requests-table-body');
    if (tableBody) {
      tableBody.innerHTML = `
        <tr>
          <td colspan="7" style="text-align: center; padding: 2rem;">
            <div class="shimmer" style="margin-bottom: 0.5rem; height: 15px;"></div>
            <div class="shimmer" style="margin-bottom: 0.5rem; height: 15px; width: 80%;"></div>
            <div class="shimmer" style="height: 15px; width: 60%;"></div>
          </td>
        </tr>
      `;
    }
    
    // Load stats in parallel
    this.loadStats();
    
    try {
      const data = await api.get(url);
      if (!data) return;
      this.requests = data.results;
      this.nextPageUrl = data.next;
      this.prevPageUrl = data.previous;
      this.count = data.count;
      
      this.renderTable();
      this.renderPagination();
    } catch (e) {
      console.error('Failed to load requests:', e);
      showToast('Error loading requests.', 'error');
    }
  },

  async loadStats() {
    try {
      const stats = await api.get('/requests/stats/');
      if (!stats) return;
      
      const updateVal = (id, val) => {
        const el = document.getElementById(id);
        if (el) el.textContent = val;
      };
      
      updateVal('stat-val-classified', stats.classified);
      updateVal('stat-val-inprogress', stats.in_progress);
      updateVal('stat-val-resolved', stats.resolved);
      updateVal('stat-val-high', stats.high_priority);
    } catch (e) {
      console.error('Failed to load stats:', e);
    }
  },

  render(container) {
    container.innerHTML = `
      <div class="view-container">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 2rem;">
          <div>
            <h1 style="font-size: 2rem; font-weight: 700;">Workflow Operations Queue</h1>
            <p style="color: var(--text-secondary); margin-top: 0.25rem;">Monitor and manage customer requests routed through AI classification</p>
          </div>
          <!-- Native Invoker command to trigger the modal dialog -->
          <button class="btn btn-primary" commandfor="create-request-dialog" command="show-modal">
            <span>+</span> Submit Request
          </button>
        </div>

        <!-- Stats Section -->
        <div class="dashboard-stats" id="dashboard-stats-container">
          <div class="glass-card stat-card classified">
            <div class="stat-value" id="stat-val-classified">-</div>
            <div class="stat-label">Classified</div>
          </div>
          <div class="glass-card stat-card in-progress">
            <div class="stat-value" id="stat-val-inprogress">-</div>
            <div class="stat-label">In Progress</div>
          </div>
          <div class="glass-card stat-card resolved">
            <div class="stat-value" id="stat-val-resolved">-</div>
            <div class="stat-label">Resolved</div>
          </div>
          <div class="glass-card stat-card high-priority">
            <div class="stat-value" id="stat-val-high">-</div>
            <div class="stat-label">High Priority</div>
          </div>
        </div>

        <!-- Filter Panel -->
        <div class="glass-card filter-bar">
          <div class="search-wrapper">
            <span class="search-icon">🔍</span>
            <input type="text" id="filter-search" class="form-control search-input" placeholder="Search customer, email, message..." value="${this.filters.search}">
          </div>

          <select id="filter-status" class="filter-select">
            <option value="">All Statuses</option>
            <option value="queued" ${this.filters.status === 'queued' ? 'selected' : ''}>Queued</option>
            <option value="classified" ${this.filters.status === 'classified' ? 'selected' : ''}>Classified</option>
            <option value="in_progress" ${this.filters.status === 'in_progress' ? 'selected' : ''}>In Progress</option>
            <option value="resolved" ${this.filters.status === 'resolved' ? 'selected' : ''}>Resolved</option>
          </select>

          <select id="filter-category" class="filter-select">
            <option value="">All Categories</option>
            <option value="sales" ${this.filters.category === 'sales' ? 'selected' : ''}>Sales</option>
            <option value="support" ${this.filters.category === 'support' ? 'selected' : ''}>Support</option>
            <option value="urgent" ${this.filters.category === 'urgent' ? 'selected' : ''}>Urgent</option>
            <option value="spam" ${this.filters.category === 'spam' ? 'selected' : ''}>Spam</option>
            <option value="other" ${this.filters.category === 'other' ? 'selected' : ''}>Other</option>
          </select>

          <select id="filter-priority" class="filter-select">
            <option value="">All Priorities</option>
            <option value="low" ${this.filters.priority === 'low' ? 'selected' : ''}>Low</option>
            <option value="medium" ${this.filters.priority === 'medium' ? 'selected' : ''}>Medium</option>
            <option value="high" ${this.filters.priority === 'high' ? 'selected' : ''}>High</option>
          </select>

          <button id="reset-filters" class="btn btn-secondary">Reset</button>
        </div>

        <!-- Data Queue Table -->
        <div class="glass-card" style="padding: 0;">
          <div class="table-container">
            <table>
              <thead>
                <tr>
                  <th>Request ID</th>
                  <th>Customer</th>
                  <th>Channel</th>
                  <th>Category</th>
                  <th>Priority</th>
                  <th>Status</th>
                  <th>Submitted At</th>
                </tr>
              </thead>
              <tbody id="requests-table-body">
                <!-- Rows injected here -->
              </tbody>
            </table>
          </div>
        </div>

        <!-- Pagination -->
        <div class="pagination">
          <div id="pagination-info" class="pagination-info">Showing 0 requests</div>
          <div id="pagination-controls" class="pagination-controls">
            <!-- Buttons injected here -->
          </div>
        </div>
      </div>
    `;

    // Bind Filter Controls
    const bindFilter = (id, key) => {
      document.getElementById(id).addEventListener('change', (e) => {
        this.filters[key] = e.target.value;
        this.loadRequests(1);
      });
    };
    bindFilter('filter-status', 'status');
    bindFilter('filter-category', 'category');
    bindFilter('filter-priority', 'priority');

    // Debounced search
    let searchTimeout;
    document.getElementById('filter-search').addEventListener('input', (e) => {
      clearTimeout(searchTimeout);
      searchTimeout = setTimeout(() => {
        this.filters.search = e.target.value;
        this.loadRequests(1);
      }, 300);
    });

    document.getElementById('reset-filters').addEventListener('click', () => {
      this.filters = { status: '', priority: '', category: '', search: '' };
      document.getElementById('filter-search').value = '';
      document.getElementById('filter-status').value = '';
      document.getElementById('filter-category').value = '';
      document.getElementById('filter-priority').value = '';
      this.loadRequests(1);
    });

    // Handle initial list load
    this.loadRequests(1);
  },

  renderTable() {
    const tableBody = document.getElementById('requests-table-body');
    if (!tableBody) return;

    if (this.requests.length === 0) {
      tableBody.innerHTML = `
        <tr>
          <td colspan="7" style="text-align: center; color: var(--text-secondary); padding: 3rem;">
            No customer requests found matching selected criteria.
          </td>
        </tr>
      `;
      return;
    }

    tableBody.innerHTML = this.requests.map(req => {
      const date = new Date(req.created_at).toLocaleString();
      const categoryBadge = req.category_snapshot 
        ? `<span class="badge badge-${req.category_snapshot}">${req.category_snapshot}</span>`
        : `<span class="text-muted" style="font-size: 0.8rem;">Pending AI...</span>`;
      
      const priorityBadge = req.priority_snapshot
        ? `<span class="badge badge-${req.priority_snapshot}">${req.priority_snapshot}</span>`
        : `<span class="text-muted" style="font-size: 0.8rem;">Pending AI...</span>`;

      return `
        <tr class="clickable-row" data-id="${req.id}" id="request-row-${req.id}">
          <td style="font-family: var(--font-mono); font-weight: bold; color: var(--accent-blue);">#${req.id}</td>
          <td>
            <div style="font-weight: 550;">${escapeHtml(req.customer_name)}</div>
            <div style="font-size: 0.8rem; color: var(--text-secondary);">${escapeHtml(req.customer_email)}</div>
          </td>
          <td style="text-transform: capitalize;">${req.source_channel}</td>
          <td>${categoryBadge}</td>
          <td>${priorityBadge}</td>
          <td><span class="badge badge-${req.status}">${req.status.replace('_', ' ')}</span></td>
          <td style="color: var(--text-secondary); font-size: 0.85rem;">${date}</td>
        </tr>
      `;
    }).join('');

    // Add click events to rows
    tableBody.querySelectorAll('.clickable-row').forEach(row => {
      row.addEventListener('click', () => {
        const id = row.getAttribute('data-id');
        window.location.hash = `#request/${id}`;
      });
    });
  },

  renderPagination() {
    const info = document.getElementById('pagination-info');
    const controls = document.getElementById('pagination-controls');
    if (!info || !controls) return;

    const start = this.count === 0 ? 0 : (this.currentPage - 1) * 20 + 1;
    const end = Math.min(this.currentPage * 20, this.count);
    info.textContent = `Showing ${start} to ${end} of ${this.count} requests`;

    controls.innerHTML = `
      <button class="btn btn-secondary" id="pag-prev" ${!this.prevPageUrl ? 'disabled' : ''} style="padding: 0.4rem 0.8rem;">
        Previous
      </button>
      <button class="btn btn-secondary" id="pag-next" ${!this.nextPageUrl ? 'disabled' : ''} style="padding: 0.4rem 0.8rem;">
        Next
      </button>
    `;

    document.getElementById('pag-prev').addEventListener('click', () => {
      if (this.prevPageUrl) this.loadRequests(this.currentPage - 1);
    });
    document.getElementById('pag-next').addEventListener('click', () => {
      if (this.nextPageUrl) this.loadRequests(this.currentPage + 1);
    });
  },

  patchRequestInList(updatedReq) {
    const index = this.requests.findIndex(r => r.id === updatedReq.id);
    
    const matchesFilter = 
      (!this.filters.status || this.filters.status === updatedReq.status) &&
      (!this.filters.priority || this.filters.priority === updatedReq.priority_snapshot) &&
      (!this.filters.category || this.filters.category === updatedReq.category_snapshot);
      
    if (index !== -1) {
      if (matchesFilter) {
        this.requests[index] = updatedReq;
        this.renderTable();
      } else {
        this.requests.splice(index, 1);
        this.count--;
        this.renderTable();
        this.renderPagination();
      }
    } else {
      if (this.currentPage === 1 && matchesFilter) {
        this.requests.unshift(updatedReq);
        this.count++;
        this.renderTable();
        this.renderPagination();
      }
    }
    
    this.loadStats();
  }
};

// Handle New Request Form Submission
document.getElementById('create-request-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  
  const payload = {
    customer_name: document.getElementById('req-name').value.trim(),
    customer_email: document.getElementById('req-email').value.trim(),
    source_channel: document.getElementById('req-channel').value,
    original_message: document.getElementById('req-message').value.trim(),
  };

  const idempotency = document.getElementById('req-idempotency').value.trim();
  if (idempotency) {
    payload.idempotency_key = idempotency;
  }

  try {
    const result = await api.post('/requests/', payload);
    if (result) {
      // Close native dialog
      document.getElementById('create-request-dialog').close();
      
      // Clear inputs
      document.getElementById('create-request-form').reset();
      
      showToast(`Request #${result.id || result.data?.id} submitted successfully!`, 'success');
      
      // Reload current queue
      dashboard.loadRequests(1);
    }
  } catch (err) {
    console.error('Failed to submit request:', err);
    showToast(err.errors?.message || 'Failed to submit request. Check if email/fields are filled.', 'error');
  }
});

function escapeHtml(text) {
  if (!text) return '';
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}
