import aiohttp
import os
import json
from util.chatgpt_nhl import *
from datetime import datetime

bot_prompt = """Imagine you are Bryce Salvador, the former NHL player and current NHL analyst known for your excellent player and play breakdowns. Act as if you are responding and answering questions in the style of Bryce Salvador, using his tone, mannerisms, and personality. Feel free to showcase your knowledge of hockey and adopt a slightly biased perspective towards the New Jersey Devils, as Bryce Salvador is associated with the team.

You will be embodying Bryce Salvador as a Discord bot, receiving messages from various users. Each message you receive will begin with "user id says:", indicating the user who made the statement. It's important to keep track of who said what to maintain the conversation flow. Avoid starting the response with "user says" to maintain a natural flow of conversation. If necessary, you can mention or ping the user in your responses by using "<@user_id>"; the <> is required. If you want to refer to the user by name, you can use "<@user_id>"; the <> is required. Your ID is {}; do not use your own ID in your responses.

Please avoid referencing yourself as an AI, language model, or anything related to AI. Instead, always refer to yourself as Bryce Salvador. Additionally, ensure that your responses are appropriate for a general audience, without engaging in jokes or content that may not be suitable for a 13-year-old.

If you come across a situation where you don't know the answer or aren't familiar with a topic, it's acceptable to respond with phrases such as "I don't know" or "I don't know that" or "I don't know what you're talking about."

Now, let's get started and have some hockey discussions as Bryce Salvador!

Some knowledge you should know:
{}
"""

async def fetch_pinecone(query):
    headers = {
        'Authorization': 'Bearer ' + os.getenv('OPENAI_API_KEY', ''),
        'Content-Type': 'application/json',
    }

    json_data = {
        'input': query,
        'model': 'text-embedding-ada-002',
    }

    async with aiohttp.ClientSession() as session:
        async with session.post('https://api.openai.com/v1/embeddings', headers=headers, json=json_data) as response:
            response = await response.json()
        
        embedding = response['data'][0]['embedding']
    
    headers = {
        'Api-Key': os.getenv('PINECONE_API_KEY', ''),
        'Content-Type': 'application/json',
    }

    json_data = {
        'vector': embedding,
        'topK': 3,
        'includeValues': False,
        'includeMetadata': True,
    }
    async with aiohttp.ClientSession() as session:
        async with session.post('https://bryce-e0a3347.svc.us-west1-gcp-free.pinecone.io/query', headers=headers, json=json_data) as response:
            response = await response.json()
            print(response)
    
    context = ''

    for match in response['matches']:
        context += f'{match["metadata"]["text"]}\n'
    
    return context

async def check_message(message):
    flagged = False

    headers = {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer ' + os.getenv('OPENAI_API_KEY', ''),
    }

    json_data = {
        'input': message,
    }

    async with aiohttp.ClientSession() as session:
        async with session.post('https://api.openai.com/v1/moderations', headers=headers, json=json_data) as response:
            response = await response.json()

    flagged = response['results'][0]['flagged']

    category_scores = response['results'][0]['category_scores']
    cats = ''

    for category, score in category_scores.items():
        cats += f'{category}: {score}\n'

    return flagged, cats

async def call_chatgpt(messages):
    headers = {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer ' + os.getenv('OPENAI_API_KEY', ''),
    }
    

    json_data = {
        'model': 'gpt-3.5-turbo-0613',
        'messages': messages,
        'functions': functions,
        'max_tokens': 350,
        'temperature': 0.1,
    }

    try:
        timeout = aiohttp.ClientTimeout(total=30)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post('https://api.openai.com/v1/chat/completions', headers=headers, json=json_data) as response:
                response = await response.json()
    except:
        return None
    
    return response


async def prompt_chatgpt(message, bot_id):
    knowledge = await fetch_pinecone(message.content)
    today = datetime.now().strftime("%m/%d/%Y %H:%M:%S")
    knowledge = knowledge + "\nToday is " + today
    #print(bot_prompt.format(knowledge))
    messages_tmp = []
    system_message = [{
        'role': 'system',
        'content': bot_prompt.format(bot_id, knowledge),
    },]
    messages_tmp.extend(system_message)
    # ignore long messages
    if len(message.content) > 1000:
        return

    messages_tmp.append({
        'role': 'user',
        'content': f"{message.author.id} says: " + message.content,
    })

    try:
        # we have to loop until the model doesn't return a function call
        while True:
            response = await call_chatgpt(messages_tmp)
            response_message = response['choices'][0]['message']
            if response_message.get('function_call'):
                function_name = response_message["function_call"]["name"]
                function_to_call = functions_dict[function_name]

                if "arguments" in response_message["function_call"]:
                    function_args = json.loads(response_message["function_call"]["arguments"])
                    function_response = await function_to_call(**function_args)
                else:
                    function_response = await function_to_call()
                print(function_response)
            
                messages_tmp.append({
                    'role': 'function',
                    'name': function_name,
                    'content': function_response,
                })
            else:
                break

        resp = response_message['content']
    except Exception as e:
        resp = "Please try again."
        print(e)
        print(response)

    return resp# + '\n\n' + cats
