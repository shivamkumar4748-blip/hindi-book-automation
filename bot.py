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

print(" [सिस्टम] डिजिटल लाइब्रेरी बैकग्राउंड सर्विस शुरू हो रही है...")
install_packages()

import time
import requests
import random
import json
import shutil
import hashlib
import internetarchive as ia
from PIL import Image, ImageDraw, ImageFont

# GitHub Secrets से सुरक्षित रूप से कीज़ उठाना
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

query = 'language:Hindi AND year:[* TO 1950] AND format:PDF'
print(" [डेटा] इंटरनेट आर्काइव से हिंदी किताबों की मास्टर लिस्ट खंगाली जा रही है...")

try:
    search_results = ia.search_items(query, fields=['identifier', 'title', 'creator'])
    identifiers = [doc for doc in search_results]
    print(f" [सफलता] कुल {len(identifiers)} शुद्ध पीडीएफ किताबें डेटाबेस में मिली हैं!\n")
except Exception as e:
    print(f" [एरर] लिस्ट फेच करने में समस्या आई: {e}")
    sys.exit()

processed_identifiers_list, total_success_count = load_progress()
print(f" [स्टेटस] अब तक कुल {total_success_count} किताबें सफलताપूर्वक लाइब्रेरी में जोड़ी जा चुकी हैं।\n")

# एक बार में केवल 1 या 2 किताबें ही प्रोसेस होंगी ताकि इंसान की तरह धीमी और सुरक्षित गति बनी रहे
session_processed = 0
MAX_BOOKS_THIS_SESSION = 2 

for index, doc_data in enumerate(identifiers, start=1):
    if session_processed >= MAX_BOOKS_THIS_SESSION:
        print(" [जानकारी] इस सेशन का इंसानी कोटा पूरा हो गया है। सिस्टम अब आराम करेगा और अगले शेड्यूल पर खुद जागेगा।")
        break

    identifier = doc_data['identifier']
    
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
        
        print(f"--------------------------------------------------")
        print(f" [प्रक्रिया] किताब उठाई गई ({index}/{len(identifiers)}): {orig_title[:50]}...")
        
        files_to_upload = []
        pdf_downloaded = False
        
        for file_info in source_item.files:
            file_name = file_info.get('name', '')
            if file_name.lower().endswith('.pdf'):
                pdf_url = f"https://archive.org/download/{identifier}/{file_name}"
                local_pdf_path = os.path.join(temp_dir, file_name)
                
                print(f"   -> मूल पीडीएफ फाइल डाउनलोड की जा रही है...")
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
            print(f"   -> [छोड़ा गया] इस किताब की सही पीडीएफ नहीं मिली, आगे बढ़ रहे हैं।")
            processed_identifiers_list.append(identifier)
            save_progress(processed_identifiers_list, total_success_count)
            continue
        
        custom_cover_path = os.path.join(temp_dir, "custom_cover.jpg")
        print(f"   -> किताब के लिए नया और आकर्षक कवर डिजाइन किया जा रहा है...")
        create_book_cover(orig_title, orig_creator, custom_cover_path)
        files_to_upload.append(custom_cover_path)
        
        print(f"   -> इंटरनेट आर्काइव पर सुरक्षित रूप से अपलोड की जा रही है ({new_identifier})...")
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
        print("   -> [सफलता] किताब सफलतापूर्वक अपलोड हो चुकी है!\n")
        
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
            
        processed_identifiers_list.append(identifier)
        total_success_count += 1
        save_progress(processed_identifiers_list, total_success_count)
        session_processed += 1
        
    except Exception as e:
        print(f"   -> [चेतावनी] अपलोड के दौरान छोटी सी अड़चन आई: {e}. सुरक्षित तरीके से हैंडल किया जा रहा है...")
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
        time.sleep(30)
        continue

    # अगर सेशन में एक से ज्यादा किताब बची है, तो इंसानी गैप (1 से 1.5 घंटे यानी 3600 से 5400 सेकंड) दें
    if session_processed < MAX_BOOKS_THIS_SESSION:
        human_gap = random.randint(3600, 5400) 
        print(f" [विराम] इंसान की तरह अगला काम करने से पहले {human_gap // 60} मिनट का नेचुरल गैップ लिया जा रहा है...\n")
        time.sleep(human_gap)

print(" [समाप्ति] वर्तमान सेशन का काम शांतिपूर्ण ढंग से पूरा हो गया है।")
