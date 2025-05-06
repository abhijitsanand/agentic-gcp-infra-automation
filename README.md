# agentic-gcp-infra-automation
A Python-powered Agentic AI script that uses Google Gemini, LangChain, and Terraform to provision GCP infrastructure using natural language prompts — complete with auto-generated Ansible playbooks and full deployment.

# Agentic GCP Infra Automation 🚀

This project demonstrates how to use **Agentic AI**, **LangChain**, and **Google Gemini** to fully automate GCP infrastructure provisioning from **natural language prompts**.

## 🧠 What It Does

- Accepts plain English prompts (e.g., “Provision 2 Ubuntu VMs on GCP...”)
- Uses Gemini + LangChain to:
  - Generate Terraform code for GCP
  - Generate Ansible playbooks for server configuration
  - Critique and validate both
- Automatically:
  - Saves code to disk
  - Runs `terraform apply`
  - Extracts IPs from state
  - Runs `ansible-playbook`

## 💬 Example Prompt

```text
Provision 2 Ubuntu 22.04 VMs in GCP using e2-micro machine type inside a new VPC called vpc-001 in which you create a new subnet called subnet-001 which uses IP address range 10.10.10.0/24. Assign both VMs internal IPs 10.10.10.100 and 10.10.10.101. Also, on VM1 install nginx and on VM2 install mariadb. The SSH authorized key should be for user abanand — who should be in sudoers and whose password should be "Cat4Dog!". Ports 22, 80, 443 and ICMP should be allowed for these VMs.
