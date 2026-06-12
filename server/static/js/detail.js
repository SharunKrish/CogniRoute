const detail = {
  request: null,

  async loadRequest(id) {
    const mainContent = document.getElementById('main-content');
    mainContent.innerHTML = `
      <div class="glass-card" style="text-align: center; padding: 3rem;">
        <div class="shimmer" style="margin: 10px auto; width: 200px; height: 20px;"></div>
        <div class="shimmer" style="margin: 10px auto; width: 150px; height: 15px;"></div>
      </div>
    `;

    try {
      const data = await api.get(`/requests/${id}/`);
      if (!data) return;
      this.request = data;
      this.render();
    } catch (e) {
      console.error(e);
      showToast('Error loading request detail.', 'error');
      window.location.hash = '#dashboard';
    }
  },

  render() {
    const mainContent = document.getElementById('main-content');
    if (!mainContent || !this.request) return;

    const req = this.request;
    const date = new Date(req.created_at).toLocaleString();
    
    // Get latest successful or pending classification
    const latestClass = req.classifications && req.classifications.length > 0 
      ? req.classifications[0] 
      : null;

    const isAdmin = auth.currentUser && auth.currentUser.role === 'admin';

    let aiCardHtml = '';
    if (latestClass) {
      const confidencePercent = Math.round(latestClass.confidence * 100);
      const isFailed = latestClass.status === 'failed';
      const isPending = latestClass.status === 'pending';
      
      if (isPending) {
        aiCardHtml = `
          <div class="glass-card ai-card" style="border-color: rgba(139, 92, 246, 0.4);">
            <div class="ai-header">
              <h3>AI Classification Process</h3>
              <span class="badge badge-queued">Analyzing</span>
            </div>
            <div style="text-align: center; padding: 1.5rem 0;">
              <div class="shimmer" style="margin-bottom: 0.5rem; height: 15px; width: 90%;"></div>
              <div class="shimmer" style="height: 15px; width: 70%;"></div>
              <p style="font-size: 0.85rem; color: var(--text-secondary); margin-top: 1rem;">Querying model provider in background...</p>
            </div>
          </div>
        `;
      } else if (isFailed) {
        aiCardHtml = `
          <div class="glass-card ai-card" style="border-color: rgba(244, 63, 94, 0.4); background: rgba(244, 63, 94, 0.02);">
            <div class="ai-header">
              <h3>AI Classification Process</h3>
              <span class="badge badge-closed">Failed</span>
            </div>
            <p style="color: #fca5a5; font-size: 0.95rem; font-weight: bold; margin-bottom: 0.5rem;">Classification Error</p>
            <p style="color: var(--text-secondary); font-size: 0.85rem; font-family: var(--font-mono); background: rgba(0,0,0,0.2); padding: 0.75rem; border-radius: var(--radius-sm); margin-bottom: 1rem;">
              ${escapeHtml(latestClass.error_message)}
            </p>
            ${isAdmin ? `
              <button id="detail-retry-btn-inline" class="btn btn-secondary" style="padding: 0.5rem 1rem; font-size: 0.85rem;">
                🔄 Retry Classification
              </button>
            ` : ''}
          </div>
        `;
      } else {
        aiCardHtml = `
          <div class="glass-card ai-card">
            <div class="ai-header">
              <h3>AI Route Recommendation</h3>
              <span class="ai-score">${confidencePercent}% Confidence</span>
            </div>
            
            <div class="ai-grid">
              <div class="ai-item">
                <label>Assigned Category</label>
                <span class="badge badge-${latestClass.category}">${latestClass.category}</span>
              </div>
              <div class="ai-item">
                <label>Suggested Priority</label>
                <span class="badge badge-${latestClass.priority}">${latestClass.priority}</span>
              </div>
            </div>

            <div class="form-group" style="margin-bottom: 1rem;">
              <label style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase;">Generated Summary</label>
              <div class="ai-summary">${escapeHtml(latestClass.summary)}</div>
            </div>

            <div class="form-group" style="margin-bottom: 1rem;">
              <label style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase;">Reasoning Rationale</label>
              <p style="font-size: 0.9rem; line-height: 1.5; color: var(--text-secondary);">${escapeHtml(latestClass.reason)}</p>
            </div>

            <!-- Collapsible Raw JSON payload for details -->
            <details style="margin-top: 1.25rem; font-size: 0.8rem; border-top: 1px solid var(--border-color); padding-top: 0.75rem;">
              <summary style="cursor: pointer; color: var(--text-secondary); font-weight: 550; outline: none; user-select: none;">
                View Raw AI Payload (${latestClass.provider})
              </summary>
              <pre style="margin-top: 0.5rem; background: rgba(0,0,0,0.4); padding: 0.75rem; border-radius: var(--radius-sm); font-family: var(--font-mono); overflow-x: auto; max-height: 200px; color: #a5f3fc;">${JSON.stringify(latestClass.raw_output, null, 2)}</pre>
            </details>
          </div>
        `;
      }
    } else {
      aiCardHtml = `
        <div class="glass-card ai-card" style="text-align: center; padding: 2rem;">
          <p style="color: var(--text-secondary); margin-bottom: 1rem;">No AI classification has run for this request.</p>
          ${isAdmin ? `
            <button id="detail-run-classify-btn" class="btn btn-primary" style="font-size: 0.85rem;">Run AI Classifier</button>
          ` : ''}
        </div>
      `;
    }

    // Status Selector dropdown
    const statuses = [
      { val: 'new', label: 'New' },
      { val: 'queued', label: 'Queued' },
      { val: 'classified', label: 'Classified' },
      { val: 'in_progress', label: 'In Progress' },
      { val: 'resolved', label: 'Resolved' },
      { val: 'closed', label: 'Closed' }
    ];

    const statusOptions = statuses.map(s => `
      <option value="${s.val}" ${req.status === s.val ? 'selected' : ''}>${s.label}</option>
    `).join('');

    mainContent.innerHTML = `
      <div class="view-container">
        <!-- Back to queue -->
        <a href="#dashboard" style="color: var(--accent-blue); text-decoration: none; display: inline-flex; align-items: center; gap: 0.5rem; font-size: 0.9rem; margin-bottom: 1.5rem; font-weight: 550;">
          <!-- Return to Operations Queue -->
          ← Return to Operations Queue
        </a>

        <!-- Detail Header -->
        <div class="detail-header">
          <div class="detail-title-section">
            <h1>Request #${req.id}</h1>
            <div class="detail-meta-text">
              Submitted via <span style="text-transform: capitalize; font-weight: bold; color: var(--text-primary);">${req.source_channel}</span> on ${date}
            </div>
          </div>
          <div style="display: flex; gap: 1rem; align-items: center;">
            ${latestClass && latestClass.status === 'failed' && isAdmin ? `
              <button id="detail-retry-btn" class="btn btn-secondary">
                🔄 Retry AI Route
              </button>
            ` : ''}
            <span class="badge badge-${req.status}" style="font-size: 0.9rem; padding: 0.4rem 0.8rem;">
              ${req.status.replace('_', ' ')}
            </span>
          </div>
        </div>

        <!-- Detail Grid Layout -->
        <div class="detail-grid">
          <!-- Left Main Area -->
          <div>
            <!-- Message Card -->
            <div class="glass-card request-card">
              <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                <div>
                  <h3 style="font-size: 1.15rem; font-weight: 600;">${escapeHtml(req.customer_name)}</h3>
                  <a href="mailto:${req.customer_email}" style="color: var(--text-secondary); font-size: 0.875rem; text-decoration: none;">
                    ${escapeHtml(req.customer_email)}
                  </a>
                </div>
                ${req.idempotency_key ? `
                  <div style="text-align: right;">
                    <div style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase;">Idempotency ID</div>
                    <code style="font-size: 0.75rem; font-family: var(--font-mono); color: var(--text-secondary); background: rgba(0,0,0,0.3); padding: 0.2rem 0.4rem; border-radius: 4px;">${req.idempotency_key}</code>
                  </div>
                ` : ''}
              </div>
              <div class="request-msg-content">${escapeHtml(req.original_message)}</div>
            </div>

            <!-- AI Recommendation block -->
            ${aiCardHtml}

            <!-- Notes card -->
            <div class="glass-card" style="margin-bottom: 1.5rem;">
              <h3 style="font-size: 1.1rem; font-weight: 600; margin-bottom: 1rem; display: flex; align-items: center; gap: 0.5rem;">
                📝 Internal Thread
              </h3>
              
              <div id="notes-list-container" class="notes-container">
                ${this.renderNotes()}
              </div>

              <!-- Note Form -->
              <form id="add-note-form" style="display: flex; gap: 0.75rem; border-top: 1px solid var(--border-color); padding-top: 1rem;">
                <input type="text" id="new-note-body" class="form-control" placeholder="Write an internal operational update..." required>
                <button type="submit" class="btn btn-primary" style="flex-shrink: 0;">Add Note</button>
              </form>
            </div>
          </div>

          <!-- Right Sidebar Operations -->
          <div class="glass-card controls-card">
            <div class="control-group">
              <h4>Update Status</h4>
              <select id="detail-status-select" class="form-control" style="background: rgba(0,0,0,0.4);">
                ${statusOptions}
              </select>
            </div>

            <!-- Event Timeline -->
            <div class="timeline-section">
              <h4>Audit Timeline</h4>
              <div class="timeline-container">
                ${this.renderTimeline()}
              </div>
            </div>
          </div>
        </div>
      </div>
    `;

    // Bind Controls
    document.getElementById('detail-status-select').addEventListener('change', async (e) => {
      await this.updateStatus(e.target.value);
    });

    document.getElementById('add-note-form').addEventListener('submit', async (e) => {
      e.preventDefault();
      const noteInput = document.getElementById('new-note-body');
      const body = noteInput.value.trim();
      if (!body) return;
      
      const success = await this.submitNote(body);
      if (success) {
        noteInput.value = '';
      }
    });

    const retryBtn = document.getElementById('detail-retry-btn');
    if (retryBtn) {
      retryBtn.addEventListener('click', () => this.retryAI());
    }

    const retryBtnInline = document.getElementById('detail-retry-btn-inline');
    if (retryBtnInline) {
      retryBtnInline.addEventListener('click', () => this.retryAI());
    }

    const runClassifyBtn = document.getElementById('detail-run-classify-btn');
    if (runClassifyBtn) {
      runClassifyBtn.addEventListener('click', () => this.retryAI());
    }
  },

  renderNotes() {
    const notes = this.request.notes || [];
    if (notes.length === 0) {
      return `<p style="font-size: 0.9rem; color: var(--text-secondary); text-align: center; padding: 1.5rem 0;">No notes have been logged on this request.</p>`;
    }

    return notes.map(note => {
      const date = new Date(note.created_at).toLocaleString();
      return `
        <div class="note-item">
          <div class="note-header">
            <span>${escapeHtml(note.author.username)} (${note.author.role})</span>
            <span>${date}</span>
          </div>
          <div class="note-body">${escapeHtml(note.body)}</div>
        </div>
      `;
    }).join('');
  },

  renderTimeline() {
    const events = this.request.events || [];
    if (events.length === 0) {
      return `<p style="font-size: 0.8rem; color: var(--text-muted);">No timeline logs available.</p>`;
    }

    // Show events with latest first or chronologically? Chronologically is default, but let's reverse for timeline view so latest status changes are at the top!
    const reversedEvents = [...events].reverse();

    return reversedEvents.map((event, index) => {
      const date = new Date(event.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
      let text = '';
      
      switch (event.event_type) {
        case 'created':
          text = `Request created by <span style="color:var(--text-primary); font-weight:500;">${event.actor}</span>`;
          break;
        case 'queued':
          text = `Enqueued for classification`;
          break;
        case 'classification_started':
          text = `AI analysis started using <span style="font-weight:550; text-transform:capitalize;">${event.metadata?.provider || 'provider'}</span>`;
          break;
        case 'classified':
          text = `AI classified as <span class="badge badge-${event.metadata?.category}" style="font-size:0.65rem; padding:0.1rem 0.3rem;">${event.metadata?.category}</span>`;
          break;
        case 'classification_failed':
          text = `<span style="color:#fda4af;">AI Classification failed</span>`;
          break;
        case 'status_changed':
          text = `Status changed from <span style="color:var(--text-secondary); font-weight:bold;">${event.old_value}</span> to <span style="color:var(--text-primary); font-weight:bold;">${event.new_value}</span> by <span style="font-weight:500;">${event.actor}</span>`;
          break;
        case 'note_added':
          text = `Note added by <span style="font-weight:550;">${event.actor}</span>`;
          break;
        default:
          text = `Event: ${event.event_type} by ${event.actor}`;
      }

      const isActive = index === 0; // Latest event

      return `
        <div class="timeline-item ${isActive ? 'active' : ''}">
          <div class="timeline-body">${text}</div>
          <div class="timeline-meta">${date}</div>
        </div>
      `;
    }).join('');
  },

  async updateStatus(status) {
    try {
      const updated = await api.patch(`/requests/${this.request.id}/status/`, { status });
      if (updated) {
        this.request = updated;
        this.render();
        showToast(`Request status updated to ${status.replace('_', ' ')}.`, 'success');
      }
    } catch (e) {
      console.error(e);
      showToast('Failed to update status.', 'error');
    }
  },

  async submitNote(body) {
    try {
      const updated = await api.post(`/requests/${this.request.id}/notes/`, { body });
      if (updated) {
        this.request = updated;
        this.render();
        showToast('Internal note added to thread.', 'success');
        return true;
      }
      return false;
    } catch (e) {
      console.error(e);
      showToast('Failed to add note.', 'error');
      return false;
    }
  },

  async retryAI() {
    try {
      const updated = await api.post(`/requests/${this.request.id}/retry-classification/`, {});
      if (updated) {
        this.request = updated;
        this.render();
        showToast('AI classification triggered.', 'info');
      }
    } catch (e) {
      console.error(e);
      showToast('Failed to trigger AI classifier.', 'error');
    }
  },

  patchRequestInDetail(updatedReq) {
    if (this.request && this.request.id === updatedReq.id) {
      // Refresh details directly
      this.request = updatedReq;
      this.render();
    }
  }
};
