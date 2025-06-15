/** Enhanced Copilot Integration for Natural Health Group */
(function() {
    'use strict';
    
    // Configuration
    const COPILOT_CONFIG = {
        apiUrl: window.location.origin,
        websiteUrl: 'https://www.naturalhealthgroup.com.au',
        position: 'bottom-right',
        theme: 'light',
        autoGreeting: true,
        sessionStorage: true,
        analytics: true,
        maxRetries: 3,
        reconnectDelay: 5000,
        heartbeatInterval: 30000
    };
    
    // State management
    let copilotState = {
        isOpen: false,
        isConnected: false,
        isLoading: false,
        messageHistory: [],
        currentSession: null,
        reconnectAttempts: 0,
        pageContext: null,
        userPreferences: {}
    };
    
    // WebSocket connection
    let websocket = null;
    let heartbeatTimer = null;
    let reconnectTimer = null;
    
    // Initialize copilot when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initializeCopilot);
    } else {
        initializeCopilot();
    }
    
    function initializeCopilot() {
        // Create copilot elements
        createCopilotElements();
        
        // Set up event listeners
        setupEventListeners();
        
        // Initialize session tracking
        initializeSession();
        
        // Set up page context detection
        setupPageContextDetection();
        
        // Load user preferences
        loadUserPreferences();
        
        // Add welcome message for new visitors
        handleNewVisitorGreeting();
        
        // Initialize analytics if enabled
        if (COPILOT_CONFIG.analytics) {
            initializeAnalytics();
        }
        
        console.log('🌿 Natural Health Group Copilot initialized');
    }
    
    function createCopilotElements() {
        // Create trigger button if it doesn't exist
        if (!document.querySelector('.copilot-trigger')) {
            const triggerButton = document.createElement('button');
            triggerButton.className = 'copilot-trigger';
            triggerButton.innerHTML = `
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <path d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
                <span class="copilot-name">Zoe</span>
            `;
            triggerButton.setAttribute('aria-label', 'Chat with Zoe');
            triggerButton.title = 'Chat with Zoe - Your Natural Health Assistant';
            document.body.appendChild(triggerButton);
        }
        
        // Add notification badge for first-time visitors
        if (isFirstTimeVisitor()) {
            addNotificationBadge();
        }
        
        // Create chat container
        createChatContainer();
    }
    
    function createChatContainer() {
        const chatContainer = document.createElement('div');
        chatContainer.className = 'copilot-container';
        chatContainer.innerHTML = `
            <div class="copilot-header">
                <div class="copilot-header-info">
                    <div class="copilot-avatar">
                        <span>🌿</span>
                    </div>
                    <div class="copilot-header-text">
                        <div class="copilot-title">Zoe</div>
                        <div class="copilot-subtitle">Natural Health Assistant</div>
                    </div>
                </div>
                <div class="copilot-header-actions">
                    <button class="copilot-minimize" aria-label="Minimize chat">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M18 6L6 18M6 6l12 12"/>
                        </svg>
                    </button>
                </div>
            </div>
            
            <div class="copilot-messages" id="copilot-messages">
                <div class="copilot-loading" id="copilot-loading">
                    <div class="copilot-typing-indicator">
                        <span></span>
                        <span></span>
                        <span></span>
                    </div>
                    <div class="copilot-loading-text">Connecting to Zoe...</div>
                </div>
            </div>
            
            <div class="copilot-input-container">
                <div class="copilot-quick-actions" id="copilot-quick-actions">
                    <button class="copilot-quick-action" data-message="What services do you offer?">
                        Services
                    </button>
                    <button class="copilot-quick-action" data-message="I'd like to book a consultation">
                        Book Consultation
                    </button>
                    <button class="copilot-quick-action" data-message="Tell me about natural health products">
                        Products
                    </button>
                </div>
                <div class="copilot-input-wrapper">
                    <textarea 
                        id="copilot-input" 
                        class="copilot-input" 
                        placeholder="Ask me about natural health, products, or book a consultation..."
                        rows="1"
                        maxlength="1000"
                    ></textarea>
                    <button id="copilot-send" class="copilot-send" disabled>
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z"/>
                        </svg>
                    </button>
                </div>
                <div class="copilot-footer">
                    <div class="copilot-status" id="copilot-status">
                        <span class="copilot-status-dot"></span>
                        <span class="copilot-status-text">Connecting...</span>
                    </div>
                    <div class="copilot-powered">
                        Powered by Natural Health Group
                    </div>
                </div>
            </div>
        `;
        
        document.body.appendChild(chatContainer);
    }
    
    function setupEventListeners() {
        // Trigger button
        const triggerButton = document.querySelector('.copilot-trigger');
        if (triggerButton) {
            triggerButton.addEventListener('click', toggleCopilot);
        }
        
        // Minimize button
        const minimizeButton = document.querySelector('.copilot-minimize');
        if (minimizeButton) {
            minimizeButton.addEventListener('click', closeCopilot);
        }
        
        // Input handling
        const input = document.getElementById('copilot-input');
        const sendButton = document.getElementById('copilot-send');
        
        if (input) {
            input.addEventListener('input', handleInputChange);
            input.addEventListener('keypress', handleKeyPress);
            input.addEventListener('paste', handlePaste);
        }
        
        if (sendButton) {
            sendButton.addEventListener('click', sendMessage);
        }
        
        // Quick actions
        const quickActions = document.querySelectorAll('.copilot-quick-action');
        quickActions.forEach(action => {
            action.addEventListener('click', (e) => {
                const message = e.target.getAttribute('data-message');
                if (message) {
                    sendQuickMessage(message);
                }
            });
        });
        
        // Close on outside click
        document.addEventListener('click', (e) => {
            const container = document.querySelector('.copilot-container');
            const trigger = document.querySelector('.copilot-trigger');
            
            if (copilotState.isOpen && 
                !container.contains(e.target) && 
                !trigger.contains(e.target)) {
                closeCopilot();
            }
        });
        
        // Handle page visibility changes
        document.addEventListener('visibilitychange', handleVisibilityChange);
        
        // Handle beforeunload
        window.addEventListener('beforeunload', handleBeforeUnload);
    }
    
    function toggleCopilot() {
        if (copilotState.isOpen) {
            closeCopilot();
        } else {
            openCopilot();
        }
    }
    
    function openCopilot() {
        const container = document.querySelector('.copilot-container');
        const trigger = document.querySelector('.copilot-trigger');
        
        if (container && trigger) {
            copilotState.isOpen = true;
            container.classList.add('copilot-open');
            trigger.classList.add('copilot-active');
            
            // Focus input
            setTimeout(() => {
                const input = document.getElementById('copilot-input');
                if (input) input.focus();
            }, 300);
            
            // Connect if not already connected
            if (!copilotState.isConnected) {
                connectToCopilot();
            }
            
            // Hide notification badge
            hideNotificationBadge();
            
            // Track analytics
            trackEvent('copilot_opened');
        }
    }
    
    function closeCopilot() {
        const container = document.querySelector('.copilot-container');
        const trigger = document.querySelector('.copilot-trigger');
        
        if (container && trigger) {
            copilotState.isOpen = false;
            container.classList.remove('copilot-open');
            trigger.classList.remove('copilot-active');
            
            // Track analytics
            trackEvent('copilot_closed');
        }
    }
    
    function connectToCopilot() {
        if (copilotState.isConnected || copilotState.isLoading) {
            return;
        }
        
        copilotState.isLoading = true;
        updateConnectionStatus('connecting', 'Connecting to Zoe...');
        
        try {
            // Create WebSocket connection to Chainlit
            const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const wsUrl = `${wsProtocol}//${window.location.host}/ws`;
            
            websocket = new WebSocket(wsUrl);
            
            websocket.onopen = handleWebSocketOpen;
            websocket.onmessage = handleWebSocketMessage;
            websocket.onclose = handleWebSocketClose;
            websocket.onerror = handleWebSocketError;
            
        } catch (error) {
            console.error('Failed to connect to copilot:', error);
            handleConnectionError();
        }
    }
    
    function handleWebSocketOpen() {
        console.log('✅ Connected to Zoe');
        copilotState.isConnected = true;
        copilotState.isLoading = false;
        copilotState.reconnectAttempts = 0;
        
        updateConnectionStatus('connected', 'Online');
        hideLoadingIndicator();
        
        // Start heartbeat
        startHeartbeat();
        
        // Send initial context
        sendInitialContext();
        
        // Show welcome message if first visit
        if (isFirstTimeVisitor() && copilotState.messageHistory.length === 0) {
            showWelcomeMessage();
        }
    }
    
    function handleWebSocketMessage(event) {
        try {
            const data = JSON.parse(event.data);
            
            switch (data.type) {
                case 'message':
                    displayMessage(data.content, 'assistant');
                    break;
                case 'typing':
                    showTypingIndicator();
                    break;
                case 'stop_typing':
                    hideTypingIndicator();
                    break;
                case 'error':
                    handleMessageError(data.error);
                    break;
                default:
                    console.log('Unhandled message type:', data.type);
            }
        } catch (error) {
            console.error('Error parsing WebSocket message:', error);
        }
    }
    
    function handleWebSocketClose(event) {
        console.log('WebSocket connection closed:', event.code, event.reason);
        copilotState.isConnected = false;
        
        updateConnectionStatus('disconnected', 'Disconnected');
        stopHeartbeat();
        
        // Attempt to reconnect if not intentionally closed
        if (event.code !== 1000 && copilotState.reconnectAttempts < COPILOT_CONFIG.maxRetries) {
            scheduleReconnect();
        }
    }
    
    function handleWebSocketError(error) {
        console.error('WebSocket error:', error);
        handleConnectionError();
    }
    
    function handleConnectionError() {
        copilotState.isLoading = false;
        copilotState.isConnected = false;
        
        updateConnectionStatus('error', 'Connection failed');
        
        // Show error message
        displayMessage(
            "I'm having trouble connecting right now. Please try refreshing the page or contact us directly.",
            'system'
        );
    }
    
    function scheduleReconnect() {
        if (reconnectTimer) {
            clearTimeout(reconnectTimer);
        }
        
        copilotState.reconnectAttempts++;
        const delay = COPILOT_CONFIG.reconnectDelay * copilotState.reconnectAttempts;
        
        updateConnectionStatus('reconnecting', `Reconnecting in ${delay/1000}s...`);
        
        reconnectTimer = setTimeout(() => {
            if (copilotState.isOpen) {
                connectToCopilot();
            }
        }, delay);
    }
    
    function sendMessage() {
        const input = document.getElementById('copilot-input');
        const message = input.value.trim();
        
        if (!message || !copilotState.isConnected) {
            return;
        }
        
        // Display user message
        displayMessage(message, 'user');
        
        // Clear input
        input.value = '';
        updateSendButton();
        
        // Send to WebSocket
        sendToWebSocket({
            type: 'message',
            content: message,
            context: copilotState.pageContext,
            session: copilotState.currentSession
        });
        
        // Show typing indicator
        showTypingIndicator();
        
        // Track analytics
        trackEvent('message_sent', { message_length: message.length });
    }
    
    function sendQuickMessage(message) {
        const input = document.getElementById('copilot-input');
        input.value = message;
        sendMessage();
        
        // Hide quick actions after first use
        const quickActions = document.getElementById('copilot-quick-actions');
        if (quickActions) {
            quickActions.style.display = 'none';
        }
    }
    
    function sendToWebSocket(data) {
        if (websocket && websocket.readyState === WebSocket.OPEN) {
            websocket.send(JSON.stringify(data));
        } else {
            console.error('WebSocket not connected');
            handleConnectionError();
        }
    }
    
    function displayMessage(content, sender) {
        const messagesContainer = document.getElementById('copilot-messages');
        const messageElement = document.createElement('div');
        messageElement.className = `copilot-message copilot-message-${sender}`;
        
        if (sender === 'assistant') {
            messageElement.innerHTML = `
                <div class="copilot-message-avatar">🌿</div>
                <div class="copilot-message-content">
                    <div class="copilot-message-text">${formatMessage(content)}</div>
                    <div class="copilot-message-time">${formatTime(new Date())}</div>
                </div>
            `;
        } else if (sender === 'user') {
            messageElement.innerHTML = `
                <div class="copilot-message-content">
                    <div class="copilot-message-text">${escapeHtml(content)}</div>
                    <div class="copilot-message-time">${formatTime(new Date())}</div>
                </div>
            `;
        } else if (sender === 'system') {
            messageElement.className = 'copilot-message copilot-message-system';
            messageElement.innerHTML = `
                <div class="copilot-message-content">
                    <div class="copilot-message-text">${content}</div>
                </div>
            `;
        }
        
        messagesContainer.appendChild(messageElement);
        
        // Store in message history
        copilotState.messageHistory.push({
            content,
            sender,
            timestamp: new Date().toISOString()
        });
        
        // Scroll to bottom
        scrollToBottom();
        
        // Save to storage
        saveMessageHistory();
    }
    
    function formatMessage(content) {
        // Convert markdown-like formatting to HTML
        let formatted = escapeHtml(content);
        
        // Bold text
        formatted = formatted.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        
        // Links
        formatted = formatted.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>');
        
        // Line breaks
        formatted = formatted.replace(/\n/g, '<br>');
        
        // Emojis (preserve them)
        return formatted;
    }
    
    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    function showTypingIndicator() {
        const messagesContainer = document.getElementById('copilot-messages');
        
        // Remove existing typing indicator
        const existingIndicator = messagesContainer.querySelector('.copilot-typing-message');
        if (existingIndicator) {
            existingIndicator.remove();
        }
        
        const typingElement = document.createElement('div');
        typingElement.className = 'copilot-message copilot-message-assistant copilot-typing-message';
        typingElement.innerHTML = `
            <div class="copilot-message-avatar">🌿</div>
            <div class="copilot-message-content">
                <div class="copilot-typing-indicator">
                    <span></span>
                    <span></span>
                    <span></span>
                </div>
            </div>
        `;
        
        messagesContainer.appendChild(typingElement);
        scrollToBottom();
    }
    
    function hideTypingIndicator() {
        const typingIndicator = document.querySelector('.copilot-typing-message');
        if (typingIndicator) {
            typingIndicator.remove();
        }
    }
    
    function hideLoadingIndicator() {
        const loadingIndicator = document.getElementById('copilot-loading');
        if (loadingIndicator) {
            loadingIndicator.style.display = 'none';
        }
    }
    
    function updateConnectionStatus(status, text) {
        const statusElement = document.getElementById('copilot-status');
        if (statusElement) {
            const dot = statusElement.querySelector('.copilot-status-dot');
            const textElement = statusElement.querySelector('.copilot-status-text');
            
            if (dot && textElement) {
                dot.className = `copilot-status-dot copilot-status-${status}`;
                textElement.textContent = text;
            }
        }
    }
    
    function handleInputChange() {
        const input = document.getElementById('copilot-input');
        updateSendButton();
        autoResizeTextarea(input);
    }
    
    function handleKeyPress(event) {
        if (event.key === 'Enter' && !event.shiftKey) {
            event.preventDefault();
            sendMessage();
        }
    }
    
    function handlePaste(event) {
        // Handle paste events, could be extended for file uploads
        setTimeout(() => {
            updateSendButton();
            autoResizeTextarea(event.target);
        }, 0);
    }
    
    function updateSendButton() {
        const input = document.getElementById('copilot-input');
        const sendButton = document.getElementById('copilot-send');
        
        if (input && sendButton) {
            const hasContent = input.value.trim().length > 0;
            const isConnected = copilotState.isConnected;
            
            sendButton.disabled = !hasContent || !isConnected;
            sendButton.classList.toggle('copilot-send-active', hasContent && isConnected);
        }
    }
    
    function autoResizeTextarea(textarea) {
        textarea.style.height = 'auto';
        textarea.style.height = Math.min(textarea.scrollHeight, 120) + 'px';
    }
    
    function scrollToBottom() {
        const messagesContainer = document.getElementById('copilot-messages');
        if (messagesContainer) {
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
        }
    }
    
    function startHeartbeat() {
        heartbeatTimer = setInterval(() => {
            if (websocket && websocket.readyState === WebSocket.OPEN) {
                websocket.send(JSON.stringify({ type: 'ping' }));
            }
        }, COPILOT_CONFIG.heartbeatInterval);
    }
    
    function stopHeartbeat() {
        if (heartbeatTimer) {
            clearInterval(heartbeatTimer);
            heartbeatTimer = null;
        }
    }
    
    function formatTime(date) {
        return date.toLocaleTimeString('en-US', {
            hour: 'numeric',
            minute: '2-digit',
            hour12: true
        });
    }
    
    function initializeSession() {
        // Generate or retrieve session ID
        if (COPILOT_CONFIG.sessionStorage) {
            copilotState.currentSession = localStorage.getItem('copilot_session') || generateSessionId();
            localStorage.setItem('copilot_session', copilotState.currentSession);
        } else {
            copilotState.currentSession = generateSessionId();
        }
        
        // Load message history
        loadMessageHistory();
    }
    
    function generateSessionId() {
        return 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    }
    
    function setupPageContextDetection() {
        // Detect current page context
        const url = window.location.href;
        const title = document.title;
        const pathname = window.location.pathname;
        
        copilotState.pageContext = {
            url,
            title,
            pathname,
            timestamp: new Date().toISOString()
        };
        
        // Detect page-specific context
        if (pathname.includes('/products/')) {
            copilotState.pageContext.type = 'product';
        } else if (pathname.includes('/services/')) {
            copilotState.pageContext.type = 'service';
        } else if (pathname.includes('/about/')) {
            copilotState.pageContext.type = 'about';
        } else if (pathname.includes('/contact/')) {
            copilotState.pageContext.type = 'contact';
        } else {
            copilotState.pageContext.type = 'general';
        }
    }
    
    function sendInitialContext() {
        sendToWebSocket({
            type: 'context',
            context: copilotState.pageContext,
            session: copilotState.currentSession,
            userAgent: navigator.userAgent,
            timestamp: new Date().toISOString()
        });
    }
    
    function isFirstTimeVisitor() {
        return !localStorage.getItem('copilot_visited');
    }
    
    function markVisitorAsReturning() {
        localStorage.setItem('copilot_visited', 'true');
        localStorage.setItem('copilot_first_visit', new Date().toISOString());
    }
    
    function addNotificationBadge() {
        const trigger = document.querySelector('.copilot-trigger');
        if (trigger && !trigger.querySelector('.copilot-notification-badge')) {
            const badge = document.createElement('div');
            badge.className = 'copilot-notification-badge';
            badge.textContent = '!';
            trigger.appendChild(badge);
        }
    }
    
    function hideNotificationBadge() {
        const badge = document.querySelector('.copilot-notification-badge');
        if (badge) {
            badge.remove();
        }
        markVisitorAsReturning();
    }
    
    function showWelcomeMessage() {
        setTimeout(() => {
            displayMessage(
                "Hi there! I'm Zoe from Natural Health Group 🌿\n\n" +
                "I'm here to help you with natural health solutions, product recommendations, " +
                "and booking consultations with our expert team.\n\n" +
                "What can I help you with today? 😊",
                'assistant'
            );
        }, 1000);
    }
    
    function handleNewVisitorGreeting() {
        if (isFirstTimeVisitor()) {
            // Show a subtle animation or notification after a delay
            setTimeout(() => {
                const trigger = document.querySelector('.copilot-trigger');
                if (trigger) {
                    trigger.classList.add('copilot-pulse');
                    setTimeout(() => {
                        trigger.classList.remove('copilot-pulse');
                    }, 3000);
                }
            }, 3000);
        }
    }
    
    function saveMessageHistory() {
        if (COPILOT_CONFIG.sessionStorage) {
            const historyToSave = copilotState.messageHistory.slice(-20); // Keep last 20 messages
            localStorage.setItem('copilot_history', JSON.stringify(historyToSave));
        }
    }
    
    function loadMessageHistory() {
        if (COPILOT_CONFIG.sessionStorage) {
            try {
                const saved = localStorage.getItem('copilot_history');
                if (saved) {
                    const history = JSON.parse(saved);
                    copilotState.messageHistory = history;
                    
                    // Display saved messages
                    history.forEach(msg => {
                        if (msg.sender !== 'system') {
                            displayMessage(msg.content, msg.sender);
                        }
                    });
                }
            } catch (error) {
                console.error('Error loading message history:', error);
            }
        }
    }
    
    function loadUserPreferences() {
        try {
            const saved = localStorage.getItem('copilot_preferences');
            if (saved) {
                copilotState.userPreferences = JSON.parse(saved);
            }
        } catch (error) {
            console.error('Error loading user preferences:', error);
        }
    }
    
    function saveUserPreferences() {
        try {
            localStorage.setItem('copilot_preferences', JSON.stringify(copilotState.userPreferences));
        } catch (error) {
            console.error('Error saving user preferences:', error);
        }
    }
    
    function handleVisibilityChange() {
        if (document.hidden) {
            // Page is hidden - pause heartbeat
            stopHeartbeat();
        } else {
            // Page is visible - resume heartbeat if connected
            if (copilotState.isConnected) {
                startHeartbeat();
            }
        }
    }
    
    function handleBeforeUnload() {
        // Clean up WebSocket connection
        if (websocket) {
            websocket.close(1000, 'Page unloading');
        }
        
        // Clear timers
        stopHeartbeat();
        if (reconnectTimer) {
            clearTimeout(reconnectTimer);
        }
    }
    
    function initializeAnalytics() {
        // Initialize analytics tracking
        trackEvent('copilot_initialized', {
            page_url: window.location.href,
            user_agent: navigator.userAgent,
            timestamp: new Date().toISOString()
        });
    }
    
    function trackEvent(eventName, data = {}) {
        if (!COPILOT_CONFIG.analytics) return;
        
        // You can integrate with Google Analytics, Mixpanel, or other analytics services
        try {
            if (typeof gtag !== 'undefined') {
                gtag('event', eventName, data);
            }
            
            // Custom analytics endpoint
            if (COPILOT_CONFIG.analyticsEndpoint) {
                fetch(COPILOT_CONFIG.analyticsEndpoint, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        event: eventName,
                        data: data,
                        session: copilotState.currentSession,
                        timestamp: new Date().toISOString()
                    })
                }).catch(error => console.error('Analytics error:', error));
            }
        } catch (error) {
            console.error('Analytics tracking error:', error);
        }
    }
    
    // Expose public API
    window.NaturalHealthCopilot = {
        open: openCopilot,
        close: closeCopilot,
        sendMessage: (message) => {
            const input = document.getElementById('copilot-input');
            if (input) {
                input.value = message;
                sendMessage();
            }
        },
        isOpen: () => copilotState.isOpen,
        isConnected: () => copilotState.isConnected
    };
    
})();