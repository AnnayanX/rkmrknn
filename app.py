from flask import Flask, request, jsonify, render_template
import os
import requests
import time

app = Flask(__name__)

# Access environment variables set in Vercel
TELEGRAM_API_TOKEN = os.getenv('TELEGRAM_API_TOKEN')
OPENAI_ENDPOINT = os.getenv('OPENAI_ENDPOINT')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
CHAT_ID = os.getenv('CHAT_ID')  # Chat ID for sending error messages

TELEGRAM_API_URL = f'https://api.telegram.org/bot{TELEGRAM_API_TOKEN}'

def send_message(chat_id, text):
    url = f'{TELEGRAM_API_URL}/sendMessage'
    response = requests.post(url, data={'chat_id': chat_id, 'text': text})
    return response.json()

def get_openai_response(query, retries=3, backoff_factor=1):
    headers = {
        'Content-Type': 'application/json',
        'api-key': OPENAI_API_KEY,
    }

    # Define maximum token limits
    MAX_TOKENS = 4096
    MAX_INPUT_TOKENS = MAX_TOKENS - 800  # Reserve 800 tokens for output

    # Trim the query to fit within the input token limit
    input_tokens = count_tokens(query)
    if input_tokens > MAX_INPUT_TOKENS:
        query = ' '.join(query.split()[:MAX_INPUT_TOKENS])  # Trim the query to fit

    payload = {
        'messages': [
            {
                'role': 'system',
                'content': [
                    {
                        'type': 'text',
                        'text': 'You are an AI assistant that helps people find information.'
                    }
                ]
            },
            {
                'role': 'user',
                'content': [
                    {
                        'type': 'text',
                        'text': query
                    }
                ]
            }
        ],
        'temperature': 0.7,
        'top_p': 0.95,
        'max_tokens': 800
    }

    url = OPENAI_ENDPOINT

    for attempt in range(retries):
        try:
            response = requests.post(url, headers=headers, json=payload)
            if response.status_code == 429:  # Rate limit error
                wait_time = backoff_factor * (2 ** attempt)  # Exponential backoff
                print(f"Rate limit exceeded. Waiting for {wait_time} seconds.")
                time.sleep(wait_time)
                continue  # Retry the request
            response.raise_for_status()  # Raise an HTTPError for other bad responses
            response_data = response.json()
            answer = response_data.get('choices', [{}])[0].get('message', {}).get('content', 'No response content')
            return answer
        except requests.RequestException as e:
            if attempt == retries - 1:  # Last attempt
                send_message(CHAT_ID, f"Failed to make the request. Error: {e}")
                return f"Failed to make the request. Error: {e}"
            wait_time = backoff_factor * (2 ** attempt)  # Exponential backoff
            print(f"Request failed. Waiting for {wait_time} seconds before retrying.")
            time.sleep(wait_time)

    return "Failed to get a response after several attempts."

def count_tokens(text):
    # Simple token count; for accurate token counting, use a tokenizer
    return len(text.split())

@app.route('/')
def index():
    # Render index.html and pass any variables if needed
    return render_template('index.html', username='Dhanrakshak')

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()

    # Extract chat_id and message text
    chat_id = data.get('message', {}).get('chat', {}).get('id')
    text = data.get('message', {}).get('text', '')

    if not chat_id or not text:
        send_message(CHAT_ID, "Received invalid data in webhook")
        return jsonify(success=False), 400

    try:
        # Check if the message starts with the '/ask' command
        if text.startswith('/ask'):
            query = text[len('/ask '):].strip()
            if query:
                answer = get_openai_response(query)
                send_message(chat_id, answer)
            else:
                send_message(chat_id, "Please provide a query after the /ask command.")
        elif text == '/start':
            send_message(chat_id, "I am working")
    except Exception as e:
        send_message(CHAT_ID, f"Error processing message: {e}")

    return jsonify(success=True)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
