document.addEventListener('DOMContentLoaded', () => {
  const saveDirectoryInput = document.getElementById('saveDirectory');
  const enableToggle = document.getElementById('enableToggle');
  const saveNowButton = document.getElementById('saveNow');
  const statusDiv = document.getElementById('status');
  
  chrome.storage.local.get(['saveDirectory', 'isEnabled'], (data) => {
    saveDirectoryInput.value = data.saveDirectory || 'Scraper/Output';
    enableToggle.checked = data.isEnabled !== false; // Default to true if not set
  });
  
  saveDirectoryInput.addEventListener('change', () => {
    chrome.storage.local.set({ saveDirectory: saveDirectoryInput.value });
    updateStatus('Settings saved!');
  });
  
  enableToggle.addEventListener('change', () => {
    chrome.storage.local.set({ isEnabled: enableToggle.checked });
    updateStatus(enableToggle.checked ? 'Auto-save enabled!' : 'Auto-save disabled!');
  });
  
  // Handle manual save button
  saveNowButton.addEventListener('click', async () => {
    try {
      updateStatus('Extracting and saving text content...');
      
      // Get the current active tab
      const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
      
      // Request text content from the content script
      chrome.tabs.sendMessage(tab.id, { action: 'getText' }, (response) => {
        if (chrome.runtime.lastError) {
          updateStatus('Error: ' + chrome.runtime.lastError.message);
          return;
        }
        
        if (response && response.text) {
          // Send the text content to the background script to save
          chrome.runtime.sendMessage({
            action: 'saveText',
            text: response.text,
            url: tab.url,
            title: tab.title
          }, (saveResponse) => {
            if (saveResponse && saveResponse.success) {
              updateStatus('Text content saved successfully as: ' + saveResponse.filename);
            } else {
              updateStatus('Error saving text: ' + (saveResponse ? saveResponse.error : 'Unknown error'));
            }
          });
        } else {
          updateStatus('Error: Could not extract text content');
        }
      });
    } catch (error) {
      updateStatus('Error: ' + error.message);
      console.error(error);
    }
  });
  
  function updateStatus(message) {
    statusDiv.textContent = message;
    setTimeout(() => {
      if (statusDiv.textContent === message) {
        statusDiv.textContent = 'Ready to extract and save text content.';
      }
    }, 3000);
  }
});
