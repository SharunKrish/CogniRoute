const websocket = {
  socket: null,
  reconnectAttempts: 0,
  maxReconnectDelay: 30000,
  
  connect() {
    const token = api.getAccessToken();
    if (!token) {
      this.updateStatusUI(false);
      return;
    }

    // Determine WS protocol
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsHost = window.location.host;
    const wsUrl = `${wsProtocol}//${wsHost}/ws/updates/?token=${token}`;

    console.log('Connecting to WebSocket updates channel...');
    this.socket = new WebSocket(wsUrl);

    this.socket.onopen = () => {
      console.log('WebSocket connected successfully.');
      this.reconnectAttempts = 0;
      this.updateStatusUI(true);
    };

    this.socket.onclose = (e) => {
      console.warn('WebSocket disconnected:', e.reason);
      this.updateStatusUI(false);
      
      // Auto-reconnect if not intentionally closed and still logged in
      if (api.getAccessToken()) {
        const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts), this.maxReconnectDelay);
        this.reconnectAttempts++;
        console.log(`Reconnecting to WebSocket in ${delay / 1000}s...`);
        setTimeout(() => this.connect(), delay);
      }
    };

    this.socket.onerror = (err) => {
      console.error('WebSocket error:', err);
      this.socket.close();
    };

    this.socket.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        this.handleEvent(payload);
      } catch (err) {
        console.error('Error handling WebSocket message:', err);
      }
    };
  },

  disconnect() {
    if (this.socket) {
      this.socket.close();
      this.socket = null;
    }
    this.updateStatusUI(false);
  },

  updateStatusUI(connected) {
    const badge = document.getElementById('ws-status');
    if (!badge) return;
    
    if (connected) {
      badge.className = 'ws-badge connected';
      badge.querySelector('.ws-status-text').textContent = 'Live Connected';
    } else {
      badge.className = 'ws-badge disconnected';
      badge.querySelector('.ws-status-text').textContent = 'Offline Sync';
    }
  },

  handleEvent(payload) {
    const { event, request } = payload;
    console.log(`Live Event Received: ${event}`, request);

    // 1. Toast Notification based on event type
    switch (event) {
      case 'request_created':
        showToast(`New Request #${request.id} submitted from ${request.customer_name}`, 'info');
        break;
      case 'classification_started':
        showToast(`Request #${request.id} classification started...`, 'info');
        break;
      case 'classification_completed':
        showToast(`Request #${request.id} classified as ${request.category_snapshot} (${request.priority_snapshot})`, 'success');
        break;
      case 'classification_failed':
        showToast(`Request #${request.id} AI route classification failed!`, 'error');
        break;
      case 'status_changed':
        showToast(`Request #${request.id} status updated to ${request.status.replace('_', ' ')}`, 'info');
        break;
      case 'note_added':
        showToast(`New internal note logged on Request #${request.id}`, 'info');
        break;
    }

    // 2. Reload Dashboard list and stats in real time
    if (window.location.hash === '' || window.location.hash === '#dashboard') {
      dashboard.loadRequests(dashboard.currentPage || 1);
    }

    // 3. Patch Detail view in real time (Fetch detail page again to get updated timeline/notes)
    if (window.location.hash.startsWith('#request/')) {
      const activeId = parseInt(window.location.hash.split('/')[1]);
      if (activeId === request.id) {
        // Trigger a reload of the request details using get API
        api.get(`/requests/${request.id}/`).then(detailedReq => {
          if (detailedReq) {
            detail.patchRequestInDetail(detailedReq);
          }
        });
      }
    }
  }
};
