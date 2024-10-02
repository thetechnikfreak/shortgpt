import json
import os
import re
from time import sleep, time
import requests
import openai
import tiktoken
import yaml

from shortGPT.config.api_db import ApiKeyManager


def num_tokens_from_messages(texts, model="gpt-3.5-turbo-0301"):
    """Returns the number of tokens used by a list of messages."""
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        encoding = tiktoken.get_encoding("cl100k_base")
    if model == "gpt-3.5-turbo-0301":  # note: future models may deviate from this
        if isinstance(texts, str):
            texts = [texts]
        score = 0
        for text in texts:
            score += 4 + len(encoding.encode(text))
        return score
    else:
        raise NotImplementedError(f"""num_tokens_from_messages() is not presently implemented for model {model}.
        See https://github.com/openai/openai-python/blob/main/chatml.md for information""")


def extract_biggest_json(string):
    json_regex = r"\{(?:[^{}]|(?R))*\}"
    json_objects = re.findall(json_regex, string)
    if json_objects:
        return max(json_objects, key=len)
    return None


def get_first_number(string):
    pattern = r'\b(0|[1-9]|10)\b'
    match = re.search(pattern, string)
    if match:
        return int(match.group())
    else:
        return None


def load_yaml_file(file_path: str) -> dict:
    """Reads and returns the contents of a YAML file as dictionary"""
    return yaml.safe_load(open_file(file_path))


def load_json_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        json_data = json.load(f)
    return json_data


def load_yaml_prompt(file_path):
    json_template = load_yaml_file(file_path)
    return json_template['chat_prompt'], json_template['system_prompt']


def open_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as infile:
        return infile.read()

def gpt3Turbo_completion(chat_prompt="", system="You are an AI that can give the answer to anything", temp=0.7, model="gpt-3.5-turbo", max_tokens=1000, remove_nl=True, conversation=None):
    openai.api_key = ApiKeyManager.get_api_key("OPENAI")
    openai.api_base = 'https://fresedgpt.space/v1/'
    max_retry = 5
    retry = 0
    while True:
        try:
            if conversation:
                messages = conversation
            else:
                messages = [
                    {"role": "system", "content": system},
                    {"role": "user", "content": chat_prompt}
                ]  
            safeInput = system + "\n" + chat_prompt
            print("------------\n")
            print(safeInput)
            print("-------------\n")
            data = {
                "prompt": safeInput
            }
            payload = json.dumps(data)

            # Set the headers
            headers = {
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/110.0",
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "en-US,en;q=0.5",
                "Content-Type": "application/json",
                "Origin": "https://chatbot.theb.ai",
                "Referer": "https://chatbot.theb.ai/"
            }
            url = "https://chatbot.theb.ai/api/chat-process"
            response = requests.post(url, data=payload, headers=headers)
            if response.status_code == 200:
                response_text = response.text

                # Find the last JSON string in the response text
                json_strings = response_text.strip().split('\n')
                last_json_string = json_strings[-1]

                response_json = json.loads(last_json_string)
                text = response_json['text']
            else:
                print("Error:", response.status_code)

            print(text)
            print("--------------\n")    
            #--------------------
            if remove_nl:
                text = re.sub('\s+', ' ', text)
            filename = '%s_gpt3.txt' % time()
            if not os.path.exists('.logs/gpt_logs'):
                os.makedirs('.logs/gpt_logs')
            with open('.logs/gpt_logs/%s' % filename, 'w', encoding='utf-8') as outfile:
                outfile.write(f"System prompt: ===\n{system}\n===\n"+f"Chat prompt: ===\n{chat_prompt}\n===\n" + f'RESPONSE:\n====\n{text}\n===\n')
            return text
        except Exception as oops:
            retry += 1
            if retry >= max_retry:
                raise Exception("GPT3 error: %s" % oops)
            print('Error communicating with OpenAI:', oops)
            sleep(1)
