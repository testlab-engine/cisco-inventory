# Cisco Inventory

A desktop application for collecting Cisco network inventory through SSH and exporting it to an Excel workbook.

## Features

- Collect device model, serial number, IOS/IOS-XE version, hostname, uptime, management IP, and device type.
- Optionally collect a full device inventory from the GUI with the **Device inventory** checkbox.
- Export the full inventory to an `Inventory` worksheet.
- Separate detected Cisco **Switches** and **Routers** into dedicated Excel worksheets.
- Export interface, ARP, MAC-table, CDP, and LLDP data.
- Optionally save startup configurations locally.
- Use shared credentials entered in the app, or a local CSV that is excluded from Git.

## Requirements

- Python 3.10 or later
- Reachability to the Cisco devices over SSH
- For legacy Cisco SSH devices that only offer SHA-1 algorithms, use **Paramiko 4.x**. The project is currently tested with Paramiko 4.0.0 and Netmiko 4.8.0.

## Install and run

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python cisco_inventory.py
```

Choose `devices.example.csv` as the template for your local `devices.csv`. The minimal required columns are `ip` and, when using CSV credentials, `username` and `password`. `secret` and `device_type` are optional.

## Device inventory

Enable **Device inventory** when you want a hardware/software inventory in Excel.

The inventory includes:

- IP
- MODEL
- OS FIRMWARE
- Hostname
- Serial Number
- Uptime
- Management IP
- Device Type

The generated workbook can contain:

- `Inventory` — all detected devices
- `Switches` — devices detected as switches
- `Routers` — devices detected as routers

Device type detection is based on common Cisco platform/model information returned by `show version`.

## Legacy Cisco SSH

Some older Cisco platforms may only offer legacy SSH algorithms such as:

- `diffie-hellman-group14-sha1`
- `ssh-rsa`
- `hmac-sha1`

These algorithms are deprecated, but may still be required for older network devices. For this reason, the project uses Paramiko 4.x compatibility rather than requiring changes to the SSH configuration of the Cisco devices.

## Security

Do not commit device inventories, credentials, Excel reports, or startup configurations. They are ignored by default. The included example uses documentation-only IP addresses.

## License

MIT. See [LICENSE](LICENSE).
