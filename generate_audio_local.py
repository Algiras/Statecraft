#!/usr/bin/env python3
"""
Local Audiobook Generator for Statecraft
Uses MLX-Audio natively on Apple Silicon to run offline TTS (using Qwen3-TTS).
Applies audio-friendly text translation (math, acronyms, lists), replaces subheadings
with custom context-aware conversational transitions, and injects pacing silence.
"""

import os
import re
import sys
import subprocess

# Hugging Face MLX model to use
MODEL_NAME = "mlx-community/Qwen3-TTS-12Hz-1.7B-Base-8bit"
BOOK_PATH = "book.md"
LOCAL_OUTPUT_DIR = "audiobook_local"
FINAL_LOCAL_AUDIO = "statecraft_audiobook_local.mp3"

# Silence parameters
PARAGRAPH_SILENCE_DURATION = 1.8  # seconds
TRANSITION_SILENCE_DURATION = 2.2  # seconds
CHAPTER_SILENCE_DURATION = 3.5  # seconds
SAMPLE_RATE = 24000  # Default Qwen3-TTS output sample rate

# Transitions map: (chapter_index, heading_type) -> transition_text
TRANSITIONS = {
    # Intro (Index 1)
    (1, "pivot"): "But then, the border police stepped in, showing that a flag is not a country.",
    (1, "investigation"): "To understand why the sandbox model fails, we have to look at the Westphalian system.",
    (1, "manual"): "Let's lay out the formal rules that define a state under international law.",

    # Ch 1 (Index 2)
    (2, "pivot"): "Somaliland's success raises a fundamental question: why did it succeed where the U-N failed?",
    (2, "investigation"): "To see why, let's look at how the traditional legal system was integrated.",
    (2, "manual"): "Here is the structural handbook for aligning modern bureaucracy with cultural software.",
    
    # Ch 2 (Index 3)
    (3, "pivot"): "How did a bankrupt, newly independent Baltic nation build a currency with zero trust?",
    (3, "investigation"): "The answer lies in the mechanics of a currency board.",
    (3, "manual"): "Let's examine the technical blueprint for establishing monetary credibility.",
    
    # Ch 3 (Index 4)
    (4, "pivot"): "Uniting Chinese, Malay, and Indian immigrants required a physical strategy.",
    (4, "investigation"): "Lee Kuan Yew's secret weapon was public housing quotas.",
    (4, "manual"): "Here are the design rules for shared spatial architecture that prevents self-segregation.",
    
    # Ch 4 (Index 5)
    (5, "pivot"): "In a region torn by civil wars, Costa Rica's decision seemed suicidal. But it was strategic.",
    (5, "investigation"): "By eliminating the army, Costa Rica redirected funds to education and built diplomatic shields.",
    (5, "manual"): "Let's look at the policy options and coefficients for small-state defense.",
    
    # Ch 5 (Index 6)
    (6, "pivot"): "Why does a landless order in Rome enjoy sovereignty while Taiwan is unrecognized?",
    (6, "investigation"): "Sovereignty is a social club. Let's look at the history of Taiwan's derecognition.",
    (6, "manual"): "Here is how a new state can navigate international law and establish bilateral representation.",
    
    # Ch 6 (Index 7)
    (7, "pivot"): "Estonia realized they could not compete with tanks, so they went online.",
    (7, "investigation"): "They built the X-Road and data embassies to make the state impossible to occupy.",
    (7, "manual"): "Let's lay out the technical database exchange architectures and disaster recovery rules.",
    
    # Ch 7 (Index 8)
    (8, "pivot"): "John Snow's work showed that public health is the primary security of a state.",
    (8, "investigation"): "Let's contrast Snow's empirical mapping with top-down quarantine blockades in history.",
    (8, "manual"): "Here is the containment protocol and surveillance framework for biosecurity.",
    
    # Ch 8 (Index 9)
    (9, "pivot"): "Prussia designed public schools to forge national discipline and industrial capability.",
    (9, "investigation"): "Let's contrast the Prussian factory-school model with high-trust Finnish and digital Estonian models.",
    (9, "manual"): "Here is the implementation framework for modern human capital development.",
    
    # Ch 9 (Index 10)
    (10, "pivot"): "Alexander Hamilton's whiskey tax proved that a state must extract resources to survive.",
    (10, "investigation"): "But extraction is a delicate balance of voluntary compliance and trust.",
    (10, "manual"): "Here are the guidelines for fiscal capacity, digital tax systems, and public debt limits.",
    
    # Ch 10 (Index 11)
    (11, "pivot"): "France's Messmer Plan showed that energy security is the lifeblood of state sovereignty.",
    (11, "investigation"): "Let's contrast France's centralized nuclear transition with Germany's natural gas dependencies.",
    (11, "manual"): "Here is the strategic energy transition framework and grid resilience guide.",
    
    # Conclusion (Index 12)
    (12, "pivot"): "These stories show how all these pillars of statecraft are interconnected.",
    (12, "investigation"): "As we look to the future, climate change and A-I will challenge the Westphalian model.",
    (12, "manual"): "Here is the Accidental Founder's Checklist: an 18-question diagnostic self-test."
}

def get_heading_transition(chapter_index, subheading_text):
    """
    Determines if a paragraph is a subheading and maps it to a conversational transition.
    """
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
    """
    Translates mathematical formulas, acronyms, and visual markdown
    into spoken English suited for audiobook reading.
    """
    # Remove YAML headers
    text = re.sub(r"^---[\s\S]*?---", "", text)
    
    # 1. Translate mathematical equations and symbols
    # Praetorian Coefficient Formula
    text = text.replace(r"\mathcal{PC} = \frac{\text{Internal Police Role} \times \text{Institutional Autonomy}}{\text{External Threat Salience} \times \text{Civilian Bureaucratic Strength}}",
                        "The Praetorian Coefficient is calculated by multiplying the internal police role by institutional autonomy, divided by the product of external threat salience and civilian bureaucratic strength.")
    
    # Duncan Index of Dissimilarity
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
    
    # 2. Format acronyms with hyphens so the TTS speaks them as individual letters
    text = re.sub(r"\bEIP\b", "E-I-P", text)
    text = re.sub(r"\bHDB\b", "H-D-B", text)
    text = re.sub(r"\beID\b", "e-I-D", text)
    text = re.sub(r"\bOAS\b", "O-A-S", text)
    text = re.sub(r"\bUN\b", "U-N", text)
    text = re.sub(r"\bSMOM\b", "S-M-O-M", text)
    text = re.sub(r"\bPRC\b", "P-R-C", text)
    text = re.sub(r"\bSaaS\b", "S-a-a-S", text)
    text = re.sub(r"\bKSI\b", "K-S-I", text)
    text = re.sub(r"\bOPEC\b", "O-P-E-C", text)
    text = re.sub(r"\bPWR\b", "P-W-R", text)
    text = re.sub(r"\bEROI\b", "E-R-O-I", text)
    
    # 3. Strip links and visual formatting
    text = re.compile(r'\[([^\]]+)\]\([^\)]+\)').sub(r'\1', text)
    text = text.replace(r"\newpage", "")
    text = text.replace(r"\pagebreak", "")
    text = text.replace("`", "")
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"\*([^*]+)\*", r"\1", text)
    
    # Clean list bullets and turn blockquotes into normal text
    text = re.sub(r"^\s*[-*+]\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*>\s*", "", text, flags=re.MULTILINE)
    
    # Remove excessive newlines
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = text.strip()
    
    return text

def clean_chapter_title(title):
    """
    Cleans chapter title to make it sound natural (e.g. removes parentheticals, translates numbers).
    """
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
    """
    Parses book.md into structural chapters.
    """
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

def generate_silence_wav(duration, output_path, sample_rate=SAMPLE_RATE):
    """
    Uses ffmpeg to generate a silent WAV file.
    """
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi",
        "-i", f"anullsrc=r={sample_rate}:cl=mono",
        "-t", str(duration),
        output_path
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

def generate_paragraph_audio(text, output_path):
    """
    Calls MLX-Audio CLI to generate speech for a single paragraph.
    """
    cmd = [
        "python3", "-m", "mlx_audio.tts.generate",
        "--model", MODEL_NAME,
        "--text", text,
        "--output_path", output_path
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

def concatenate_wav_files(file_list, output_path):
    """
    Concatenates multiple WAV files into one.
    """
    list_file_path = output_path + ".list.txt"
    with open(list_file_path, "w", encoding="utf-8") as f:
        for filepath in file_list:
            f.write(f"file '{os.path.abspath(filepath)}'\n")
            
    cmd = [
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", list_file_path,
        "-c", "copy",
        output_path
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    if os.path.exists(list_file_path):
        os.remove(list_file_path)

def main():
    print(f"Initializing local MLX-Audio generator using model: {MODEL_NAME}")
    
    # Setup paths
    os.makedirs(LOCAL_OUTPUT_DIR, exist_ok=True)
    temp_dir = os.path.join(LOCAL_OUTPUT_DIR, "temp")
    os.makedirs(temp_dir, exist_ok=True)
    
    # Generate silent blocks
    p_silence = os.path.join(temp_dir, "p_silence.wav")
    t_silence = os.path.join(temp_dir, "t_silence.wav")
    c_silence = os.path.join(temp_dir, "c_silence.wav")
    generate_silence_wav(PARAGRAPH_SILENCE_DURATION, p_silence)
    generate_silence_wav(TRANSITION_SILENCE_DURATION, t_silence)
    generate_silence_wav(CHAPTER_SILENCE_DURATION, c_silence)
    
    # Parse manuscript
    print("Parsing manuscript...")
    chapters = parse_chapters(BOOK_PATH)
    print(f"Found {len(chapters)} sections to convert.")
    
    chapter_wav_files = []
    
    for ch in chapters:
        chapter_title = ch["title"]
        chapter_filename = ch["filename"]
        chapter_body = ch["body"]
        chapter_index = ch["index"]
        
        # Skip the dummy YAML block
        if chapter_filename.startswith("00_"):
            continue
            
        print(f"\nProcessing Chapter: '{chapter_title}'...")
        
        # Split body into paragraphs
        paragraphs = [p.strip() for p in chapter_body.split("\n\n") if p.strip()]
        
        # Insert cleaned title as the first paragraph
        clean_title = clean_chapter_title(chapter_title)
        paragraphs.insert(0, clean_title + ".")
        
        paragraph_files = []
        
        for p_idx, raw_p in enumerate(paragraphs):
            # Check if the paragraph is a subheading and map it to a transition
            transition = get_heading_transition(chapter_index, raw_p)
            if transition:
                p_text = transition
                silence_file = t_silence  # Longer pause after a transition
            else:
                if raw_p.startswith("#"):
                    continue
                p_text = make_audio_friendly(raw_p)
                silence_file = p_silence  # Standard pause
                
            if not p_text:
                continue
                
            p_file = os.path.join(temp_dir, f"{chapter_filename}_p{p_idx:03d}.wav")
            print(f"  -> Voicing paragraph {p_idx+1}/{len(paragraphs)}...")
            
            try:
                generate_paragraph_audio(p_text, p_file)
                paragraph_files.append(p_file)
                paragraph_files.append(silence_file)
            except Exception as e:
                print(f"  [ERROR] Failed generating paragraph {p_idx}: {e}")
                
        # Merge paragraphs
        if paragraph_files:
            paragraph_files.pop()  # Remove trailing paragraph silence
            
            chapter_wav = os.path.join(LOCAL_OUTPUT_DIR, f"{chapter_filename}.wav")
            print(f"Merging paragraphs into chapter: {chapter_wav}...")
            concatenate_wav_files(paragraph_files, chapter_wav)
            chapter_wav_files.append(chapter_wav)
            chapter_wav_files.append(c_silence)
            
            # Clean up paragraph temp files
            for pf in paragraph_files:
                if pf != p_silence and pf != t_silence and os.path.exists(pf):
                    os.remove(pf)
                    
    # Merge chapters
    if chapter_wav_files:
        chapter_wav_files.pop()  # Remove trailing chapter silence
        
        final_wav = os.path.join(LOCAL_OUTPUT_DIR, "statecraft_full_local.wav")
        print("\nMerging all chapters into full WAV...")
        concatenate_wav_files(chapter_wav_files, final_wav)
        
        print(f"Converting full WAV to final MP3: {FINAL_LOCAL_AUDIO}...")
        cmd = [
            "ffmpeg", "-y",
            "-i", final_wav,
            "-codec:a", "libmp3lame",
            "-qscale:a", "4",
            FINAL_LOCAL_AUDIO
        ]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        
        # Clean up temp WAVs
        if os.path.exists(final_wav):
            os.remove(final_wav)
        for cw in chapter_wav_files:
            if cw != c_silence and os.path.exists(cw):
                os.remove(cw)
                
        print(f"\n[SUCCESS] Local MLX Audiobook generated as '{FINAL_LOCAL_AUDIO}'!")
    else:
        print("\n[ERROR] No audio files were generated.")

if __name__ == "__main__":
    main()
