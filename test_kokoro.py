import os
import urllib.request
from kokoro_onnx import Kokoro

MODEL_URL = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files/kokoro-v0_19.onnx"
VOICES_URL = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files/voices.json"

MODEL_FILE = "kokoro-v0_19.onnx"
VOICES_FILE = "voices.json"

def download_file(url, filename):
    if not os.path.exists(filename):
        print(f"Downloading {filename} from GitHub Releases...")
        req = urllib.request.Request(
            url, 
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        )
        with urllib.request.urlopen(req) as response, open(filename, 'wb') as out_file:
            out_file.write(response.read())
        print(f"Finished downloading {filename}")
    else:
        print(f"{filename} already exists.")

def main():
    download_file(MODEL_URL, MODEL_FILE)
    download_file(VOICES_URL, VOICES_FILE)
    
    print("Initializing Kokoro...")
    try:
        kokoro = Kokoro(MODEL_FILE, VOICES_FILE)
        print("Kokoro successfully initialized!")
    except Exception as e:
        print(f"Error initializing Kokoro: {e}")

if __name__ == "__main__":
    main()
