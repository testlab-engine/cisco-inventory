════════════════════════════════════════════════════════════════
Cisco Inventory Extractor Software Guide - Version 2.0
════════════════════════════════════════════════════════════════

────────────────────────────────────────────────────────────────

1. Introduction
   ────────────────────────────────────────────────────────────────
   This software extracts information from Cisco routers and switches and saves the data in an Excel file.

Version 2 features:
• Select required sections using checkboxes
• Device information (Serial / Model / IOS Version / Uptime)
• Interfaces + Description + IP + MAC + Status
• ARP table
• MAC Address table
• CDP and LLDP neighbors
• Save show startup-config as a separate text file
• Select the output directory
• Copy Operation Report button for troubleshooting
• Filter to show only Up interfaces

────────────────────────────────────────────────────────────────
2. Required Files
────────────────────────────────────────────────────────────────
• CiscoInventory_v2.exe
• devices.csv          (device list)
• Guide.txt            (this file)

────────────────────────────────────────────────────────────────
3. Creating the devices.csv File
────────────────────────────────────────────────────────────────

Option 1 – Different passwords for each device:

ip,device_type,username,password,secret
172.21.1.1,cisco_ios,admin,Pass@123,Enable@123
172.21.1.2,cisco_ios,netadmin,Cisco2024,Enable2024
172.21.1.5,cisco_ios,admin,AnotherPass,

Option 2 – One username and password for all devices:

ip,device_type
172.21.1.1,cisco_ios
172.21.1.2,cisco_ios

Allowed device_type values:
• cisco_ios
• cisco_xe
• cisco_nxos
• cisco_asa

────────────────────────────────────────────────────────────────
4. How to Run
────────────────────────────────────────────────────────────────

1. Place the devices.csv file in the same directory as the application.
2. Run the application.
3. Select the CSV file.
4. Specify the output directory (optional).
5. Select the authentication method.
6. Enable or disable the required sections using the checkboxes.
7. Click "Start Extraction".
8. Wait until the process is complete.

────────────────────────────────────────────────────────────────
5. Description of the Output Excel Sheets
────────────────────────────────────────────────────────────────
• Summary          → Summary of the status of each device
• Device_Info      → Serial, Model, Version, Uptime
• Interfaces       → Interface + Status + Description + IP + MAC
• ARP_Table        → Output of show ip arp
• MAC_Table        → Output of show mac address-table dynamic
• CDP_Neighbors    → CDP neighbors
• LLDP_Neighbors   → LLDP neighbors

If the startup-config option is enabled,
the configuration files will be saved in the startup_configs folder.

────────────────────────────────────────────────────────────────
6. "Copy Operation Report" Button
────────────────────────────────────────────────────────────────
If an error occurs, click this button to copy the complete operation report
to the clipboard. You can then send the report for troubleshooting.

────────────────────────────────────────────────────────────────
7. Common Issues
────────────────────────────────────────────────────────────────
• Authentication failed
→ The username, password, or Enable password is incorrect.

• TCP connection failed
→ The device is unreachable or SSH is not enabled.

• Permission denied for the Excel file
→ Close the previous Excel file.

• Unsupported device_type
→ Enter the correct device_type value (for example, cisco_ios).

────────────────────────────────────────────────────────────────
8. Security Notes
────────────────────────────────────────────────────────────────
• Passwords are not stored in the Excel file.
• If you use the CSV mode with passwords, keep the file in a secure location.
• After completing the task, you can delete the CSV file containing the passwords.



════════════════════════════════════════════════════════════════
