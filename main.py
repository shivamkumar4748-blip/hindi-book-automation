import os
import time
import subprocess

# GitHub Secrets से STACK_OCID को लेना
stack_ocid = os.environ.get("STACK_OCID")

if not stack_ocid:
    print("Error: STACK_OCID नहीं मिला! कृपया GitHub Secrets चेक करें।")
    exit(1)

print(f"[*] Zoya Server के लिए आक्रामक (Aggressive) स्क्रिप्ट शुरू हो गई है...")
print(f"[*] Stack ID: {stack_ocid}")

# GitHub Actions 6 घंटे में टाइमआउट हो जाता है, इसलिए हम इसे 5 घंटे 45 मिनट (20700 सेकंड) चलाएंगे
end_time = time.time() + 20700 

while time.time() < end_time:
    current_time = time.strftime('%Y-%m-%d %H:%M:%S')
    print(f"\n[{current_time}] Oracle को Zoya सर्वर बनाने की रिक्वेस्ट भेजी जा रही है...")
    
    try:
        # ओरेकल को स्टैक रन करने की कमांड
        command = [
            "oci", "resource-manager", "job", "create-apply-job",
            "--stack-id", stack_ocid,
            "--execution-plan-strategy", "AUTO_APPROVED"
        ]
        
        # कमांड रन करना
        result = subprocess.run(command, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("[+] सफलता! जॉब ओरेकल में भेज दी गई है। (अगर कैपेसिटी होगी तो सर्वर बन जाएगा)")
        else:
            print("[-] एरर या कैपेसिटी फुल है। ओरेकल ने मना कर दिया।")
            
    except Exception as e:
        print(f"[!] स्क्रिप्ट में कोई दिक्कत आई: {e}")
        
    print("[*] 30 सेकंड का इंतज़ार कर रहे हैं (ओरेकल को बैन करने से रोकने के लिए)...")
    time.sleep(30)

print("[*] 5 घंटे 45 मिनट पूरे हो गए। GitHub इसे अपने आप रीस्टार्ट कर देगा।")
