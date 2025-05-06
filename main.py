import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import PromptTemplate
from langchain_core.runnables import RunnableSequence
from pathlib import Path
import yaml
import json
from langchain_google_genai import ChatGoogleGenerativeAI
from google.api_core.exceptions import ResourceExhausted

# Load API key
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise EnvironmentError("GEMINI_API_KEY not found in .env")

# llm = ChatGoogleGenerativeAI(model="models/gemini-2.5-pro-exp-03-25", google_api_key=GEMINI_API_KEY)
# GEMINI_MODEL = os.getenv("GEMINI_MODEL", "models/gemini-1.5-pro")
# llm = ChatGoogleGenerativeAI(model=GEMINI_MODEL, google_api_key=GEMINI_API_KEY)

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "models/gemini-1.5-pro")

# Ordered fallback list — from most powerful to least
MODEL_FALLBACKS = [
    "models/gemini-2.5-pro-preview-03-25",
    "models/gemini-2.5-flash-preview-04-17",
    "models/gemini-1.5-pro",
    "models/gemini-1.5-flash",
    "models/gemini-1.0-pro-vision-latest",
    "models/chat-bison-001"
]
# Start with preferred model from .env if it exists
if GEMINI_MODEL not in MODEL_FALLBACKS:
    MODEL_FALLBACKS.insert(0, GEMINI_MODEL)

llm = None
for model_name in MODEL_FALLBACKS:
    try:
        print(f"🔍 Trying Gemini model: {model_name}")
        llm = ChatGoogleGenerativeAI(model=model_name, google_api_key=GEMINI_API_KEY)
        # Test the model with a dummy ping
        llm.invoke("Ping")  # This will trigger a real API call and fail if quota exceeded
        print(f"✅ Using model: {model_name}")
        break
    except ResourceExhausted:
        print(f"❌ Quota exceeded for model: {model_name}. Trying next...")
    except Exception as e:
        print(f"⚠️ Error initializing model {model_name}: {e}")

print(f"🧠 Using Gemini model: {GEMINI_MODEL}")

# === Prompt Templates ===
planner_prompt = PromptTemplate.from_template("""
You are a DevOps expert.
Given the goal: "{goal}", break it into:
1. Terraform provisioning requirements
2. Ansible configuration requirements
Respond with two sections: 'Terraform Plan:' and 'Ansible Plan:'

Add the following specifics:
- Use this provider block:
  provider "google" {{
    credentials = file("~/terraform-cyberrange-key.json")
    project     = "abhijit-sandbox-1"
    region      = "us-central1"
    zone        = "us-central1-a"
  }}
- Let the user choose or create a VPC (custom or default) with name if specified.
- Let the user choose or create a subnet with custom IP ranges.
- Allow user-defined firewall rules.
- Allow setting internal/external IPs.
- Inject this SSH public key into the instance's authorized_keys:
  ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAACAQC4uBwyKl/HiMKMuxdyNbOsLyI9Dygw+E/N2kHtCAtb8CIzyh91Fzo0XvmItiGwz0uUaz0Z0V/hrktwyaqaiPVuKM6OUhQQTnpl5vH1W7KOsUd1VAf5Vmn1h4KhULzCWCSkhrXAzSK4+MoauAHI7GtJAvTSBwi5N8gDTNlZubGJygFbhBfQUkPtVGAF6cD0o0Awe/Q21Hk55KfBu8u6pAtSlE7mUEIEp3Q8s181qf3hkUmV9x7CYFmm1FEqPR/uPbcCxi0G2+mdhiUL9nyaB4CUTKCMojSnTyU2/pHvZiGwrWwd/o5as9HyD0LYvqsYCvykicZfPpBQXsTf28fRQAykA80FRLowQgX6zJ4o3GE9lRMQV4Alun9AlvtZy5qR2FtZJzqaSARqqeLXIE0MCqQbGyCleft6vVKgj0lKrTd5ZkMe8C4j7CoXtWJ6gUwR7qswIzpxLiU21lAnQwDklfJ5wVSFRUrdV6RBlbwPdr0xgKoLVSseoUL4UeqiCS40t8K7gdlVRCA+K6udaa8M3qFNxyONFMbvB+K9LTDjA4aL5kbF6utNv86RR6sDl7OJX41aR5pEqx4fTFupLbJEvmz2gN6dbkOSuhsKl8TMXSwus+/7FEzTFqa21r1jJPwVo1RdNQQaGT3u0sV2mOMDnGx7ElVhB6qIyIcKy9QfpjFpuQ== abanand@zindagi.tech
- Let the user choose machine type (e.g., "e2-micro").
""")

terraform_prompt = PromptTemplate.from_template("""
You are an infrastructure engineer. Write Terraform code to:
{terraform_task}
Output only .tf code, no explanations.
""")

ansible_prompt = PromptTemplate.from_template("""
You are a DevOps engineer. Write an Ansible playbook to:
{ansible_task}
Output only YAML code.
""")

critic_prompt = PromptTemplate.from_template("""
You are a strict DevOps reviewer.

Your job is to:
- Detect invalid YAML in the Ansible code
- Reject any playbooks that have empty `tasks: []` lists
- Flag hallucinated Terraform values (e.g., dummy IPs or usernames)
- Confirm that playbooks actually install nginx or mariadb

Give PASS/FAIL for each section and suggest corrected snippets if needed.

Terraform:
{terraform_code}

Ansible:
{ansible_code}
""")


# === Input Goal ===
user_goal = input("Enter your infrastructure goal in natural language (e.g., 'Provision 2 Ubuntu VMs in GCP and install NGINX using Ansible'): ").strip()

vpc_default = "Use default VPC"
subnet_default = "Use existing subnet"
firewall_default = "Allow ports 22,80 from 0.0.0.0/0"
ip_default = "Assign public IP"
machine_default = "e2-micro"

goal = f"""
{user_goal}
If not explicitly mentioned above, assume the following:
- {vpc_default}
- {subnet_default}
- {firewall_default}
- {ip_default}
- Machine type: {machine_default}
"""

print("\n🎯 Goal:")
print(goal)
print("=" * 60)

# === Planner Chain ===
planner_chain = planner_prompt | llm
plan = planner_chain.invoke({"goal": goal}).content.strip()
print("\n🧠 Plan Output:\n" + plan)

# === Extract Terraform/Ansible tasks ===
if "Ansible Plan:" in plan:
    terraform_task = plan.split("Ansible Plan:")[0].replace("Terraform Plan:", "").strip()
    ansible_task = plan.split("Ansible Plan:")[-1].strip()
else:
    terraform_task = plan
    ansible_task = "Configure VMs as needed using provided SSH credentials."

# Automatically include SSH user setup logic if user/password is mentioned
if "password" in goal.lower():
    ansible_task += "\\nAlso, ensure that the specified user is created, added to the sudoers group, and assigned the provided password securely using ansible.builtin.user, ansible.builtin.copy, or ansible.builtin.lineinfile for sudoers permissions."

# === Terraform Chain ===
terraform_chain = terraform_prompt | llm
terraform_code = terraform_chain.invoke({"terraform_task": terraform_task}).content.strip()
print("\n📦 Terraform Code:")
print("\n" + terraform_code)
print("=" * 60)

# === Ansible Chain ===
ansible_chain = ansible_prompt | llm
# ansible_code = ansible_chain.invoke({"ansible_task": ansible_task}).content.strip()

# # === Validate Ansible YAML ===
# try:
#     parsed = yaml.safe_load(ansible_code)
#     if not isinstance(parsed, list):
#         raise ValueError("Ansible playbook must be a list of plays.")
# except Exception as e:
#     print(f"❌ Ansible code is invalid YAML: {e}")
#     print("⚠️ Overriding with dummy playbook to prevent failure.")
#     ansible_code = """---
# - name: Dummy playbook
#   hosts: all
#   gather_facts: false
#   tasks: []
# """

# === Generate and sanitize Ansible code ===
raw_ansible = ansible_chain.invoke({"ansible_task": ansible_task}).content.strip()

# Clean markdown fences
ansible_code = raw_ansible.replace("```yaml", "").replace("```", "").strip()

# === Validate Ansible YAML ===
try:
    parsed = yaml.safe_load(ansible_code)
    if not isinstance(parsed, list):
        raise ValueError("Ansible playbook must be a list of plays.")
except Exception as e:
    print(f"❌ Ansible code is invalid YAML: {e}")
    print("⚠️ Overriding with dummy playbook to prevent failure.")
    ansible_code = """---
- name: Dummy playbook
  hosts: all
  gather_facts: false
  tasks: []
"""


print("\n 🔧 Ansible Code:")
print("\n" + ansible_code)
print("=" * 60)

# === Critic Chain ===
critic_chain = critic_prompt | llm
critique = critic_chain.invoke({"terraform_code": terraform_code, "ansible_code": ansible_code}).content.strip()
print("\n🕵️‍♂️ Critique:")
print("\n" + critique)
print("=" * 60)

# === Save Outputs ===
os.makedirs("generated/terraform", exist_ok=True)
os.makedirs("generated/ansible", exist_ok=True)
os.makedirs("generated/plan", exist_ok=True)

with open("generated/terraform/main.tf", "w") as f:
    f.write(terraform_code.replace("```terraform", "").replace("```", "").strip())

# === Inject SSH public key via .auto.tfvars ===
ssh_key = os.getenv("SSH_PUBLIC_KEY")
if ssh_key:
    with open("generated/terraform/override.auto.tfvars", "w") as f:
        f.write(f'ssh_public_key = "{ssh_key}"\n')
else:
    print("⚠️ SSH_PUBLIC_KEY not set in .env — Terraform apply will likely fail.")


with open("generated/ansible/playbook.yml", "w") as f:
    f.write(ansible_code.replace("```yaml", "").replace("```", "").strip())

with open("generated/plan/plan.txt", "w") as f:
    f.write(plan)

with open("generated/plan/review.md", "w") as f:
    f.write(critique)

# with open("generated/ansible/inventory.ini", "w") as f:
#     f.write("""[nginx_servers]
# vm1 ansible_host=10.10.10.100 ansible_user=abanand

# [mariadb_servers]
# vm2 ansible_host=10.10.10.101 ansible_user=abanand

# [all:vars]
# ansible_ssh_private_key_file=~/.ssh/id_rsa
# ansible_python_interpreter=/usr/bin/python3
# """)

# === Extract IPs from terraform output
try:
    tf_output = os.popen("cd generated/terraform && terraform output -json").read()
    ip_data = json.loads(tf_output)

    vm1_ip = ip_data.get("vm_internal_ips", {}).get("value", {}).get("vm1", "10.10.10.100")
    vm2_ip = ip_data.get("vm_internal_ips", {}).get("value", {}).get("vm2", "10.10.10.101")

except Exception as e:
    print(f"❌ Could not extract IPs from terraform output: {e}")
    vm1_ip = "10.10.10.100"
    vm2_ip = "10.10.10.101"


with open("generated/ansible/inventory.ini", "w") as f:
    f.write(f"""[nginx_servers]
vm1 ansible_host={vm1_ip} ansible_user=abanand

[mariadb_servers]
vm2 ansible_host={vm2_ip} ansible_user=abanand

[all:vars]
ansible_ssh_private_key_file=~/.ssh/id_rsa
ansible_python_interpreter=/usr/bin/python3
""")


# === Validate Terraform ===
print("\n🔍 Validating Terraform...")
Path("generated/terraform/.terraform").mkdir(parents=True, exist_ok=True)
os.system("cd generated/terraform && terraform init -backend=false > /dev/null 2>&1")
os.system("cd generated/terraform && terraform validate")

print("\n✅ All outputs saved to 'generated/' folder. 🗂")
print("🧪 Run 'terraform plan' inside generated/terraform or 'ansible-playbook' inside generated/ansible.")

# === Apply Terraform Automatically ===
print("\n🚀 Deploying infrastructure with Terraform apply...")
# apply_result = os.system("cd generated/terraform && terraform init -upgrade > /dev/null 2>&1")
apply_result = os.system("cd generated/terraform && terraform apply -auto-approve")

if apply_result == 0:
    print("\n✅ Terraform apply completed successfully!")
else:
    print("\n❌ Terraform apply failed. Please check the output above for errors.")

# === Run Ansible Playbook Automatically ===
if apply_result == 0:
    print("\n📦 Running Ansible playbook to configure the provisioned VMs...")
    ansible_result = os.system("cd generated/ansible && ansible-playbook -i inventory.ini playbook.yml")
    
    if ansible_result == 0:
        print("\n✅ Ansible playbook executed successfully!")
    else:
        print("\n❌ Ansible playbook execution failed. Check the output for details.")
