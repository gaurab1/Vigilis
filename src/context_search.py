from codecs import ignore_errors
import os
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np
import requests
import time

PHONE_TRANSCRIPT_DIR = "outputs/phone_calls"
MESSAGE_DIR = "outputs/messages"
BROWSER_DIR = "C:/Users/gaura/Downloads/Scraper/Output"

def do_semantic_search(query, documents):
    model = SentenceTransformer('all-MiniLM-L6-v2')
    
    doc_embeddings = model.encode([doc['content'] for doc in documents])
    query_embedding = model.encode([query])[0]
    
    # Create FAISS index for efficient similarity search
    index = faiss.IndexFlatL2(len(query_embedding))
    index.add(np.array(doc_embeddings))
    
    # Find the most similar document
    distances, indices = index.search(np.array([query_embedding]), 1)
    
    if indices[0][0] != -1:
        return documents[indices[0][0]]
    else:
        return None

def match_filter(text, amount, to):
    score = 0
    score += text.count(amount)
    score += text.count(to)
    amount = float(amount)
    score += text.count(f"{amount:,}")
    score += text.count("{:,.2f}".format(amount))
    if amount == int(amount):
        score += text.count(str(amount))
    return score

def search_transcripts(amount, to):
    possible_matches = {}
    for folder_name in os.listdir(PHONE_TRANSCRIPT_DIR):
            count_score = 0
            if 'transcript.txt' not in os.listdir(os.path.join(PHONE_TRANSCRIPT_DIR, folder_name)):
                continue
            with open(os.path.join(PHONE_TRANSCRIPT_DIR, folder_name, 'transcript.txt'), 'r') as f:
                content = f.read()
                lines = content.split("\n")
                try:
                    number = folder_name.split('_from_')[1]
                except:
                    number = ''
                highlight_idx = -1
                for idx, line in enumerate(lines):
                    if amount in line:
                        highlight_idx = idx
                        break
                if (to in folder_name) or (to.replace('+1', '') in folder_name):
                    count_score += 1

                count_score += match_filter(content, amount, to)
                if count_score > 0:
                    possible_matches[folder_name] = {'type': 'phone', 'count': count_score, 
                                              'content': content, 'number': number, 'highlight': '\n'.join(lines[max(0, highlight_idx - 2):min(len(lines), highlight_idx + 3)]) if highlight_idx != -1 else ''}
    return sorted(possible_matches.items(), key=lambda x: x[1]['count'], reverse=True)

def search_messages(amount, to):
    possible_matches = {}
    for filename in os.listdir(MESSAGE_DIR):
        count_score = 0
        with open(os.path.join(MESSAGE_DIR, filename), 'r') as f:
            content = f.read()
            content = "Conversation with " + filename.split('.')[0] + "\n" + content
            lines = content.split('\n')
            highlight_message = ''
            for line in lines:
                if amount in line:
                    highlight_message = line
                    break
            if (to in filename) or (to.replace('+1', '') in filename):
                count_score += 1

            count_score += match_filter(content, amount, to)
            if count_score > 0:
                possible_matches[filename] = {'type': 'message', 'count': count_score, 
                                            'content': content, 'number': filename[:-3],'highlight': highlight_message}
    return sorted(possible_matches.items(), key=lambda x: x[1]['count'], reverse=True)

def search_browser(amount, to):
    possible_matches = {}
    for filename in os.listdir(BROWSER_DIR):
        count_score = 0
        with open(os.path.join(BROWSER_DIR, filename), 'r', errors='ignore') as f:
            contents = f.read()
            title = contents.split('\n')[0].split('Title: ')[1]
            url = contents.split('\n')[1].split('URL: ')[1]
            time = contents.split('\n')[2].split('Extracted on: ')[1]
            if (to in filename) or (to.replace('+1', '') in filename):
                count_score += 1

            count_score += match_filter(contents, amount, to)
            if count_score > 0:
                possible_matches[filename] = {'type': 'browser', 'count': count_score, 
                                        'content': contents, 'title': title, 'url': url, 'date': time}
    return sorted(possible_matches.items(), key=lambda x: x[1]['count'], reverse=True)

def summarize_context(context, highlight):
    api_url = "http://localhost:11434/api/generate"
    
    # Prepare the prompt similar to the OpenAI version
    # system_prompt = f"You are an expert summarizer, and can look for important information even in unorganized settings."
    user_prompt = f"You are given text from a scraped website that a user is about to make a purchase from, and you should understand whether the website is fraudulent or not, using crucial information present in the URL, title, and contents of the page. Think about the task in not more than 1-2 lines, and finally make a decision in a new line whether it involves fraudulent/normal transaction. The website contents are:\n {context[:3000]}"
    
    full_prompt = f"{user_prompt}"
    
    payload = {
        "model": "phi3:latest",
        "prompt": full_prompt,
        "stream": False,
    }

    print("Sending request...")
    start = time.time()
    response = requests.post(api_url, json=payload)
    response.raise_for_status()  # Raise exception for HTTP errors
    print(f"Received request... at {time.time() - start}")
    # Parse the response
    result = response.json()
        
    # Extract the generated text
    generated_text = result.get("response", "").strip()
    return generated_text

def find_context(amount, to, description):
    amount = str(amount).replace(',', '')
    transcript_results = search_transcripts(amount, to)
    message_results = search_messages(amount, to)
    browser_results = search_browser(amount, to)
    combined_results = [x[1] for x in (transcript_results + message_results + browser_results)]
    combined_results = sorted(combined_results, key=lambda x: x['count'], reverse=True)

    if description:
        description_results = do_semantic_search(description, combined_results)
        if description_results:
            item = description_results
    else:
        item = combined_results[0]
    if item['type'] == 'browser':
        return f"Found Context from <b>Browsing History</b>: <a href=\"{item['url']}\">{item['title']}</a> viewed at <b>{item['date']}</b><br>More info: {summarize_context(item['content'], item['title']).replace('\n', '<br>')}"
    elif item['type'] == 'message':
        return f"Found Context from <b>Text Conversation</b> with <b>{item['number']}</b><br>Highlighted text: {item['highlight']}"
    else:
        return f"Found Context from <b>Phone Call</b> with <b>{item['number']}</b><br>Highlighted conversation: {item['highlight']}"

if __name__ == '__main__':
    print(find_context(4.19, '+12243916520', "Thanks for the snacks!"))