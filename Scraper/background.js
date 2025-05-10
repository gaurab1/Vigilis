const DEFAULT_SAVE_DIRECTORY = "Scraper/Output";

chrome.runtime.onInstalled.addListener(() => {
  chrome.storage.local.set({
    saveDirectory: DEFAULT_SAVE_DIRECTORY,
    isEnabled: true
  });
});

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === "saveText") {
    chrome.storage.local.get(['saveDirectory', 'isEnabled'], (data) => {
      if (data.isEnabled) {
        saveTextToFile(request.text, data.saveDirectory, request.url, request.title)
          .then(filename => {
            sendResponse({ success: true, filename });
          })
          .catch(error => {
            console.error("Error saving text:", error);
            sendResponse({ success: false, error: error.toString() });
          });
      } else {
        sendResponse({ success: false, error: "Extension is disabled" });
      }
    });
    return true;
  }
});

// Function to save extracted text to a local file
async function saveTextToFile(textData, saveDirectory, pageUrl, pageTitle) {
  let filename = pageTitle ? 
    pageTitle.replace(/[^a-z0-9]/gi, '_').toLowerCase() : 
    new URL(pageUrl).hostname.replace(/[^a-z0-9]/gi, '_');
  
  const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
  filename = `${filename}_${timestamp}.txt`;
  
  if (saveDirectory) {
    filename = `${saveDirectory}/${filename}`;
  }
  
  const formattedText = formatTextContent(textData);
  
  await chrome.downloads.download({
    url: `data:text/plain;charset=utf-8,${encodeURIComponent(formattedText)}`,
    filename: filename,
    saveAs: false
  });
  
  return filename;
}

// Function to format the extracted text content nicely
function formatTextContent(textData) {
  function isTextContent(str) {
    const clean = str.replace(/\s+/g, '');
    
    if (clean.length === 0) return false;
    
    if (clean.length < 3) return false;
    
    if (/function\(|var |const |let |{.*}|\(.*\)|if\(|for\(|while\(|<script|<style/i.test(str)) return false;
    
    if (/<\/?[a-z][^>]*>/i.test(str)) return false;
    
    if (/data:image|blob:|url\(|https?:\/\/[^\/]*amazonaws\.com/.test(str)) return false;
    
    if (/\.[a-zA-Z]+\(|window\.|document\./.test(str)) return false;
    
    const alphaNum = (clean.match(/[a-z0-9]/gi) || []).length;
    if (alphaNum / clean.length < 0.4) return false;
    
    return true;
  }
  let output = "";
  
  // Add page title and URL
  output += `Title: ${textData.title}\n`;
  output += `URL: ${textData.url}\n`;
  output += `Extracted on: ${new Date(textData.timestamp).toLocaleString()}\n\n`;
  
  // Add paragraphs
  if (textData.paragraphs && textData.paragraphs.length > 0) {
    output += "=== CONTENT ===\n\n";
    textData.paragraphs.forEach(paragraph => {
      output += `${paragraph}\n\n`;
    });
  }
  
  // Add lists
  if (textData.lists && textData.lists.length > 0) {
    // Only include lists that have at least one item with real text
    const filteredLists = textData.lists.map(list => {
      const filteredItems = list.items.filter(isTextContent);
      return { ...list, items: filteredItems };
    }).filter(list => list.items.length > 0);
    if (filteredLists.length > 0) {
      output += "=== LISTS ===\n\n";
      filteredLists.forEach(list => {
        if (list.type === 'ol') {
          list.items.forEach((item, index) => {
            output += `${index + 1}. ${item}\n`;
          });
        } else {
          list.items.forEach(item => {
            output += `• ${item}\n`;
          });
        }
        output += "\n";
      });
    }
  }
  
  // Add tables
  if (textData.tables && textData.tables.length > 0) {
    output += "=== TABLES ===\n\n";
    textData.tables.forEach(table => {
      // Calculate column widths
      const columnWidths = [];
      table.forEach(row => {
        row.forEach((cell, colIndex) => {
          const cellLength = cell.length;
          if (!columnWidths[colIndex] || columnWidths[colIndex] < cellLength) {
            columnWidths[colIndex] = cellLength;
          }
        });
      });
      
      table.forEach((row, rowIndex) => {
        let rowOutput = "";
        row.forEach((cell, colIndex) => {
          rowOutput += cell.padEnd(columnWidths[colIndex] + 2, ' ');
        });
        output += rowOutput.trim() + "\n";
        
        // Add separator after header row
        if (rowIndex === 0) {
          let separator = "";
          columnWidths.forEach(width => {
            separator += "-".repeat(width) + "  ";
          });
          output += separator.trim() + "\n";
        }
      });
      output += "\n";
    });
  }
  
  return output;
}
