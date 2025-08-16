import requests
import os

# Create models directory if it doesn't exist
os.makedirs('models', exist_ok=True)

url = 'https://huggingface.co/bartowski/janhq_Jan-v1-4B-GGUF/resolve/main/janhq_Jan-v1-4B-Q4_K_M.gguf'
filename = 'models/janhq_Jan-v1-4B-Q4_K_M.gguf'

print("Downloading Mistral 7B Instruct model...")
response = requests.get(url, stream=True, timeout=10)
response.raise_for_status()

with open(filename, 'wb') as f:
    for chunk in response.iter_content(chunk_size=8192):
        f.write(chunk)

print("Download complete!")