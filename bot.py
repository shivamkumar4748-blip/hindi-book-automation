# 1. जरूरी लाइब्रेरीज चेक और इंस्टॉल करना
import subprocess
import sys

def install_packages():
    packages = ["internetarchive", "requests", "Pillow"]
    for package in packages:
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        except subprocess.CalledProcessError:
            subprocess.check_call([sys.executable, "-m", "pip", "install", package, "--user"])

print("सिस्टम सेटअप चेक किया जा रहा है...")
install_packages()
print("सिस्टम पूरी तरह तैयार है!\n")

# 2. मुख्य ऑटोमेशन स्क्रिप्ट
import time
import requests
import random
import os
import json
import shutil
import hashlib
import internetarchive as ia
from PIL import Image, ImageDraw, ImageFont

ACCESS_KEY = "6yJQhusUsuUme95s"
SECRET_KEY = "cBEIKuzxUjPxQbXI"
PROGRESS_FILE = "archive_progress.json"

def load_progress():
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, "r") as f:
            try:
                return json.load(f).get("processed_identifiers", [])
            except json.JSONDecodeError:
                return []
    return []

def save_progress(processed_list):
    with open(PROGRESS_FILE, "w") as f:
        json.dump({"processed_identifiers": processed_list}, f, indent=4)

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

# 3. मास्टर लिस्ट फेच करना
query = 'language:Hindi AND year:[* TO 1950] AND format:PDF'
print("इंटरनेट आर्काइव से शुद्ध पीडीएफ वाली हिंदी किताबों की लिस्ट निकाली जा रही है...")

try:
    search_results = ia.search_items(query, fields=['identifier', 'title', 'creator'])
    identifiers = [doc for doc in search_results]
    print(f"कुल {len(identifiers)} प्रीमियम किताबें मिल चुकी हैं!\n")
except Exception as e:
    print(f"लिस्ट फेच करने में एरर आया: {e}")
    sys.exit()

processed_identifiers_list = load_progress()
if processed_identifiers_list:
    print(f"नोट: कुल {len(processed_identifiers_list)} किताबें पहले ही अपलोड हो चुकी हैं, उन्हें छोड़कर आगे बढ़ रहे हैं...\n")

# 4. ऑटोमैटिक प्रोसेसिंग लूप
for index, doc_data in enumerate(identifiers, start=1):
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
        
        print(f"[{index}/{len(identifiers)}] प्रोसेस हो रही किताब: {formatted_title}")
        
        files_to_upload = []
        
        pdf_downloaded = False
        for file_info in source_item.files:
            file_name = file_info.get('name', '')
            if file_name.lower().endswith('.pdf'):
                pdf_url = f"https://archive.org/download/{identifier}/{file_name}"
                local_pdf_path = os.path.join(temp_dir, file_name)
                
                print(f"  - PDF डाउनलोड हो रही है...")
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
            print(f"  - PDF नहीं मिलने के कारण यह किताब स्किप की जा रही है।")
            processed_identifiers_list.append(identifier)
            save_progress(processed_identifiers_list)
            continue
        
        custom_cover_path = os.path.join(temp_dir, "custom_cover.jpg")
        print(f"  - कवर इमेज बनाई जा रही है...")
        create_book_cover(orig_title, orig_creator, custom_cover_path)
        files_to_upload.append(custom_cover_path)
        
        print(f"  - इंटरनेट आर्काइव पर अपलोड की जा रही है ({new_identifier})...")
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
        print("  - अपलोड पूरी तरह सफल!\n")
        
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
            
        processed_identifiers_list.append(identifier)
        save_progress(processed_identifiers_list)
        
    except Exception as e:
        print(f"  - एरर आया: {e}. सुरक्षित रूप से आगे बढ़ रहे हैं...")
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
        time.sleep(30)
        continue

    # हर अपलोड के बाद छोटा और सेफ गैप (ताकि सर्वर ब्लॉक न करे)
    random_gap = random.randint(600, 1200) # 10 से 20 मिनट का गैप ताकि फोन से भी आसानी से हैंडल हो सके
    print(f"अगली किताब के लिए {random_gap // 60} मिनट का गैप लिया जा रहा है...\n")
    time.sleep(random_gap)

print("शानदार! वर्तमान सेशन की सभी किताबें सफलतापूर्वक अपलोड हो चुकी हैं।")
