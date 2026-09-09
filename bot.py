import subprocess
import sys
import os

def install_packages():
    packages = ["internetarchive", "requests", "Pillow"]
    for package in packages:
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        except subprocess.CalledProcessError:
            subprocess.check_call([sys.executable, "-m", "pip", "install", package, "--user"])

print(" [सिस्टम] सेटअप चेक किया जा रहा है...", flush=True)
install_packages()

import time
import requests
import random
import json
import shutil
import hashlib
import internetarchive as ia
from PIL import Image, ImageDraw, ImageFont

ACCESS_KEY = os.environ.get("IA_ACCESS_KEY")
SECRET_KEY = os.environ.get("IA_SECRET_KEY")
PROGRESS_FILE = "archive_progress.json"

def load_progress():
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, "r") as f:
            try:
                data = json.load(f)
                return data.get("processed_identifiers", []), data.get("total_success", 0)
            except json.JSONDecodeError:
                return [], 0
    return [], 0

def save_progress(processed_list, total_success):
    with open(PROGRESS_FILE, "w") as f:
        json.dump({
            "total_success": total_success,
            "processed_identifiers": processed_list
        }, f, indent=4)

def create_book_cover(title, author, output_path):
    width, height = 800, 1200
    title_hash = hashlib.md5(title.encode('utf-8')).hexdigest()
    hash_int = int(title_hash, 16)
    
    palettes = [
        {"bg": (28, 35, 49), "border": (218, 165, 32), "text_c": (255, 250, 250)}, 
        {"bg": (47, 62, 78), "border": (184, 134, 11), "text_c": (255, 248, 220)}, 
        {"bg": (54, 69, 79), "border": (192, 192, 192), "text_c": (245, 245, 245)}, 
        {"bg": (70, 130, 180), "border": (255, 215, 0), "text_c": (255, 255, 250)},  
        {"bg": (60, 179, 113), "border": (255, 250, 240), "text_c": (255, 255, 255)} 
    ]
    selected_palette = palettes[hash_int % len(palettes)]
    
    image = Image.new("RGB", (width, height), color=selected_palette["bg"])
    draw = ImageDraw.Draw(image)
    
    margin = 40
    draw.rectangle([margin, margin, width - margin, height - margin], outline=selected_palette["border"], width=5)
    draw.rectangle([margin + 15, margin + 15, width - margin - 15, height - margin - 15], outline=selected_palette["border"], width=1)
    
    try:
        font_title = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 55)
        font_author = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 35)
        font_brand = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Oblique.ttf", 28)
    except IOError:
        font_title = font_author = font_brand = ImageFont.load_default()

    def get_wrapped_text(text, font, max_width):
        lines = []
        words = text.split()
        if not words:
            return []
        current_line = words[0]
        for word in words[1:]:
            if font.getbbox(current_line + " " + word)[2] <= max_width:
                current_line += " " + word
            else:
                lines.append(current_line)
                current_line = word
        lines.append(current_line)
        return lines

    max_text_width = width - (2 * margin + 80)
    title_lines = get_wrapped_text(title, font_title, max_text_width)
    
    y_start = 250
    for i, line in enumerate(title_lines[:4]): 
        bbox = draw.textbbox((0, 0), line, font=font_title)
        text_width = bbox[2]
        draw.text(((width - text_width) / 2, y_start + (i * 70)), line, fill=selected_palette["text_c"], font=font_title)
        
    author_line = f"— {author[:50]}"
    bbox_author = draw.textbbox((0, 0), author_line, font=font_author)
    draw.text(((width - bbox_author[2]) / 2, 750), author_line, fill=selected_palette["text_c"], font=font_author)

    brand_line = "शिवम डिजिटल ई लाइब्रेरी"
    bbox_brand = draw.textbbox((0, 0), brand_line, font=font_brand)
    draw.text(((width - bbox_brand[2]) / 2, 1080), brand_line, fill=selected_palette["text_c"], font=font_brand)
    
    image.save(output_path)

print(" [डेटा] इंटरनेट आर्काइव एपीआई से पूरी हिंदी किताबों की सूची खोजी जा रही है...", flush=True)

search_url = "https://archive.org/advancedsearch.php"
params = {
    "q": "language:Hindi AND year:[* TO 1950] AND format:PDF",
    "fl[]": "identifier,title,creator",
    "rows": "5000",
    "page": "1",
    "output": "json"
}

try:
    response = requests.get(search_url, params=params, timeout=60)
    data = response.json()
    identifiers = data.get("response", {}).get("docs", [])
    total_found = len(identifiers)
    print(f" [सफलता] कुल {total_found} किताबें मिल चुकी हैं!\n", flush=True)
except Exception as e:
    print(f" [एरर] लिस्ट फेच करने में समस्या आई: {e}", flush=True)
    sys.exit()

processed_identifiers_list, total_success_count = load_progress()
print(f" [स्टेटस] अब तक कुल {total_success_count} किताबें लाइब्रेरी में जुड़ चुकी हैं।", flush=True)

session_processed = 0
MAX_BOOKS_THIS_SESSION = 2  # सुरक्षा और टाइम-लिमिट के कारण प्रति सेशन 2 किताबें

for index, doc_data in enumerate(identifiers, start=1):
    if session_processed >= MAX_BOOKS_THIS_SESSION:
        print(" [जानकारी] इस सेशन का कोटा पूरा हो गया है। सिस्टम सुरक्षित रूप से बंद हो रहा है।", flush=True)
        break

    identifier = doc_data.get('identifier')
    if identifier in processed_identifiers_list:
        continue
        
    temp_dir = "./temp_book_data"
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
    os.makedirs(temp_dir, exist_ok=True)
    
    try:
        source_item = ia.get_item(identifier)
        metadata = source_item.metadata
        
        orig_title = metadata.get('title', 'अज्ञात पुस्तक')
        orig_creator = metadata.get('creator', 'अज्ञात लेखक')
        orig_description = metadata.get('description', 'डिजिटल पुस्तकालय संग्रह.')
        
        formatted_title = f"{orig_title[:200]} - {orig_creator[:100]} | शिवम डिजिटल ई लाइब्रेरी"
        new_identifier = f"shivam_hindi_{identifier}"
        
        print(f"--------------------------------------------------", flush=True)
        print(f" [प्रक्रिया] ({index}/{total_found}) किताब प्रोसेस हो रही है: {orig_title[:40]}...", flush=True)
        
        files_to_upload = []
        pdf_downloaded = False
        
        for file_info in source_item.files:
            file_name = file_info.get('name', '')
            if file_name.lower().endswith('.pdf'):
                pdf_url = f"https://archive.org/download/{identifier}/{file_name}"
                local_pdf_path = os.path.join(temp_dir, file_name)
                
                print(f"   -> पीडीएफ डाउनलोड हो रही है...", flush=True)
                r = requests.get(pdf_url, stream=True, timeout=60)
                if r.status_code == 200:
                    with open(local_pdf_path, 'wb') as f:
                        for chunk in r.iter_content(chunk_size=1024*512):
                            if chunk:
                                f.write(chunk)
                    files_to_upload.append(local_pdf_path)
                    pdf_downloaded = True
                    break
        
        if not pdf_downloaded:
            print(f"   -> [छोड़ा गया] पीडीएफ नहीं मिली।", flush=True)
            processed_identifiers_list.append(identifier)
            save_progress(processed_identifiers_list, total_success_count)
            continue
        
        custom_cover_path = os.path.join(temp_dir, "custom_cover.jpg")
        print(f"   -> कवर डिजाइन हो रहा है...", flush=True)
        create_book_cover(orig_title, orig_creator, custom_cover_path)
        files_to_upload.append(custom_cover_path)
        
        print(f"   -> इंटरनेट आर्काइव पर अपलोड हो रही है...", flush=True)
        ia.upload(
            new_identifier,
            files=files_to_upload,
            access_key=ACCESS_KEY,
            secret_key=SECRET_KEY,
            metadata={
                'title': formatted_title,
                'creator': orig_creator,
                'description': orig_description,
                'mediatype': 'texts',
                'language': 'Hindi',
                'collection': 'opensource',
                'publisher': 'शिवम डिजिटल ई लाइब्रेरी'
            },
            verify=True
        )
        print(f"   -> [सफलता] अपलोड पूरी हुई!\n", flush=True)
        
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
            
        processed_identifiers_list.append(identifier)
        total_success_count += 1
        save_progress(processed_identifiers_list, total_success_count)
        session_processed += 1
        
    except Exception as e:
        print(f"   -> [चेतावनी] दिक्कत: {e}. आगे बढ़ रहे हैं...", flush=True)
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
        time.sleep(60)
        continue

    if session_processed < MAX_BOOKS_THIS_SESSION:
        # एक किताब से दूसरी किताब के बीच 1 से 1.5 घंटे (3600 से 5400 सेकंड) का वास्तविक इंसानी गैप
        human_gap = random.randint(3600, 5400) 
        print(f" [विराम] अगली किताब उठाने से पहले {human_gap // 60} मिनट का नेचुरल रेस्ट लिया जा रहा है...\n", flush=True)
        time.sleep(human_gap)

print(" [समाप्ति] वर्तमान सेशन शांतिपूर्वक पूरा हुआ।", flush=True)
