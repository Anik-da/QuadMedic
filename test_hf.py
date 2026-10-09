import os
import requests
from dotenv import load_dotenv

load_dotenv()

HF_TOKEN = os.getenv("HF_TOKEN", "")
headers = {"Authorization": f"Bearer {HF_TOKEN}"}

# Test models
models = [
    "HuggingFaceH4/zephyr-7b-beta",
    "meta-llama/Llama-3.2-1B-Instruct",
    "mistralai/Mistral-7B-Instruct-v0.3",
    "facebook/bart-large-mnli"
]

for model in models:
    url = f"https://api-inference.huggingface.co/models/{model}"
    if "mnli" in model:
        payload = {"inputs": "I have headache", "parameters": {"candidate_labels": ["Neurological", "Respiratory"]}}
    else:
        payload = {"inputs": "<|system|>\nYou are a doctor.</s>\n<|user|>\nI have a headache. Any remedy?</s>\n<|assistant|>\n"}
    try:
        res = requests.post(url, headers=headers, json=payload, timeout=10)
        print(f"Model: {model}")
        print(f"Status: {res.status_code}")
        print(f"Response: {res.text[:300]}\n")
    except Exception as e:
        print(f"Model: {model} failed with: {e}\n")
