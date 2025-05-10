from codecs import ignore_errors
import os
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np
import requests
import time
import random
import matplotlib.pyplot as plt

PHONE_TRANSCRIPT_DIR = "outputs/phone_calls"
MESSAGE_DIR = "outputs/messages"
BROWSER_DIR = "C:/Users/gaura/Downloads/Scraper/Output"

def do_semantic_search(query, documents):
    if not documents:
        return None
        
    model = SentenceTransformer('all-MiniLM-L6-v2')
    
    doc_embeddings = model.encode([doc['content'] for doc in documents])
    query_embedding = model.encode([query])[0]
    
    # Create FAISS index for efficient similarity search
    vector_dimension = len(query_embedding)
    index = faiss.IndexFlatL2(vector_dimension)
    
    if len(doc_embeddings.shape) != 2:
        print(f"Warning: Unexpected embedding shape: {doc_embeddings.shape}")
        # Reshape if it's a single vector
        if doc_embeddings.size == vector_dimension:
            doc_embeddings = doc_embeddings.reshape(1, vector_dimension)
    
    index.add(doc_embeddings)
    
    # Find the most similar document
    distances, indices = index.search(np.array([query_embedding]), 1)
    
    if indices.size > 0 and indices[0][0] != -1:
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
        score += text.count(str(int(amount)))
    return score

def get_testcases():
    matches = []
    with open('test_cases.txt', 'r') as f:
        content = f.read()
        lines = content.split("\n")
        within_case = False
        history = None
        amount = None
        description = None
        for line in lines:
            if "Amount: $" in line:
                within_case = True
                if history:
                    matches.append({'amount': amount, 'description': description, 'content': '\n'.join(history)})
                amount = line.split("Amount: $")[-1].strip()
            elif "Description: " in line:
                description = line.split("Description: ")[-1].strip()
            elif "History" in line:
                history = []
                continue
            else:
                if "Speaker 1:" in line or "Speaker 2:" in line:
                    history.append(line.strip())
        if history:
            matches.append({'amount': amount, 'description': description, 'content': '\n'.join(history)})

    return matches

def search_tests(amount, files):
    possible_matches = []
    for file in files:
        count = match_filter(file, amount, 'ibgvrtbsrs')
        if count > 0:
            possible_matches.append({'type': 'test', 'count': count, 'content': file})
    return possible_matches

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
                    highlight_message = line.replace("Input: ", "").replace("Output: ", "")
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
    response.raise_for_status()
    print(f"Received request... at {time.time() - start}")
    result = response.json()
    generated_text = result.get("response", "").strip()
    return generated_text

def find_context_test(amount, description, files):
    amount = str(amount).replace(',', '')
    possible_matches = search_tests(amount, files)
    possible_matches = sorted(possible_matches, key=lambda x: x['count'], reverse=True)
    if description:
        description_results = do_semantic_search(description, possible_matches)
        if description_results:
            item = description_results
        else:
            item = possible_matches[0]
    else:
        item = possible_matches[0]
    return item['content']

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

def run_tests():
    tests = get_testcases()
    num_files = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 110, 117]
    percentage_with_description = []
    percentage_without_description = []
    for num in num_files:
        print(num)
        curr_tests = random.sample(tests, num)
        files = [x['content'] for x in curr_tests]
        correct = 0
        for idx, test in enumerate(curr_tests):
            amount = test['amount']
            desc = test['description']
            expected_content = test['content']
            content = find_context_test(amount, desc, files)
            if content == expected_content:
                correct += 1
        percentage_with_description.append(correct / len(curr_tests))

        correct = 0
        for idx, test in enumerate(curr_tests):
            amount = test['amount']
            desc = None
            expected_content = test['content']
            content = find_context_test(amount, desc, files)
            if content == expected_content:
                correct += 1
        percentage_without_description.append(correct / len(curr_tests))

    print(percentage_with_description)
    print(percentage_without_description)

    plt.plot(num_files, percentage_with_description, label='With Semantic Search')
    plt.plot(num_files, percentage_without_description, label='Without Semantic Search')
    plt.xlabel("Number of documents")
    plt.ylabel("Correct Fraction")
    plt.title("Accuracy of searching right context in documents")
    plt.grid()
    plt.legend()
    plt.savefig("results.png")
    plt.show()

if __name__ == '__main__':
    print(find_context(4.19, '+12243916520', "Thanks for the snacks!"))
    # run_tests()
    
    
    
    
