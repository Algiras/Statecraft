#!/usr/bin/env python3
"""
Chatterbox Audiobook Generator for Statecraft
Uses Resemble AI's Chatterbox local TTS with emotional control and paralinguistic tags.
Uses MPS (Apple Silicon GPU) with explicit garbage collection and cache flushing to prevent memory crashes.
"""

import os
import re
import sys
import gc
import subprocess
import torch

try:
    import torchaudio
    from chatterbox.tts import ChatterboxTTS
except ImportError:
    print("chatterbox-tts or torchaudio not found. Please run this script with:")
    print("uv run --with chatterbox-tts --with torchaudio generate_audio_chatterbox.py")
    sys.exit(1)

BOOK_PATH = "book.md"
OUTPUT_DIR = "audiobook_chatterbox"
FINAL_AUDIO = "statecraft_audiobook.mp3"

# Detect device: use MPS for speed, fallback to CPU
if torch.backends.mps.is_available():
    DEVICE = "mps"
elif torch.cuda.is_available():
    DEVICE = "cuda"
else:
    DEVICE = "cpu"

print(f"Using torch device: {DEVICE}")

# Conversational narrative transitions
TRANSITIONS = {
    (1, "pivot"): "[sigh] But then, the border police stepped in, showing that a flag is not a country.",
    (1, "investigation"): "To understand why the sandbox model fails, we have to look at the Westphalian system.",
    (1, "manual"): "Let's lay out the formal rules that define a state under international law.",

    (2, "pivot"): "Somaliland's success raises a fundamental question: why did it succeed where the U-N failed?",
    (2, "investigation"): "To see why, let's look at how the traditional legal system was integrated.",
    (2, "manual"): "Here is the structural handbook for aligning modern bureaucracy with cultural software.",
    
    (3, "pivot"): "[sigh] How did a bankrupt, newly independent Baltic nation build a currency with zero trust?",
    (3, "investigation"): "The answer lies in the mechanics of a currency board.",
    (3, "manual"): "Let's examine the technical blueprint for establishing monetary credibility.",
    
    (4, "pivot"): "Uniting Chinese, Malay, and Indian immigrants required a physical strategy.",
    (4, "investigation"): "Lee Kuan Yew's secret weapon was public housing quotas.",
    (4, "manual"): "Here are the design rules for shared spatial architecture that prevents self-segregation.",
    
    (5, "pivot"): "In a region torn by civil wars, Costa Rica's decision seemed suicidal. But it was strategic.",
    (5, "investigation"): "By eliminating the army, Costa Rica redirected funds to education and built diplomatic shields.",
    (5, "manual"): "Let's look at the policy options and coefficients for small-state defense.",
    
    (6, "pivot"): "Why does a landless order in Rome enjoy sovereignty while Taiwan is unrecognized?",
    (6, "investigation"): "Sovereignty is a social club. Let's look at the history of Taiwan's derecognition.",
    (6, "manual"): "Here is how a new state can navigate international law and establish bilateral representation.",
    
    (7, "pivot"): "Estonia realized they could not compete with tanks, so they went online.",
    (7, "investigation"): "They built the X-Road and data embassies to make the state impossible to occupy.",
    (7, "manual"): "Let's lay out the technical database exchange architectures and disaster recovery rules.",
    
    (8, "pivot"): "John Snow's work showed that public health is the primary security of a state.",
    (8, "investigation"): "Let's contrast Snow's empirical mapping with top-down quarantine blockades in history.",
    (8, "manual"): "Here is the containment protocol and surveillance framework for biosecurity.",
    
    (9, "pivot"): "Prussia designed public schools to forge national discipline and industrial capability.",
    (9, "investigation"): "Let's contrast the Prussian factory-school model with high-trust Finnish and digital Estonian models.",
    (9, "manual"): "Here is the implementation framework for modern human capital development.",
    
    (10, "pivot"): "Alexander Hamilton's whiskey tax proved that a state must extract resources to survive.",
    (10, "investigation"): "But extraction is a delicate balance of voluntary compliance and trust.",
    (10, "manual"): "Here are the guidelines for fiscal capacity, digital tax systems, and public debt limits.",
    
    (11, "pivot"): "France's Messmer Plan showed that energy security is the lifeblood of state sovereignty.",
    (11, "investigation"): "Let's contrast France's centralized nuclear transition with Germany's natural gas dependencies.",
    (11, "manual"): "Here is the strategic energy transition framework and grid resilience guide.",
    
    (12, "pivot"): "These stories show how all these pillars of statecraft are interconnected.",
    (12, "investigation"): "As we look to the future, climate change and A-I will challenge the Westphalian model.",
    (12, "manual"): "Here is the Accidental Founder's Checklist: an 18-question diagnostic self-test."
}

def get_heading_transition(chapter_index, subheading_text):
    text_lower = subheading_text.lower().strip()
    if not text_lower.startswith("#"):
        return None
    text_clean = re.sub(r"^#+\s+", "", text_lower)
    h_type = None
    if "pivot" in text_clean or "section ii" in text_clean or "spectrum" in text_clean or "living" in text_clean or "standardized" in text_clean or "collector" in text_clean or "unseen" in text_clean or "matrix" in text_clean:
        h_type = "pivot"
    elif "investigation" in text_clean or "section iii" in text_clean or "gates" in text_clean or "barbed" in text_clean or "prussian" in text_clean or "compliance" in text_clean or "energiewende" in text_clean or "future" in text_clean:
        h_type = "investigation"
    elif "manual" in text_clean or "checklist" in text_clean or "section iv" in text_clean or "framework" in text_clean or "audit" in text_clean or "guidelines" in text_clean:
        h_type = "manual"
    if h_type:
        return TRANSITIONS.get((chapter_index, h_type))
    return None

def make_audio_friendly(text):
    text = re.sub(r"^---[\s\S]*?---", "", text)
    text = re.sub(r"^##+\s+.*$", "", text, flags=re.MULTILINE)
    
    text = text.replace(r"\mathcal{PC} = \frac{\text{Internal Police Role} \times \text{Institutional Autonomy}}{\text{External Threat Salience} \times \text{Civilian Bureaucratic Strength}}",
                        "The Praetorian Coefficient is calculated by multiplying the internal police role by institutional autonomy, divided by the product of external threat salience and civilian bureaucratic strength.")
    text = text.replace(r"D = \frac{1}{2} \sum_{i=1}^{N} \left| \frac{a_i}{A} - \frac{b_i}{B} \right|",
                        "The Duncan Index of Dissimilarity is defined as half of the sum, across all neighborhoods, of the absolute difference between the proportion of group A in that neighborhood and the proportion of group B in the overall city.")
    
    text = text.replace(r"\mathcal{PC}", "the Praetorian Coefficient")
    text = text.replace(r"\mathcal{CSA}", "the Collective Security Arbitrage")
    text = text.replace(r"\mathcal{PDM}", "the Peace Dividend Multiplier")
    text = text.replace(r"\text{Internal Police Role}", "the internal police role")
    text = text.replace(r"\text{Institutional Autonomy}", "institutional autonomy")
    text = text.replace(r"\text{External Threat Salience}", "external threat salience")
    text = text.replace(r"\text{Civilian Bureaucratic Strength}", "civilian bureaucratic strength")
    text = text.replace(r"8:1", "eight to one")
    text = text.replace("96%", "ninety-six percent")
    text = text.replace("99%", "ninety-nine percent")
    text = text.replace("2%", "two percent")
    text = text.replace("60%", "sixty percent")
    text = text.replace("70%", "seventy percent")
    text = text.replace("80%", "eighty percent")
    text = text.replace("84%", "eighty-four percent")
    text = text.replace("22%", "twenty-two percent")
    text = text.replace("12%", "twelve percent")
    text = text.replace("74%", "seventy-four percent")
    text = text.replace("13%", "thirteen percent")
    text = text.replace("9%", "nine percent")
    text = text.replace("$1", "one dollar")
    text = text.replace("WPM", "words per minute")
    
    text = re.sub(r"\bEIP\b", "E I P", text)
    text = re.sub(r"\bHDB\b", "H D B", text)
    text = re.sub(r"\beID\b", "e I D", text)
    text = re.sub(r"\bOAS\b", "O A S", text)
    text = re.sub(r"\bUN\b", "U N", text)
    text = re.sub(r"\bSMOM\b", "S M O M", text)
    text = re.sub(r"\bPRC\b", "P R C", text)
    text = re.sub(r"\bSaaS\b", "S a a S", text)
    text = re.sub(r"\bKSI\b", "K S I", text)
    text = re.sub(r"\bOPEC\b", "O P E C", text)
    text = re.sub(r"\bPWR\b", "P W R", text)
    text = re.sub(r"\bEROI\b", "E R O I", text)
    
    text = re.compile(r'\[([^\]]+)\]\([^\)]+\)').sub(r'\1', text)
    text = text.replace(r"\newpage", "")
    text = text.replace(r"\pagebreak", "")
    text = text.replace("`", "")
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"\*([^*]+)\*", r"\1", text)
    
    text = re.sub(r"^\s*[-*+]\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*>\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = text.strip()
    return text

def clean_chapter_title(title):
    title = re.sub(r"^---[\s\S]*?---", "", title)
    title = re.sub(r"\s*\([^)]*\)", "", title)
    title = re.sub(r"\bChapter 1\b", "Chapter One", title)
    title = re.sub(r"\bChapter 2\b", "Chapter Two", title)
    title = re.sub(r"\bChapter 3\b", "Chapter Three", title)
    title = re.sub(r"\bChapter 4\b", "Chapter Four", title)
    title = re.sub(r"\bChapter 5\b", "Chapter Five", title)
    title = re.sub(r"\bChapter 6\b", "Chapter Six", title)
    title = re.sub(r"\bChapter 7\b", "Chapter Seven", title)
    title = re.sub(r"\bChapter 8\b", "Chapter Eight", title)
    title = re.sub(r"\bChapter 9\b", "Chapter Nine", title)
    title = re.sub(r"\bChapter 10\b", "Chapter Ten", title)
    title = re.sub(r"\bChapter 11\b", "Chapter Eleven", title)
    return title.strip()

def parse_chapters(file_path):
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Manuscript '{file_path}' not found.")
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    sections = re.split(r"^#\s+", content, flags=re.MULTILINE)
    chapters = []
    chapter_index = 0
    for section in sections:
        section = section.strip()
        if not section:
            continue
        lines = section.split("\n")
        title = lines[0].strip()
        body = "\n".join(lines[1:]).strip()
        if not body:
            continue
        safe_title = re.sub(r"[^\w\s-]", "", title.lower())
        safe_title = re.sub(r"[-\s]+", "_", safe_title).strip("_")
        chapters.append({
            "index": chapter_index,
            "title": title,
            "filename": f"{chapter_index:02d}_{safe_title}",
            "body": body
        })
        chapter_index += 1
    return chapters

def main():
    print(f"Loading Chatterbox TTS model on device: {DEVICE}...")
    model = ChatterboxTTS.from_pretrained(device=DEVICE)
    print("Model loaded successfully!")
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    temp_dir = os.path.join(OUTPUT_DIR, "temp")
    os.makedirs(temp_dir, exist_ok=True)
    
    print("Parsing manuscript...")
    chapters = parse_chapters(BOOK_PATH)
    print(f"Found {len(chapters)} chapters.")
    
    p_silence_path = os.path.join(temp_dir, "p_silence.wav")
    c_silence_path = os.path.join(temp_dir, "c_silence.wav")
    t_silence_path = os.path.join(temp_dir, "t_silence.wav")
    
    # Generate silence WAVs
    subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono", "-t", "1.8", p_silence_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono", "-t", "2.2", t_silence_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono", "-t", "3.5", c_silence_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    
    chapter_wav_files = []
    
    for ch in chapters:
        chapter_title = ch["title"]
        chapter_filename = ch["filename"]
        chapter_body = ch["body"]
        chapter_index = ch["index"]
        
        if chapter_filename.startswith("00_"):
            continue
            
        print(f"\nProcessing Chapter {chapter_index}: '{chapter_title}'...")
        
        paragraphs = [p.strip() for p in chapter_body.split("\n\n") if p.strip()]
        clean_title = clean_chapter_title(chapter_title)
        paragraphs.insert(0, clean_title + ".")
        
        paragraph_files = []
        
        for p_idx, raw_p in enumerate(paragraphs):
            transition = get_heading_transition(chapter_index, raw_p)
            if transition:
                p_text = transition
                silence_file = t_silence_path
            else:
                if raw_p.startswith("#"):
                    continue
                p_text = make_audio_friendly(raw_p)
                silence_file = p_silence_path
                
            if not p_text:
                continue
                
            p_file = os.path.join(temp_dir, f"{chapter_filename}_p{p_idx:03d}.wav")
            print(f"  -> Voicing paragraph {p_idx+1}/{len(paragraphs)}...")
            
            try:
                # Generate audio
                wav_tensor = model.generate(p_text)
                torchaudio.save(p_file, wav_tensor.cpu(), model.sr)
                
                paragraph_files.append(p_file)
                paragraph_files.append(silence_file)
                
                # MEMORY MANAGEMENT: Explicitly clean up tensors and flush cache after each paragraph
                del wav_tensor
                if DEVICE == "mps":
                    torch.mps.empty_cache()
                gc.collect()
                
            except Exception as e:
                print(f"  [ERROR] Failed generating paragraph {p_idx}: {e}")
                
        if paragraph_files:
            paragraph_files.pop()
            chapter_wav = os.path.join(OUTPUT_DIR, f"{chapter_filename}.wav")
            print(f"Merging paragraphs into chapter: {chapter_wav}...")
            
            concat_list = chapter_wav + ".list.txt"
            with open(concat_list, "w", encoding="utf-8") as f:
                for pf in paragraph_files:
                    f.write(f"file '{os.path.abspath(pf)}'\n")
            subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_list, "-c", "copy", chapter_wav], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            os.remove(concat_list)
            
            chapter_wav_files.append(chapter_wav)
            chapter_wav_files.append(c_silence_path)
            
            # Clean up paragraph temp files
            for pf in paragraph_files:
                if pf not in (p_silence_path, t_silence_path) and os.path.exists(pf):
                    os.remove(pf)
                    
    if chapter_wav_files:
        chapter_wav_files.pop()
        final_wav = os.path.join(OUTPUT_DIR, "statecraft_full_chatterbox.wav")
        print("\nMerging all chapters into full WAV...")
        
        concat_list = final_wav + ".list.txt"
        with open(concat_list, "w", encoding="utf-8") as f:
            for cw in chapter_wav_files:
                f.write(f"file '{os.path.abspath(cw)}'\n")
        subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_list, "-c", "copy", final_wav], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        os.remove(concat_list)
        
        print(f"Converting full WAV to final MP3: {FINAL_AUDIO}...")
        subprocess.run(["ffmpeg", "-y", "-i", final_wav, "-codec:a", "libmp3lame", "-qscale:a", "4", FINAL_AUDIO], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        
        if os.path.exists(final_wav):
            os.remove(final_wav)
        for cw in chapter_wav_files:
            if cw != c_silence_path and os.path.exists(cw):
                os.remove(cw)
                
        print(f"\n[SUCCESS] Chatterbox Audiobook generated as '{FINAL_AUDIO}'!")
    else:
        print("[ERROR] No audio files were generated.")

if __name__ == "__main__":
    main()
