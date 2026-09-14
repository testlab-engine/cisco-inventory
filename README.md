# Cisco Inventory

A desktop application for collecting Cisco network inventory through SSH and exporting it to an Excel workbook.

## Features

- Collect device model, serial, IOS version, and uptime.
- Export interface, ARP, MAC-table, CDP, and LLDP data.
- Optionally save startup configurations locally.
- Use shared credentials entered in the app, or a local CSV that is excluded from Git.

## Requirements

- Python 3.10 or later
- Reachability to the Cisco devices over SSH

## Install and run

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python cisco_inventory.py
```

Choose `devices.example.csv` as the template for your local `devices.csv`. The minimal required columns are `ip` and, when using CSV credentials, `username` and `password`. `secret` and `device_type` are optional.

## Security

Do not commit device inventories, credentials, Excel reports, or startup configurations. They are ignored by default. The included example uses documentation-only IP addresses.

## License

MIT. See [LICENSE](LICENSE).
