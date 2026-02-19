// AuraBot Content Script - Injects enhancement button into AI chat interfaces
(function() {
  'use strict';

  // Configuration
  const AURABOT_API_URL = 'http://localhost:7345';
  const DEBOUNCE_DELAY = 300;

  // State
  let isEnhancing = false;
  let currentPlatform = detectPlatform();
  let observer = null;

  // Platform detection
  function detectPlatform() {
    const hostname = window.location.hostname;
    if (hostname.includes('chat.openai.com') || hostname.includes('chatgpt.com')) return 'chatgpt';
    if (hostname.includes('claude.ai')) return 'claude';
    if (hostname.includes('gemini.google.com')) return 'gemini';
    if (hostname.includes('perplexity.ai')) return 'perplexity';
    return 'unknown';
  }

  // Check if AuraBot app is running
  async function checkAppStatus() {
    try {
      const response = await fetch(`${AURABOT_API_URL}/health`, {
        method: 'GET',
        headers: { 'Content-Type': 'application/json' }
      });
      return response.ok;
    } catch (e) {
      return false;
    }
  }

  // Enhance prompt via AuraBot API
  async function enhancePrompt(prompt) {
    try {
      const response = await fetch(`${AURABOT_API_URL}/api/enhance`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          prompt: prompt,
          context: currentPlatform,
          max_memories: 5
        })
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      return data;
    } catch (error) {
      console.error('[AuraBot] Enhancement failed:', error);
      throw error;
    }
  }

  // Create enhancement button
  function createEnhanceButton() {
    const button = document.createElement('button');
    button.className = 'aurabot-enhance-btn';
    button.innerHTML = `
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/>
      </svg>
      <span>Enhance</span>
    `;
    button.title = 'Enhance with AuraBot memories';
    return button;
  }

  // Platform-specific selectors
  const PLATFORM_SELECTORS = {
    chatgpt: {
      textarea: 'textarea[placeholder*="Message"], #prompt-textarea, textarea[data-id="root"]',
      submitButton: 'button[data-testid="send-button"], button[aria-label="Send prompt"]'
    },
    claude: {
      textarea: 'div[contenteditable="true"], textarea[placeholder*="Message"], [data-testid="input-field"]',
      submitButton: 'button[aria-label="Send message"], button[type="submit"]'
    },
    gemini: {
      textarea: 'textarea[placeholder*="Ask"], textarea[placeholder*="Type"], rich-textarea',
      submitButton: 'button[aria-label="Send"], button.send-button'
    },
    perplexity: {
      textarea: 'textarea[placeholder*="Ask"], textarea[placeholder*="Type"], #search-input',
      submitButton: 'button[aria-label="Submit"], button[type="submit"]'
    }
  };

  // Find input element based on platform
  function findInputElement() {
    const selectors = PLATFORM_SELECTORS[currentPlatform];
    if (!selectors) return null;

    // Try primary selector
    let element = document.querySelector(selectors.textarea);
    if (element) return element;

    // Fallback: look for any textarea or contenteditable
    element = document.querySelector('textarea');
    if (element) return element;

    element = document.querySelector('[contenteditable="true"]');
    return element;
  }

  // Get text from input element
  function getInputText(element) {
    if (!element) return '';

    if (element.tagName === 'TEXTAREA' || element.tagName === 'INPUT') {
      return element.value;
    }

    if (element.isContentEditable) {
      return element.innerText || element.textContent;
    }

    // Handle rich text editors
    const textContent = element.querySelector('[data-text="true"]');
    if (textContent) {
      return textContent.innerText || textContent.textContent;
    }

    return element.innerText || element.textContent || '';
  }

  // Set text in input element
  function setInputText(element, text) {
    if (!element) return;

    if (element.tagName === 'TEXTAREA' || element.tagName === 'INPUT') {
      element.value = text;
      element.dispatchEvent(new Event('input', { bubbles: true }));
      element.dispatchEvent(new Event('change', { bubbles: true }));
    } else if (element.isContentEditable) {
      element.innerText = text;
      element.dispatchEvent(new InputEvent('input', { bubbles: true }));
    } else {
      // Handle rich text editors
      const textContent = element.querySelector('[data-text="true"]');
      if (textContent) {
        textContent.innerText = text;
        element.dispatchEvent(new InputEvent('input', { bubbles: true }));
      }
    }

    // Focus the element
    element.focus();
  }

  // Inject button into the page
  async function injectButton() {
    // Remove existing buttons
    const existing = document.querySelectorAll('.aurabot-enhance-btn');
    existing.forEach(btn => btn.remove());

    const inputElement = findInputElement();
    if (!inputElement) return;

    // Check if app is running
    const isAppRunning = await checkAppStatus();

    const button = createEnhanceButton();
    
    if (!isAppRunning) {
      button.classList.add('aurabot-offline');
      button.title = 'AuraBot app is not running. Please start the app.';
    }

    button.addEventListener('click', async (e) => {
      e.preventDefault();
      e.stopPropagation();

      if (isEnhancing) return;

      const currentText = getInputText(inputElement).trim();
      if (!currentText) {
        showNotification('Please enter a prompt first', 'warning');
        return;
      }

      if (!isAppRunning) {
        showNotification('AuraBot app is not running', 'error');
        return;
      }

      try {
        isEnhancing = true;
        button.classList.add('aurabot-loading');
        button.innerHTML = `<span class="aurabot-spinner"></span><span>Enhancing...</span>`;

        const result = await enhancePrompt(currentText);

        if (result.enhanced_prompt && result.enhanced_prompt !== currentText) {
          setInputText(inputElement, result.enhanced_prompt);
          showNotification(`Enhanced with ${result.memory_count} memories!`, 'success');
        } else {
          showNotification('No relevant memories found', 'info');
        }
      } catch (error) {
        showNotification('Failed to enhance prompt', 'error');
        console.error('[AuraBot]', error);
      } finally {
        isEnhancing = false;
        button.classList.remove('aurabot-loading');
        button.innerHTML = `
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/>
          </svg>
          <span>Enhance</span>
        `;
      }
    });

    // Position button based on platform
    positionButton(button, inputElement);
  }

  // Position button relative to input
  function positionButton(button, inputElement) {
    const container = inputElement.closest('form') || 
                      inputElement.closest('[data-testid="input-container"]') ||
                      inputElement.parentElement;

    if (container) {
      // Check if button already exists in container
      if (container.querySelector('.aurabot-enhance-btn')) return;

      container.style.position = 'relative';
      container.appendChild(button);
    } else {
      // Fallback: insert before input
      if (inputElement.parentElement && !inputElement.parentElement.querySelector('.aurabot-enhance-btn')) {
        inputElement.parentElement.style.position = 'relative';
        inputElement.parentElement.appendChild(button);
      }
    }
  }

  // Show notification
  function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `aurabot-notification aurabot-${type}`;
    notification.textContent = message;
    document.body.appendChild(notification);

    setTimeout(() => {
      notification.classList.add('aurabot-show');
    }, 10);

    setTimeout(() => {
      notification.classList.remove('aurabot-show');
      setTimeout(() => notification.remove(), 300);
    }, 3000);
  }

  // Debounce function
  function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
      const later = () => {
        clearTimeout(timeout);
        func(...args);
      };
      clearTimeout(timeout);
      timeout = setTimeout(later, wait);
    };
  }

  // Initialize
  async function init() {
    console.log('[AuraBot] Initializing on', currentPlatform);

    // Initial injection
    await injectButton();

    // Watch for DOM changes
    observer = new MutationObserver(debounce(() => {
      injectButton();
    }, DEBOUNCE_DELAY));

    observer.observe(document.body, {
      childList: true,
      subtree: true
    });

    // Listen for messages from popup
    chrome.runtime.onMessage?.addListener((request, sender, sendResponse) => {
      if (request.action === 'checkStatus') {
        checkAppStatus().then(status => {
          sendResponse({ isRunning: status });
        });
        return true;
      }
      if (request.action === 'enhance') {
        const inputElement = findInputElement();
        if (inputElement) {
          enhancePrompt(request.prompt).then(result => {
            sendResponse(result);
          }).catch(error => {
            sendResponse({ error: error.message });
          });
        }
        return true;
      }
    });
  }

  // Run initialization
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  // Cleanup on page unload
  window.addEventListener('beforeunload', () => {
    if (observer) {
      observer.disconnect();
    }
  });
})();
