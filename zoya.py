import oci
import time
import sys

STACK_ID = "ocid1.ormstack.oc1.ap-mumbai-1.amaaaaaaijjqvbiaouwuvwmvswgusathlneeuw5rfrpyl75flrqwftptfz5a"
config = oci.config.from_file("~/.oci/config")
rm_client = oci.resource_manager.ResourceManagerClient(config)

print("=======================================", flush=True)
print(" 🚀 Zoya Auto-Provisioning Started! 🚀 ", flush=True)
print("=======================================", flush=True)

attempt = 1
while True:
    try:
        print(f"[{attempt}] Oracle ko request bhej raha hu...", flush=True)
        job_details = oci.resource_manager.models.CreateJobDetails(
            stack_id=STACK_ID,
            display_name=f"Zoya-Auto-{attempt}",
            operation="APPLY",
            job_operation_details=oci.resource_manager.models.CreateApplyJobOperationDetails(
                execution_plan_strategy="AUTO_APPROVED"
            )
        )
        job = rm_client.create_job(job_details).data
        
        while True:
            job_state = rm_client.get_job(job.id).data.lifecycle_state
            if job_state in ["SUCCEEDED", "FAILED", "CANCELED"]:
                break
            time.sleep(5)
        
        if job_state == "SUCCEEDED":
            print("\n🎉 BINGO! Zoya Server ban gaya! 🎉", flush=True)
            break
        else:
            print("❌ Out of capacity. 60 seconds wait kar raha hu...\n", flush=True)
            time.sleep(60)
            attempt += 1

    except Exception as e:
        print(f"⚠️ Error aaya: {e}", flush=True)
        time.sleep(60)
