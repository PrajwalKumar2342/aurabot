/**
 * Aura — AI Memory Assistant
 * Complete UI Controller
 */

class AuraApp {
    constructor() {
        this.currentView = 'dashboard';
        this.isCaptureEnabled = false;
        this.memories = [];
        this.config = {};
        this.expandedCards = new Set();
        this.init();
    }

    init() {
        this.setupNavigation();
        this.setupDashboard();
        this.setupMemories();
        this.setupChat();
        this.setupSettings();
        this.setupModal();
        this.setupKeyboardShortcuts();
        this.setupQuickEnhance();
        
        // Load initial data
        this.loadStatus();
        this.loadConfig();
        this.loadMemories();
        
        // Start polling
        this.startPolling();
        
        // Listen for backend events
        this.setupBackendEvents();
        
        console.log('✨ Aura initialized');
    }

    // ========================================
    // Quick Enhance
    // ========================================
    setupQuickEnhance() {
        const popup = document.getElementById('quick-enhance-popup');
        const overlay = document.getElementById('quick-enhance-overlay');
        const closeBtn = document.getElementById('quick-enhance-close');
        const enhanceBtn = document.getElementById('btn-enhance-text');
        const pasteBtn = document.getElementById('btn-paste-enhanced');
        const copyBtn = document.getElementById('btn-copy-enhanced');
        const floatingBtn = document.getElementById('floating-enhance-btn');
        
        // Close handlers
        const closePopup = () => {
            popup.classList.remove('active');
            overlay.classList.remove('active');
            this.resetQuickEnhance();
        };
        
        closeBtn?.addEventListener('click', closePopup);
        overlay?.addEventListener('click', closePopup);
        
        // Floating button click
        floatingBtn?.addEventListener('click', () => {
            this.openQuickEnhance('');
        });
        
        // Enhance button
        enhanceBtn?.addEventListener('click', async () => {
            const originalText = document.getElementById('quick-enhance-original').value;
            if (!originalText.trim()) return;
            
            enhanceBtn.disabled = true;
            enhanceBtn.innerHTML = '<div class="spinner"></div> Enhancing...';
            
            try {
                const result = await window.go.main.App.QuickEnhanceText(originalText);
                this.showEnhancedResult(result);
            } catch (error) {
                console.error('Enhancement failed:', error);
                this.showToast('Enhancement failed', 'error');
            } finally {
                enhanceBtn.disabled = false;
                enhanceBtn.innerHTML = `
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16">
                        <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/>
                    </svg>
                    Enhance with Memories
                `;
            }
        });
        
        // Copy button
        copyBtn?.addEventListener('click', async () => {
            const resultText = document.getElementById('quick-enhance-result').value;
            try {
                await navigator.clipboard.writeText(resultText);
                this.showToast('Copied to clipboard');
            } catch (err) {
                console.error('Copy failed:', err);
            }
        });
        
        // Paste button
        pasteBtn?.addEventListener('click', async () => {
            const resultText = document.getElementById('quick-enhance-result').value;
            try {
                await window.go.main.App.PasteEnhanced(resultText);
                this.showToast('Pasted to active window');
                closePopup();
            } catch (error) {
                console.error('Paste failed:', error);
                this.showToast('Failed to paste', 'error');
            }
        });
    }
    
    openQuickEnhance(text) {
        const popup = document.getElementById('quick-enhance-popup');
        const overlay = document.getElementById('quick-enhance-overlay');
        const originalTextarea = document.getElementById('quick-enhance-original');
        
        originalTextarea.value = text || '';
        this.resetQuickEnhance();
        
        popup.classList.add('active');
        overlay.classList.add('active');
        
        if (!text) {
            originalTextarea.focus();
        }
    }
    
    resetQuickEnhance() {
        document.getElementById('enhanced-section').style.display = 'none';
        document.getElementById('quick-enhance-footer').style.display = 'none';
        document.getElementById('quick-enhance-result').value = '';
        document.getElementById('quick-enhance-memories').innerHTML = '';
        document.getElementById('memories-count').textContent = '0 memories';
    }
    
    showEnhancedResult(result) {
        const resultTextarea = document.getElementById('quick-enhance-result');
        const memoriesContainer = document.getElementById('quick-enhance-memories');
        const memoriesBadge = document.getElementById('memories-count');
        
        resultTextarea.value = result.EnhancedPrompt || result.enhanced_prompt;
        
        const memoriesUsed = result.MemoriesUsed || result.memories_used || [];
        memoriesBadge.textContent = `${memoriesUsed.length} memories`;
        
        memoriesContainer.innerHTML = memoriesUsed.map(m => 
            `<div class="memory-chip" title="${this.escapeHtml(m)}">${this.escapeHtml(m.substring(0, 50))}...</div>`
        ).join('');
        
        document.getElementById('enhanced-section').style.display = 'block';
        document.getElementById('quick-enhance-footer').style.display = 'flex';
    }
    
    setupBackendEvents() {
        // Listen for hotkey-triggered events from backend
        if (window.runtime) {
            window.runtime.EventsOn('quickenhance:triggered', (data) => {
                this.openQuickEnhance(data.text);
            });
        }
    }

    // ========================================
    // Navigation
    // ========================================
    setupNavigation() {
        const navItems = document.querySelectorAll('.nav-item[data-view]');
        const views = document.querySelectorAll('.view');

        navItems.forEach(item => {
            item.addEventListener('click', () => {
                const viewName = item.dataset.view;
                
                // Update nav
                navItems.forEach(n => n.classList.remove('active'));
                item.classList.add('active');
                
                // Switch view
                views.forEach(v => v.classList.remove('active'));
                document.getElementById(`view-${viewName}`)?.classList.add('active');
                
                this.currentView = viewName;
                
                // Load view data
                if (viewName === 'memories') this.loadMemories();
                if (viewName === 'dashboard') this.loadMemories();
            });
        });
    }

    // ========================================
    // Dashboard
    // ========================================
    setupDashboard() {
        // New Memory button
        document.getElementById('btn-new-memory')?.addEventListener('click', () => {
            this.openModal();
        });
        
        // Start capture from empty state
        document.getElementById('btn-start-capture-empty')?.addEventListener('click', () => {
            this.toggleCapture(true);
        });
        
        // View all memories
        document.getElementById('btn-view-all-memories')?.addEventListener('click', () => {
            document.querySelector('[data-view="memories"]')?.click();
        });
        
        // Sidebar capture toggle
        document.getElementById('sidebar-capture-toggle')?.addEventListener('change', (e) => {
            this.toggleCapture(e.target.checked);
        });
    }

    // ========================================
    // Memories View
    // ========================================
    setupMemories() {
        // Search functionality
        const searchInput = document.getElementById('memories-search-input');
        const searchBtn = document.getElementById('btn-search');
        
        const doSearch = () => {
            const query = searchInput?.value?.trim();
            if (query) {
                this.searchMemories(query);
            } else {
                this.loadMemories();
            }
        };
        
        searchBtn?.addEventListener('click', doSearch);
        searchInput?.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') doSearch();
        });
    }

    // ========================================
    // Chat
    // ========================================
    setupChat() {
        const chatInput = document.getElementById('chat-input');
        const sendBtn = document.getElementById('btn-send-message');
        
        const sendMessage = async () => {
            const message = chatInput?.value?.trim();
            if (!message) return;
            
            // Add user message
            this.addChatMessage(message, 'user');
            chatInput.value = '';
            
            // Show typing
            this.showTypingIndicator();
            
            try {
                if (window.go?.main?.App?.Chat) {
                    const response = await window.go.main.App.Chat(message);
                    this.hideTypingIndicator();
                    this.addChatMessage(response, 'assistant');
                } else {
                    // Demo mode
                    setTimeout(() => {
                        this.hideTypingIndicator();
                        const demoResponses = [
                            "Based on your recent memories, you were working on product strategy and coding. Would you like me to summarize your key insights?",
                            "I see you've been reading about design principles. The key concepts you captured were Visibility, Feedback, and Constraints.",
                            "From your meeting notes, you discussed Q4 planning with action items for marketing and engineering teams."
                        ];
                        this.addChatMessage(demoResponses[Math.floor(Math.random() * demoResponses.length)], 'assistant');
                    }, 1000);
                }
            } catch (error) {
                this.hideTypingIndicator();
                this.addChatMessage('Sorry, I encountered an error. Please try again.', 'assistant');
            }
        };
        
        sendBtn?.addEventListener('click', sendMessage);
        chatInput?.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') sendMessage();
        });
    }

    addChatMessage(content, type) {
        const container = document.getElementById('chat-messages');
        if (!container) return;
        
        const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        
        const avatar = type === 'user' ? '' : `
            <div class="message-avatar">
                <svg viewBox="0 0 24 24" fill="none">
                    <defs>
                        <linearGradient id="grad-${Date.now()}" x1="2" y1="2" x2="22" y2="22">
                            <stop offset="0%" stop-color="#F5D76E"/>
                            <stop offset="100%" stop-color="#E8C84A"/>
                        </linearGradient>
                    </defs>
                    <circle cx="12" cy="12" r="10" fill="url(#grad-${Date.now()})"/>
                    <path d="M8 14s1.5 2 4 2 4-2 4-2M9 9h.01M15 9h.01" stroke="#1A1A1A" stroke-width="2" stroke-linecap="round"/>
                </svg>
            </div>
        `;
        
        const html = `
            <div class="chat-message ${type}">
                ${avatar}
                <div class="message-content">
                    <p>${this.escapeHtml(content)}</p>
                    <span class="message-time">${time}</span>
                </div>
            </div>
        `;
        
        container.insertAdjacentHTML('beforeend', html);
        container.scrollTop = container.scrollHeight;
    }

    showTypingIndicator() {
        const container = document.getElementById('chat-messages');
        if (!container) return;
        
        const indicator = document.createElement('div');
        indicator.id = 'typing-indicator';
        indicator.className = 'chat-message assistant';
        indicator.innerHTML = `
            <div class="message-avatar">
                <svg viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="10" fill="#F5D76E"/></svg>
            </div>
            <div class="message-content"><p>Thinking...</p></div>
        `;
        container.appendChild(indicator);
        container.scrollTop = container.scrollHeight;
    }

    hideTypingIndicator() {
        document.getElementById('typing-indicator')?.remove();
    }

    // ========================================
    // Settings
    // ========================================
    setupSettings() {
        // Tab navigation
        const tabs = document.querySelectorAll('.settings-tab');
        const panels = document.querySelectorAll('.settings-panel');
        
        tabs.forEach(tab => {
            tab.addEventListener('click', () => {
                const tabName = tab.dataset.tab;
                
                tabs.forEach(t => t.classList.remove('active'));
                tab.classList.add('active');
                
                panels.forEach(p => p.classList.remove('active'));
                document.getElementById(`panel-${tabName}`)?.classList.add('active');
            });
        });
        
        // Capture enabled toggle
        document.getElementById('setting-capture-enabled')?.addEventListener('change', (e) => {
            this.toggleCapture(e.target.checked);
        });
        
        // Capture interval slider
        const intervalSlider = document.getElementById('setting-capture-interval');
        intervalSlider?.addEventListener('input', (e) => {
            document.getElementById('display-capture-interval').textContent = `${e.target.value}s`;
        });
        
        // Quality slider
        const qualitySlider = document.getElementById('setting-capture-quality');
        qualitySlider?.addEventListener('input', (e) => {
            document.getElementById('display-capture-quality').textContent = `${e.target.value}%`;
        });
        
        // Save settings
        document.getElementById('btn-save-settings')?.addEventListener('click', () => {
            this.saveSettings();
        });
        
        // Reset settings
        document.getElementById('btn-reset-settings')?.addEventListener('click', () => {
            this.resetSettings();
        });
        
        // Permission buttons
        document.getElementById('btn-grant-accessibility')?.addEventListener('click', () => {
            this.showToast('Opening system settings...');
        });
        
        document.getElementById('btn-grant-screen')?.addEventListener('click', () => {
            this.showToast('Opening system settings...');
        });
    }

    // ========================================
    // Modal (New Memory)
    // ========================================
    setupModal() {
        const overlay = document.getElementById('modal-overlay');
        const modal = document.getElementById('modal-new-memory');
        
        // Close modal
        const closeModal = () => {
            overlay?.classList.remove('active');
            modal?.classList.remove('active');
            document.getElementById('memory-title').value = '';
            document.getElementById('memory-content').value = '';
        };
        
        document.getElementById('btn-close-modal')?.addEventListener('click', closeModal);
        document.getElementById('btn-cancel-memory')?.addEventListener('click', closeModal);
        overlay?.addEventListener('click', closeModal);
        
        // Save memory
        document.getElementById('btn-save-memory')?.addEventListener('click', async () => {
            const title = document.getElementById('memory-title')?.value;
            const content = document.getElementById('memory-content')?.value;
            
            if (!content?.trim()) {
                this.showToast('Please enter some content', 'error');
                return;
            }
            
            closeModal();
            this.showToast('Memory saved successfully');
            
            // Add to list
            const newMemory = {
                id: Date.now().toString(),
                content: content,
                timestamp: new Date().toISOString(),
                metadata: { context: title || 'Manual Entry' }
            };
            this.memories.unshift(newMemory);
            this.renderMemories();
        });
    }

    openModal() {
        document.getElementById('modal-overlay')?.classList.add('active');
        document.getElementById('modal-new-memory')?.classList.add('active');
        setTimeout(() => {
            document.getElementById('memory-title')?.focus();
        }, 100);
    }

    // ========================================
    // Backend Integration
    // ========================================
    async loadStatus() {
        try {
            if (window.go?.main?.App?.GetStatus) {
                const status = await window.go.main.App.GetStatus();
                this.updateStatusUI(status);
            } else {
                // Demo mode
                this.updateStatusUI({
                    running: true,
                    config: { capture_enabled: this.isCaptureEnabled, capture_interval: 30 }
                });
            }
        } catch (error) {
            console.error('Failed to load status:', error);
        }
    }

    updateStatusUI(status) {
        // Update sidebar status dots
        const llmDot = document.getElementById('status-llm');
        const memDot = document.getElementById('status-memory');
        const capDot = document.getElementById('status-capture');
        
        if (llmDot) llmDot.className = 'status-dot ' + (status.running ? 'online' : 'offline');
        if (memDot) memDot.className = 'status-dot ' + (status.running ? 'online' : 'offline');
        if (capDot) capDot.className = 'status-dot ' + (status.config?.capture_enabled ? 'online' : 'offline');
        
        // Update capture toggle
        this.isCaptureEnabled = status.config?.capture_enabled || false;
        const toggle = document.getElementById('sidebar-capture-toggle');
        if (toggle) toggle.checked = this.isCaptureEnabled;
        
        // Update status text
        const statusText = document.getElementById('capture-status-text');
        if (statusText) statusText.textContent = this.isCaptureEnabled ? 'Active' : 'Paused';
        
        // Update interval display
        const intervalDisplay = document.getElementById('capture-interval-display');
        if (intervalDisplay) {
            intervalDisplay.textContent = `Interval: ${status.config?.capture_interval || 30}s`;
        }
        
        // Update stats
        const intervalStat = document.getElementById('stat-interval');
        if (intervalStat) intervalStat.textContent = `${status.config?.capture_interval || 30}s`;
        
        const lastStat = document.getElementById('stat-last');
        if (lastStat && status.last_state) {
            lastStat.textContent = status.last_state.length > 20 
                ? status.last_state.substring(0, 20) + '...' 
                : status.last_state;
        }
    }

    async toggleCapture(enabled) {
        try {
            if (window.go?.main?.App?.ToggleCapture) {
                await window.go.main.App.ToggleCapture(enabled);
            }
            this.isCaptureEnabled = enabled;
            this.loadStatus();
            this.showToast(enabled ? 'Capture started' : 'Capture paused');
        } catch (error) {
            console.error('Failed to toggle capture:', error);
            this.showToast('Failed to toggle capture', 'error');
        }
    }

    async loadConfig() {
        try {
            if (window.go?.main?.App?.GetConfig) {
                const config = await window.go.main.App.GetConfig();
                this.config = config;
                this.populateSettings(config);
            }
        } catch (error) {
            console.error('Failed to load config:', error);
        }
    }

    populateSettings(config) {
        // Capture settings
        if (config.capture) {
            document.getElementById('setting-capture-enabled').checked = config.capture.enabled;
            document.getElementById('setting-capture-interval').value = config.capture.intervalSeconds || 30;
            document.getElementById('display-capture-interval').textContent = `${config.capture.intervalSeconds || 30}s`;
            document.getElementById('setting-capture-quality').value = config.capture.quality || 60;
            document.getElementById('display-capture-quality').textContent = `${config.capture.quality || 60}%`;
            document.getElementById('setting-process-on-capture').checked = config.capture.processOnCapture !== false;
        }
        
        // AI settings
        if (config.llm) {
            document.getElementById('setting-llm-url').value = config.llm.baseUrl || 'http://localhost:1234/v1';
            document.getElementById('setting-llm-model').value = config.llm.model || 'local-model';
        }
        
        if (config.app) {
            document.getElementById('setting-memory-window').value = config.app.memoryWindow || 10;
        }
        
        if (config.memory) {
            document.getElementById('setting-mem0-url').value = config.memory.baseUrl || 'http://localhost:8000';
        }
    }

    async saveSettings() {
        const settings = {
            capture: {
                enabled: document.getElementById('setting-capture-enabled')?.checked || false,
                intervalSeconds: parseInt(document.getElementById('setting-capture-interval')?.value || 30),
                quality: parseInt(document.getElementById('setting-capture-quality')?.value || 60),
                processOnCapture: document.getElementById('setting-process-on-capture')?.checked || false
            },
            llm: {
                baseUrl: document.getElementById('setting-llm-url')?.value || 'http://localhost:1234/v1',
                model: document.getElementById('setting-llm-model')?.value || 'local-model'
            },
            app: {
                memoryWindow: parseInt(document.getElementById('setting-memory-window')?.value || 10)
            },
            memory: {
                baseUrl: document.getElementById('setting-mem0-url')?.value || 'http://localhost:8000'
            }
        };
        
        try {
            if (window.go?.main?.App?.UpdateConfig) {
                await window.go.main.App.UpdateConfig(settings);
            }
            this.config = settings;
            this.showToast('Settings saved successfully');
            this.loadStatus();
        } catch (error) {
            console.error('Failed to save settings:', error);
            this.showToast('Failed to save settings', 'error');
        }
    }

    resetSettings() {
        if (confirm('Reset all settings to defaults?')) {
            document.getElementById('setting-capture-enabled').checked = true;
            document.getElementById('setting-capture-interval').value = 30;
            document.getElementById('display-capture-interval').textContent = '30s';
            document.getElementById('setting-capture-quality').value = 60;
            document.getElementById('display-capture-quality').textContent = '60%';
            document.getElementById('setting-process-on-capture').checked = true;
            document.getElementById('setting-memory-window').value = 10;
            this.showToast('Settings reset to defaults');
        }
    }

    async loadMemories() {
        try {
            if (window.go?.main?.App?.GetMemories) {
                const memories = await window.go.main.App.GetMemories(20);
                this.memories = memories;
            } else {
                // Demo data
                this.memories = [
                    {
                        id: '1',
                        content: 'The key insight from today\'s meeting is that we need to pivot our approach to focus on the enterprise market rather than SMBs. The data shows that enterprise customers have a 3x higher LTV and significantly lower churn rates.',
                        timestamp: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
                        metadata: { context: 'Product Strategy Notes', aiEnhanced: true }
                    },
                    {
                        id: '2',
                        content: 'Good design is actually a lot harder to notice than poor design, in part because good designs fit our needs so well that the design is invisible. Three key principles: Visibility, Feedback, and Constraints.',
                        timestamp: new Date(Date.now() - 4 * 60 * 60 * 1000).toISOString(),
                        metadata: { context: 'Design of Everyday Things' }
                    },
                    {
                        id: '3',
                        content: 'const useAsync = (asyncFunction, immediate = true) => { const [status, setStatus] = useState("idle"); const [value, setValue] = useState(null); const [error, setError] = useState(null); }',
                        timestamp: new Date(Date.now() - 8 * 60 * 60 * 1000).toISOString(),
                        metadata: { context: 'React Hook Pattern' }
                    },
                    {
                        id: '4',
                        content: 'Meeting with the team about Q4 planning. Key decisions: 1) Launch new feature by Nov 15, 2) Increase marketing budget by 40%, 3) Hire 3 new engineers.',
                        timestamp: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString(),
                        metadata: { context: 'Q4 Planning Meeting' }
                    }
                ];
            }
            this.renderMemories();
        } catch (error) {
            console.error('Failed to load memories:', error);
        }
    }

    async searchMemories(query) {
        // In real implementation, this would call a search API
        this.showToast(`Searching for "${query}"...`);
        // For now, just filter local memories
        const filtered = this.memories.filter(m => 
            m.content.toLowerCase().includes(query.toLowerCase()) ||
            m.metadata?.context?.toLowerCase().includes(query.toLowerCase())
        );
        this.renderMemories(filtered);
    }

    renderMemories(memoriesToRender = this.memories) {
        this.updateStats(memoriesToRender.length);
        
        const dashboardList = document.getElementById('dashboard-memories');
        const allList = document.getElementById('all-memories-list');
        
        const html = memoriesToRender.map((m, i) => this.createMemoryCard(m, i)).join('');
        
        if (dashboardList) {
            if (memoriesToRender.length === 0) {
                dashboardList.innerHTML = `
                    <div class="empty-state">
                        <div class="empty-icon">🧠</div>
                        <h3>No memories yet</h3>
                        <p>Start screen capture to begin recording your activities</p>
                        <button class="btn-primary" onclick="app.openModal()">Add Memory</button>
                    </div>
                `;
            } else {
                dashboardList.innerHTML = html;
            }
        }
        
        if (allList) {
            allList.innerHTML = html || `
                <div class="empty-state">
                    <div class="empty-icon">🔍</div>
                    <h3>No memories found</h3>
                    <p>Try a different search term</p>
                </div>
            `;
        }
        
        // Setup card expansion
        document.querySelectorAll('.memory-card').forEach(card => {
            card.addEventListener('click', (e) => {
                if (e.target.closest('.memory-actions') || e.target.closest('.btn-text')) return;
                this.toggleCardExpansion(card);
            });
        });
    }

    createMemoryCard(memory, index) {
        const date = new Date(memory.timestamp);
        const timeStr = date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        const isToday = new Date().toDateString() === date.toDateString();
        const displayTime = isToday ? `Today, ${timeStr}` : date.toLocaleDateString();
        
        const aiBadge = memory.metadata?.aiEnhanced ? '<span class="tag">AI Enhanced</span>' : '';
        
        return `
            <article class="memory-card" data-id="${memory.id}" style="animation: messageIn 0.3s ease ${index * 0.05}s both;">
                <div class="memory-header">
                    <div class="memory-icon">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M12 18v-5.25m0 0a6.01 6.01 0 001.5-.189m-1.5.189a6.01 6.01 0 01-1.5-.189m3.75 7.478a12.06 12.06 0 01-4.5 0m3.75 2.383a14.406 14.406 0 01-3 0M14.25 18v-.192c0-.983.658-1.823 1.508-2.316a7.5 7.5 0 10-7.517 0c.85.493 1.509 1.333 1.509 2.316V18"/>
                        </svg>
                    </div>
                    <div class="memory-meta">
                        <div class="memory-title">${this.escapeHtml(memory.metadata?.context || 'Memory')}</div>
                        <div class="memory-tags">${aiBadge}</div>
                    </div>
                </div>
                <div class="memory-preview">${this.escapeHtml(memory.content)}</div>
                <div class="memory-full hidden">
                    ${memory.metadata?.aiEnhanced ? `
                        <div class="ai-summary-box">
                            <div class="ai-summary-label">AI Summary</div>
                            <p>Strategic pivot recommended from SMB to Enterprise market. Key metrics: 3x LTV, lower churn.</p>
                        </div>
                    ` : ''}
                    <div class="memory-actions">
                        <button class="btn-text">Copy</button>
                        <button class="btn-text">Share</button>
                        <button class="btn-text primary">AI Enhance</button>
                    </div>
                </div>
                <div class="memory-footer">
                    <span>${displayTime}</span>
                    <span>•</span>
                    <span class="category-tag">#${memory.metadata?.context?.toLowerCase().replace(/\s+/g, '-') || 'general'}</span>
                </div>
            </article>
        `;
    }

    toggleCardExpansion(card) {
        const id = card.dataset.id;
        const full = card.querySelector('.memory-full');
        if (!full) return;
        
        const isExpanded = this.expandedCards.has(id);
        
        if (isExpanded) {
            full.classList.add('hidden');
            this.expandedCards.delete(id);
            card.classList.remove('expanded');
        } else {
            full.classList.remove('hidden');
            this.expandedCards.add(id);
            card.classList.add('expanded');
        }
    }

    updateStats(count) {
        const statEl = document.getElementById('stat-memories');
        if (statEl) statEl.textContent = count;
    }

    // ========================================
    // Utilities
    // ========================================
    startPolling() {
        setInterval(() => this.loadStatus(), 5000);
    }

    setupKeyboardShortcuts() {
        document.addEventListener('keydown', (e) => {
            // Cmd/Ctrl + K for search
            if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
                e.preventDefault();
                if (this.currentView === 'memories') {
                    document.getElementById('memories-search-input')?.focus();
                } else {
                    document.querySelector('[data-view="memories"]')?.click();
                }
            }
            
            // Cmd/Ctrl + N for new memory
            if ((e.metaKey || e.ctrlKey) && e.key === 'n') {
                e.preventDefault();
                this.openModal();
            }
            
            // Escape to close modal
            if (e.key === 'Escape') {
                document.getElementById('modal-overlay')?.classList.remove('active');
                document.getElementById('modal-new-memory')?.classList.remove('active');
            }
            
            // Cmd/Ctrl + Enter to save memory
            if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
                if (document.getElementById('modal-new-memory')?.classList.contains('active')) {
                    document.getElementById('btn-save-memory')?.click();
                }
            }
        });
    }

    showToast(message, type = 'success') {
        const toast = document.getElementById('toast');
        const toastMessage = document.getElementById('toast-message');
        const toastIcon = document.getElementById('toast-icon');
        
        if (!toast) return;
        
        toastMessage.textContent = message;
        toastIcon.innerHTML = type === 'error' 
            ? '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><path d="M6 18L18 6M6 6l12 12"/></svg>'
            : '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><path d="M4.5 12.75l6 6 9-13.5"/></svg>';
        
        toast.classList.add('show');
        
        setTimeout(() => {
            toast.classList.remove('show');
        }, 3000);
    }

    escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Initialize
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        window.app = new AuraApp();
    });
} else {
    window.app = new AuraApp();
}
