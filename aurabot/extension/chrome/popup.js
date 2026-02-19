// AuraBot Popup Script

const AURABOT_API_URL = 'http://localhost:7345';

async function checkStatus() {
  const statusDot = document.getElementById('statusDot');
  const statusText = document.getElementById('statusText');
  const content = document.getElementById('content');
  const error = document.getElementById('error');

  try {
    const response = await fetch(`${AURABOT_API_URL}/health`, {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' }
    });

    if (response.ok) {
      const data = await response.json();
      statusDot.classList.add('online');
      statusText.textContent = 'AuraBot is running';
      content.style.display = 'block';
      error.style.display = 'none';
    } else {
      throw new Error('Not OK');
    }
  } catch (e) {
    statusDot.classList.remove('online');
    statusText.textContent = 'AuraBot is offline';
    content.style.display = 'none';
    error.style.display = 'block';
  }
}

// Check status on load
checkStatus();

// Refresh status every 3 seconds
setInterval(checkStatus, 3000);
