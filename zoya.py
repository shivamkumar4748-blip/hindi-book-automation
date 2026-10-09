import oci
import time
import os
import sys

# GitHub Actions se STACK_OCID lena
STACK_ID = os.environ.get("STACK_OCID")
if not STACK_ID:
    print("❌ Error: STACK_OCID nahi mila! GitHub secrets check karein.")
    sys.exit(1)

print("🚀 Zoya Server Auto-Provisioning (Pro Version) Started...")
print("⏳ Har 30 second mein Oracle ko request jayegi...\n")

# OCI Config load karna
try:
    config = oci.config.from_file("~/.oci/config")
    rm_client = oci.resource_manager.ResourceManagerClient(config)
except Exception as e:
    print(f"❌ Config load karne mein error: {e}")
    sys.exit(1)

attempt = 1
# 5 ghante 45 minute ka safe timer (GitHub 6 hr ban se bachne ke liye)
end_time = time.time() + 20700 

while time.time() < end_time:
    print(f"🔄 [Attempt {attempt}] Oracle ko request bhej raha hu...", flush=True)
    try:
        # Stack apply karne ki request
        job_details = oci.resource_manager.models.CreateJobDetails(
            stack_id=STACK_ID,
            display_name=f"Zoya-Auto-{attempt}",
            operation="APPLY",
            job_operation_details=oci.resource_manager.models.CreateApplyJobOperationDetails(
                execution_plan_strategy="AUTO_APPROVED"
            )
        )
        
        job = rm_client.create_job(job_details).data
        
        # Job ka status check karna (SUCCEEDED ya FAILED)
        while True:
            job_state = rm_client.get_job(job.id).data.lifecycle_state
            if job_state in ["SUCCEEDED", "FAILED", "CANCELED"]:
                break
            time.sleep(5)
            
        if job_state == "SUCCEEDED":
            print("\n🎉 BINGO! Zoya Server book ho gaya! 🎉", flush=True)
            sys.exit(0) # Kaam ho gaya, action band karo
        else:
            print("❌ Out of capacity (Server full hai). 30 second wait kar raha hu...\n", flush=True)
            
    except Exception as e:
        print(f"⚠️ Request fail hui (Shayad limit hit hui): {e}", flush=True)
        print("⏳ 30 second baad wapas try karunga...\n", flush=True)
        
    time.sleep(30)
    attempt += 1

print("⏱️ 5 ghante 45 minute pure ho gaye. GitHub ise apne aap naye loop me restart karega.")
