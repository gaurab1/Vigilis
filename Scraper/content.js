function extractVisibleText() {
  const result = {
    title: document.title,
    url: window.location.href,
    timestamp: new Date().toISOString(),
    paragraphs: [],
    lists: [],
    tables: []
  };
  
  // Extract text from all paragraph elements
  document.querySelectorAll('p').forEach(paragraph => {
    if (isVisible(paragraph) && paragraph.textContent.trim()) {
      // Use getTextRecursive to get only the visible text without duplications
      const text = getTextRecursive(paragraph);
      if (text) {
        result.paragraphs.push(text);
      }
    }
  });
  
  // Extract text from all list elements
  document.querySelectorAll('ul, ol').forEach(list => {
    if (isVisible(list)) {
      const items = [];
      list.querySelectorAll('li').forEach(item => {
        if (isVisible(item)) {
          const text = getTextRecursive(item);
          if (text) {
            items.push(text);
          }
        }
      });
      
      if (items.length > 0) {
        result.lists.push({
          type: list.tagName.toLowerCase(),
          items: items
        });
      }
    }
  });
  
  // Extract text from all table elements
  document.querySelectorAll('table').forEach(table => {
    if (isVisible(table)) {
      const tableData = [];
      table.querySelectorAll('tr').forEach(row => {
        if (isVisible(row)) {
          const rowData = [];
          row.querySelectorAll('th, td').forEach(cell => {
            if (isVisible(cell)) {
              const text = getTextRecursive(cell);
              rowData.push(text);
            }
          });
          
          if (rowData.length > 0) {
            tableData.push(rowData);
          }
        }
      });
      
      if (tableData.length > 0) {
        result.tables.push(tableData);
      }
    }
  });
  
  const contentSelectors = 'article, section, div.content, div.main, div[role="main"], main, .main-content, .article-content, .post-content, .a-section';
  document.querySelectorAll(contentSelectors).forEach(container => {
    if (isVisible(container)) {
      if (container.tagName === 'TABLE' ||
          container.tagName === 'UL' ||
          container.tagName === 'OL') {
        return;
      }
      
      // Get text directly from the container, avoiding already captured elements
      const directTextElements = [];
      for (const child of container.children) {
        if (child.tagName !== 'P' && 
            child.tagName !== 'TABLE' && 
            child.tagName !== 'UL' &&
            child.tagName !== 'OL' && 
            isVisible(child)) {
          const text = getTextRecursive(child);
          if (text && text.length > 3 && isTextContent(text)) {
            directTextElements.push(text);
          }
        }
      }
      
      // Add any found content to paragraphs
      directTextElements.forEach(text => {
        if (!result.paragraphs.includes(text)) {
          result.paragraphs.push(text);
        }
      });
    }
  });
  
  if (result.paragraphs.length === 0 && 
      result.lists.length === 0 && result.tables.length === 0) {
    
    const textNodes = [];
    const walker = document.createTreeWalker(
      document.body,
      NodeFilter.SHOW_TEXT,
      { acceptNode: node => isVisible(node.parentElement) ? NodeFilter.FILTER_ACCEPT : NodeFilter.FILTER_REJECT },
      false
    );
    
    while (walker.nextNode()) {
      const text = walker.currentNode.textContent.trim();
      if (text) {
        textNodes.push(text);
      }
    }
    
    let currentParagraph = "";
    textNodes.forEach(text => {
      if (text.length > 50 || text.endsWith('.') || text.endsWith('!') || text.endsWith('?')) {
        currentParagraph += " " + text;
        if (currentParagraph.trim()) {
          result.paragraphs.push(currentParagraph.trim());
          currentParagraph = "";
        }
      } else {
        currentParagraph += " " + text;
      }
    });
    
    if (currentParagraph.trim()) {
      result.paragraphs.push(currentParagraph.trim());
    }
  }
  
  return result;
}

function isVisible(element) {
  if (!element) return false;
  
  // Check for aria-hidden attribute
  // if (element.getAttribute('aria-hidden') === 'true') return false;
  
  // Check for off-screen classes (common in e-commerce sites like Amazon)
  // if (element.classList && 
  //     (element.classList.contains('a-offscreen') || 
  //      element.classList.contains('visually-hidden') || 
  //      element.classList.contains('sr-only'))) return false;
  
  // Check computed style properties
  const style = window.getComputedStyle(element);
  return style.display !== 'none' && 
         style.visibility !== 'hidden' && 
        //  style.opacity !== '0' &&
         element.offsetWidth > 0 && 
         element.offsetHeight > 0;
}

function getTextRecursive(element) {
  if (!element) return '';
  if (!isVisible(element)) return '';
  
  if (element.children.length === 0 && isVisible(element)) {
    return element.textContent.trim();
  }
  
  // Get only the direct text nodes (not including child elements)
  let text = '';
  for (const node of element.childNodes) {
    // Node.TEXT_NODE equals 3
    if (node.nodeType === 3) {
      text += node.textContent;
    }
  }
  
  // Add text from child elements recursively
  for (const child of element.children) {
    text += getTextRecursive(child);
  }
  
  return text.trim();
}
window.addEventListener('load', () => {
  setTimeout(() => {
    const textContent = extractVisibleText();
    const currentUrl = window.location.href;
    const pageTitle = document.title;
    
    chrome.runtime.sendMessage({
      action: "saveText",
      text: textContent,
      url: currentUrl,
      title: pageTitle
    }, response => {
      if (response && response.success) {
        console.log("Text content successfully saved to file:", response.filename);
      } else {
        console.error("Failed to save text content:", response ? response.error : "Unknown error");
      }
    });
  }, 1000);
});

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === "getText") {
    const textContent = extractVisibleText();
    sendResponse({ text: textContent });
  }
  return true;
});


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