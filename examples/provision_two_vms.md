### Prompt:

Provision 2 Ubuntu 22.04 VMs in GCP using e2-micro machine type inside a new VPC called vpc-001 in which you create a new subnet called subnet-001 which uses IP address range 10.10.10.0/24. Assign both VMs internal IPs 10.10.10.100 and 10.10.10.101. Also, on VM1 install nginx and on VM2 install mariadb. The SSH authorized key should be for user abanand — who should be in sudoers and whose password should be "Cat4Dog!". Ports 22, 80, 443 and ICMP should be allowed for these VMs.

---

This prompt will trigger:
- Terraform code to provision VPC, subnet, firewall, and 2 VMs
- Ansible playbook to configure nginx on one and mariadb on the other
- Dynamic inventory generation
- Fully automatic deployment
