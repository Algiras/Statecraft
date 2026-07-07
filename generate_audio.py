#!/usr/bin/env python3
"""
Audiobook Generator for Statecraft (Edge TTS Version)
Uses Microsoft Edge's Neural TTS via edge-tts.
Applies audio-friendly text translation (math, acronyms, lists), replaces subheadings
with natural transitions, and concatenates paragraphs with silent MP3 buffers using ffmpeg
to achieve professional, human-like narration pacing.
"""

import os
import re
import sys
import asyncio
import subprocess

# Ensure we have edge-tts installed or let the user run via uv
try:
    import edge_tts
except ImportError:
    print("edge-tts not found. Please run this script with:")
    print("uv run --with edge-tts generate_audio.py")
    sys.exit(1)

BOOK_PATH = "book.md"
OUTPUT_DIR = "audiobook"
VOICE = "en-US-ChristopherNeural"  # Warm, authoritative, non-fiction narrator style
FINAL_AUDIO = "statecraft_audiobook.mp3"

# Silence durations in seconds
PARAGRAPH_SILENCE = 1.8
TRANSITION_SILENCE = 2.2
CHAPTER_SILENCE = 3.5

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
    text = re.sub(r"^---[\s\S]*?---", "", text)
    
    # 1. Translate mathematical equations and symbols
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
        raise FileNotFoundError(f"Source manuscript '{file_path}' not found.")
        
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
            "filename": f"{chapter_index:02d}_{safe_title}.mp3",
            "body": body
        })
        chapter_index += 1
        
    return chapters

def generate_silence_mp3(duration, output_path):
    """
    Uses ffmpeg to generate a silent MP3 file with matching properties.
    """
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi",
        "-i", "anullsrc=r=24000:cl=mono",
        "-t", str(duration),
        "-codec:a", "libmp3lame",
        "-b:a", "48k",
        output_path
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

async def voice_paragraph(text, output_path):
    """
    Sends a single paragraph of plain text to edge-tts.
    """
    communicate = edge_tts.Communicate(text, VOICE)
    await communicate.save(output_path)

def concatenate_mp3_files(file_list, output_path):
    """
    Concatenates multiple MP3 files using ffmpeg concat demuxer.
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

async def generate_chapter_audio(chapter, temp_dir, p_silence, t_silence):
    """
    Generates audio for a chapter paragraph-by-paragraph and merges them with silent buffers.
    """
    title = chapter["title"]
    filename = chapter["filename"]
    body = chapter["body"]
    chapter_index = chapter["index"]
    dest_path = os.path.join(OUTPUT_DIR, filename)
    
    print(f"\nVoicing Chapter: '{title}' -> {dest_path}...")
    
    # Parse paragraphs
    paragraphs = [p.strip() for p in body.split("\n\n") if p.strip()]
    
    # Clean the title and insert it as the first chunk
    clean_title = clean_chapter_title(title)
    paragraphs.insert(0, clean_title + ".")
    
    paragraph_files = []
    
    for p_idx, raw_p in enumerate(paragraphs):
        transition = get_heading_transition(chapter_index, raw_p)
        if transition:
            p_text = transition
            silence_file = t_silence
        else:
            if raw_p.startswith("#"):
                continue
            p_text = make_audio_friendly(raw_p)
            silence_file = p_silence
            
        if not p_text:
            continue
            
        p_file = os.path.join(temp_dir, f"ch{chapter_index:02d}_p{p_idx:03d}.mp3")
        print(f"  -> Sending paragraph {p_idx+1}/{len(paragraphs)} to Edge-TTS...")
        
        try:
            await voice_paragraph(p_text, p_file)
            paragraph_files.append(p_file)
            paragraph_files.append(silence_file)
        except Exception as e:
            print(f"  [ERROR] Failed generating paragraph {p_idx}: {e}")
            
    if paragraph_files:
        paragraph_files.pop()  # Remove trailing paragraph silence
        print(f"Merging paragraphs into chapter: {dest_path}...")
        concatenate_mp3_files(paragraph_files, dest_path)
        
        # Clean up temporary paragraph MP3s to save space
        for pf in paragraph_files:
            if pf not in (p_silence, t_silence) and os.path.exists(pf):
                os.remove(pf)

async def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    temp_dir = os.path.join(OUTPUT_DIR, "temp")
    os.makedirs(temp_dir, exist_ok=True)
    
    # Generate silent MP3 buffers
    p_silence = os.path.join(temp_dir, "p_silence.mp3")
    t_silence = os.path.join(temp_dir, "t_silence.mp3")
    c_silence = os.path.join(temp_dir, "c_silence.mp3")
    
    print("Generating silent pacing buffers...")
    generate_silence_mp3(PARAGRAPH_SILENCE, p_silence)
    generate_silence_mp3(TRANSITION_SILENCE, t_silence)
    generate_silence_mp3(CHAPTER_SILENCE, c_silence)
    
    print(f"Parsing manuscript from {BOOK_PATH}...")
    try:
        chapters = parse_chapters(BOOK_PATH)
    except Exception as e:
        print(f"Error parsing chapters: {e}")
        return
        
    print(f"Found {len(chapters)} sections to convert.")
    
    chapter_files = []
    
    # Process chapters sequentially
    for ch in chapters:
        if ch["filename"].startswith("00_"):
            continue
        await generate_chapter_audio(ch, temp_dir, p_silence, t_silence)
        chapter_files.append(os.path.join(OUTPUT_DIR, ch["filename"]))
        chapter_files.append(c_silence)
        
    # Combine chapters into the final master audiobook
    if chapter_files:
        chapter_files.pop()  # Remove trailing chapter silence
        print("\nCombining all chapters into the final audiobook...")
        concatenate_mp3_files(chapter_files, FINAL_AUDIO)
        print(f"\n[SUCCESS] Custom-paced Edge TTS Audiobook generated as '{FINAL_AUDIO}'!")
        
        # Clean up temp files
        for f in [p_silence, t_silence, c_silence]:
            if os.path.exists(f):
                os.remove(f)
        if os.path.exists(temp_dir):
            try:
                os.rmdir(temp_dir)
            except OSError:
                pass
    else:
        print("[ERROR] No chapters were voiced.")

if __name__ == "__main__":
    asyncio.run(main())
