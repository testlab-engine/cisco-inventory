"""Cisco network inventory collection desktop application.

The application reads a user-supplied CSV, connects with Netmiko, and writes
an Excel report. Device inventories, credentials, reports, and configurations
are deliberately excluded from this source distribution.
"""

from __future__ import annotations

import queue
import re
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
from netmiko import ConnectHandler
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk


class CiscoInventoryApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Cisco Inventory")
        self.root.geometry("900x720")

        self.csv_path = tk.StringVar()
        self.output_path = tk.StringVar(value=str(Path.cwd()))
        self.use_csv_credentials = tk.BooleanVar(value=False)
        self.options = {
            "device_info": tk.BooleanVar(value=True),
            "interfaces": tk.BooleanVar(value=True),
            "arp": tk.BooleanVar(value=True),
            "mac": tk.BooleanVar(value=True),
            "cdp": tk.BooleanVar(value=True),
            "lldp": tk.BooleanVar(value=False),
            "startup": tk.BooleanVar(value=False),
            "only_up": tk.BooleanVar(value=False),
        }
        self.events: queue.Queue[tuple[str, Any]] = queue.Queue()
        self.is_running = False
        self._build_ui()
        self.root.after(100, self._process_events)

    def _build_ui(self) -> None:
        ttk.Label(self.root, text="Cisco Inventory", font=("Segoe UI", 16, "bold")).pack(pady=(12, 8))

        files = ttk.LabelFrame(self.root, text="Input and output", padding=8)
        files.pack(fill="x", padx=15, pady=4)
        self._file_row(files, "Devices CSV", self.csv_path, self._browse_csv, "Choose CSV")
        self._file_row(files, "Output folder", self.output_path, self._browse_output, "Choose folder")

        auth = ttk.LabelFrame(self.root, text="Credentials", padding=8)
        auth.pack(fill="x", padx=15, pady=4)
        ttk.Radiobutton(auth, text="Enter shared credentials below", variable=self.use_csv_credentials,
                        value=False, command=self._toggle_credentials).grid(row=0, column=0, columnspan=6, sticky="w")
        ttk.Radiobutton(auth, text="Read credentials from CSV (do not commit that file)", variable=self.use_csv_credentials,
                        value=True, command=self._toggle_credentials).grid(row=1, column=0, columnspan=6, sticky="w")
        self.credential_entries: list[ttk.Entry] = []
        for column, label in enumerate(("Username", "Password", "Enable password")):
            ttk.Label(auth, text=label).grid(row=2, column=column * 2, sticky="w", pady=(8, 0))
            entry = ttk.Entry(auth, width=22, show="" if label == "Username" else "*")
            entry.grid(row=2, column=column * 2 + 1, padx=(4, 10), pady=(8, 0))
            self.credential_entries.append(entry)
        self.username_entry, self.password_entry, self.secret_entry = self.credential_entries

        options = ttk.LabelFrame(self.root, text="Data to collect", padding=8)
        options.pack(fill="x", padx=15, pady=4)
        labels = {
            "device_info": "Device information", "interfaces": "Interfaces", "arp": "ARP table",
            "mac": "MAC address table", "cdp": "CDP neighbors", "lldp": "LLDP neighbors",
            "startup": "Save startup configurations", "only_up": "Only interfaces that are up",
        }
        for index, (key, label) in enumerate(labels.items()):
            ttk.Checkbutton(options, text=label, variable=self.options[key]).grid(
                row=index // 2, column=index % 2, sticky="w", padx=10, pady=2
            )

        buttons = ttk.Frame(self.root)
        buttons.pack(pady=8)
        self.start_button = ttk.Button(buttons, text="Start collection", command=self.start)
        self.start_button.pack(side="left", padx=5)
        ttk.Button(buttons, text="Copy log", command=self._copy_log).pack(side="left", padx=5)

        self.progress = ttk.Progressbar(self.root, mode="determinate")
        self.progress.pack(fill="x", padx=15)
        self.status = ttk.Label(self.root, text="Ready", foreground="gray")
        self.status.pack(pady=(3, 0))
        log_frame = ttk.LabelFrame(self.root, text="Activity log", padding=5)
        log_frame.pack(fill="both", expand=True, padx=15, pady=8)
        self.log_text = scrolledtext.ScrolledText(log_frame, height=14, state="disabled", font=("Consolas", 9))
        self.log_text.pack(fill="both", expand=True)
        self._toggle_credentials()

    @staticmethod
    def _file_row(parent: ttk.LabelFrame, label: str, variable: tk.StringVar, command: Any, button_text: str) -> None:
        row = parent.grid_size()[1]
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", padx=(0, 8), pady=3)
        ttk.Entry(parent, textvariable=variable, width=74).grid(row=row, column=1, sticky="ew", pady=3)
        ttk.Button(parent, text=button_text, command=command).grid(row=row, column=2, padx=(8, 0), pady=3)
        parent.columnconfigure(1, weight=1)

    def _toggle_credentials(self) -> None:
        state = "disabled" if self.use_csv_credentials.get() else "normal"
        for entry in self.credential_entries:
            entry.configure(state=state)

    def _browse_csv(self) -> None:
        path = filedialog.askopenfilename(filetypes=[("CSV files", "*.csv"), ("All files", "*.*")])
        if path:
            self.csv_path.set(path)

    def _browse_output(self) -> None:
        path = filedialog.askdirectory()
        if path:
            self.output_path.set(path)

    def _copy_log(self) -> None:
        content = self.log_text.get("1.0", "end").strip()
        if content:
            self.root.clipboard_clear()
            self.root.clipboard_append(content)

    def start(self) -> None:
        csv_file = Path(self.csv_path.get())
        if not csv_file.is_file():
            messagebox.showerror("Missing input", "Choose an existing devices CSV file.")
            return
        if not self.use_csv_credentials.get() and not (self.username_entry.get().strip() and self.password_entry.get()):
            messagebox.showerror("Missing credentials", "Enter a username and password, or use CSV credentials.")
            return
        self.is_running = True
        self.start_button.configure(state="disabled")
        self.progress.configure(value=0)
        self._set_log("")
        self.status.configure(text="Collecting inventory…", foreground="blue")
        shared = (self.username_entry.get().strip(), self.password_entry.get(), self.secret_entry.get())
        threading.Thread(target=self._run, args=(csv_file, Path(self.output_path.get()), shared), daemon=True).start()

    def _run(self, csv_file: Path, output_dir: Path, shared: tuple[str, str, str]) -> None:
        try:
            devices = self._load_devices(csv_file, shared)
            if not devices:
                raise ValueError("The CSV contains no valid devices.")
            output_dir.mkdir(parents=True, exist_ok=True)
            config_dir = output_dir / "startup_configs"
            if self.options["startup"].get():
                config_dir.mkdir(exist_ok=True)
            self.events.put(("start", len(devices)))
            results: list[dict[str, Any]] = []
            with ThreadPoolExecutor(max_workers=min(5, len(devices))) as executor:
                futures = [executor.submit(self._collect_device, device, config_dir) for device in devices]
                for completed, future in enumerate(as_completed(futures), 1):
                    result = future.result()
                    results.append(result)
                    self.events.put(("progress", (completed, result["summary"]["IP"], result["summary"]["Status"])))
            report_path = self._write_report(results, output_dir)
            self.events.put(("complete", report_path))
        except Exception as error:  # report unexpected errors in the GUI
            self.events.put(("error", str(error)))

    def _load_devices(self, csv_file: Path, shared: tuple[str, str, str]) -> list[dict[str, str]]:
        frame = pd.read_csv(csv_file, dtype=str).fillna("")
        required = {"ip"}
        if self.use_csv_credentials.get():
            required.update({"username", "password"})
        missing = required - set(frame.columns.str.lower())
        if missing:
            raise ValueError(f"CSV is missing required column(s): {', '.join(sorted(missing))}")
        normalized = {column.lower(): column for column in frame.columns}
        devices = []
        for _, row in frame.iterrows():
            ip = row[normalized["ip"]].strip()
            if not ip:
                continue
            username, password, secret = shared
            if self.use_csv_credentials.get():
                username = row[normalized["username"]].strip()
                password = row[normalized["password"]]
                secret = row[normalized.get("secret", "")].strip() if "secret" in normalized else ""
            devices.append({"ip": ip, "device_type": row[normalized.get("device_type", "")].strip() or "cisco_ios",
                            "username": username, "password": password, "secret": secret or password})
        return devices

    def _collect_device(self, device: dict[str, str], config_dir: Path) -> dict[str, Any]:
        result: dict[str, Any] = {"summary": {"IP": device["ip"], "Hostname": "", "Status": "Failed"},
                                  "device_info": [], "switch_inventory": [], "interfaces": [], "arp": [], "mac": [], "cdp": [], "lldp": []}
        connection = None
        try:
            connection = ConnectHandler(device_type=device["device_type"], ip=device["ip"], username=device["username"],
                password=device["password"], secret=device["secret"], conn_timeout=40, banner_timeout=30, auth_timeout=30,
                fast_cli=False, disabled_algorithms={"pubkeys": ["rsa-sha2-512", "rsa-sha2-256"]})
            connection.enable()
            hostname = connection.find_prompt().rstrip("#>").strip()
            result["summary"]["Hostname"] = hostname
            if self.options["device_info"].get():
                version = connection.send_command("show version")
                model = self._extract_model(version)
                ios_version = self._match(r"Version\\s+([^\\s,]+)", version)
                result["device_info"].append({"Hostname": hostname, "Device_IP": device["ip"],
                    "Model": model, "Serial": self._match(r"Processor board ID\\s+(\\S+)", version),
                    "IOS_Version": ios_version, "Uptime": self._match(r"uptime is\\s+(.+)", version)})
                result["switch_inventory"] = [{"IP": device["ip"], "MODEL": model, "OS FIRMWARE": ios_version}]
            if self.options["interfaces"].get():
                result["interfaces"] = self._interfaces(connection, hostname, device["ip"])
            for key, command, parser in (("arp", "show ip arp", self._arp), ("mac", "show mac address-table dynamic", self._mac)):
                if self.options[key].get():
                    result[key] = parser(connection.send_command(command), hostname, device["ip"])
            if self.options["cdp"].get():
                result["cdp"] = self._cdp(connection.send_command("show cdp neighbors detail"), hostname, device["ip"])
            if self.options["lldp"].get():
                result["lldp"] = self._lldp(connection.send_command("show lldp neighbors detail"), hostname, device["ip"])
            if self.options["startup"].get():
                filename = re.sub(r'[\\/*?:"<>|]', "_", hostname) + f"_{device['ip']}_startup.txt"
                (config_dir / filename).write_text(connection.send_command("show startup-config"), encoding="utf-8")
            result["summary"]["Status"] = "Success"
        except Exception as error:
            result["summary"]["Status"] = f"Error: {error!s:.100}"
        finally:
            if connection:
                connection.disconnect()
        return result

    @staticmethod
    def _match(pattern: str, value: str) -> str:
        match = re.search(pattern, value, re.I | re.M)
        return match.group(1).strip() if match else ""

    @staticmethod
    def _extract_model(version: str) -> str:
        """Extract the Cisco hardware model from common `show version` formats."""
        patterns = (
            r"cisco\\s+(\\S+)\\s+\\(",
            r"Model Number\\s*[: ]\\s*(\\S+)",
            r"Model number\\s*[: ]\\s*(\\S+)",
        )
        for pattern in patterns:
            model = CiscoInventoryApp._match(pattern, version)
            if model:
                return model
        return ""

    def _interfaces(self, connection: Any, hostname: str, ip: str) -> list[dict[str, str]]:
        descriptions = {parts[0]: parts[3].strip() if len(parts) > 3 else "" for line in connection.send_command("show interfaces description").splitlines()[1:] if (parts := line.split(None, 3))}
        rows = []
        for line in connection.send_command("show ip interface brief").splitlines()[1:]:
            match = re.match(r"(\\S+)\\s+(\\S+)\\s+\\S+\\s+\\S+\\s+(\\S+)\\s+(\\S+)", line)
            if not match:
                continue
            interface, address, status, protocol = match.groups()
            if self.options["only_up"].get() and status.lower() != "up":
                continue
            rows.append({"Hostname": hostname, "Device_IP": ip, "Interface": interface, "Status": f"{status}/{protocol}",
                         "Description": descriptions.get(interface, ""), "IP_Address": "" if address.lower() == "unassigned" else address})
        return rows

    @staticmethod
    def _arp(output: str, hostname: str, device_ip: str) -> list[dict[str, str]]:
        rows = []
        for line in output.splitlines():
            match = re.match(r"Internet\\s+(\\d+(?:\\.\\d+){3})\\s+\\S+\\s+([0-9a-fA-F.]+)\\s+\\S+\\s+(\\S+)", line)
            if match:
                rows.append({"Hostname": hostname, "Device_IP": device_ip, "IP_Address": match.group(1), "MAC_Address": match.group(2), "Interface": match.group(3)})
        return rows

    @staticmethod
    def _mac(output: str, hostname: str, device_ip: str) -> list[dict[str, str]]:
        rows = []
        for line in output.splitlines():
            match = re.search(r"(\\d+)\\s+([0-9a-fA-F]{4}\\.[0-9a-fA-F]{4}\\.[0-9a-fA-F]{4})\\s+\\S+\\s+(\\S+)", line)
            if match:
                rows.append({"Hostname": hostname, "Device_IP": device_ip, "VLAN": match.group(1), "MAC_Address": match.group(2), "Port": match.group(3)})
        return rows

    @staticmethod
    def _cdp(output: str, hostname: str, device_ip: str) -> list[dict[str, str]]:
        rows = []
        for block in re.split(r"-{5,}", output):
            neighbor = CiscoInventoryApp._match(r"Device ID:\\s*(.+)", block)
            if neighbor:
                rows.append({"Hostname": hostname, "Device_IP": device_ip, "Neighbor_ID": neighbor,
                             "Neighbor_IP": CiscoInventoryApp._match(r"IP address:\\s*(\\S+)", block),
                             "Platform": CiscoInventoryApp._match(r"Platform:\\s*([^,]+)", block),
                             "Local_Interface": CiscoInventoryApp._match(r"Interface:\\s*(\\S+),", block),
                             "Remote_Interface": CiscoInventoryApp._match(r"Port ID \\(outgoing port\\):\\s*(\\S+)", block)})
        return rows

    @staticmethod
    def _lldp(output: str, hostname: str, device_ip: str) -> list[dict[str, str]]:
        return [{"Hostname": hostname, "Device_IP": device_ip, "Raw_Line": line.strip()} for line in output.splitlines() if "System Name:" in line or "Local Port:" in line]

    @staticmethod
    def _write_report(results: list[dict[str, Any]], output_dir: Path) -> Path:
        report = output_dir / f"cisco_inventory_{datetime.now():%Y%m%d_%H%M%S}.xlsx"
        with pd.ExcelWriter(report, engine="openpyxl") as writer:
            pd.DataFrame([item["summary"] for item in results]).to_excel(writer, sheet_name="Summary", index=False)
            switch_rows = [row for item in results for row in item["switch_inventory"]]
            if switch_rows:
                pd.DataFrame(switch_rows, columns=["IP", "MODEL", "OS FIRMWARE"]).to_excel(
                    writer, sheet_name="Switch_Inventory", index=False
                )
            for key, sheet in (("device_info", "Device_Info"), ("interfaces", "Interfaces"), ("arp", "ARP_Table"), ("mac", "MAC_Table"), ("cdp", "CDP_Neighbors"), ("lldp", "LLDP_Neighbors")):
                rows = [row for item in results for row in item[key]]
                if rows:
                    pd.DataFrame(rows).to_excel(writer, sheet_name=sheet, index=False)
        return report

    def _process_events(self) -> None:
        while not self.events.empty():
            kind, value = self.events.get()
            if kind == "start":
                self.progress.configure(maximum=value)
                self._log(f"Collecting inventory from {value} device(s).")
            elif kind == "progress":
                completed, ip, status = value
                self.progress.configure(value=completed)
                self.status.configure(text=f"Progress: {completed}/{self.progress['maximum']}")
                self._log(f"{ip}: {status}")
            elif kind == "complete":
                self.is_running = False
                self.start_button.configure(state="normal")
                self.status.configure(text="Complete", foreground="green")
                self._log(f"Report written to: {value}")
                messagebox.showinfo("Complete", f"Inventory report written to:\n{value}")
            elif kind == "error":
                self.is_running = False
                self.start_button.configure(state="normal")
                self.status.configure(text="Failed", foreground="red")
                self._log(f"Error: {value}")
                messagebox.showerror("Collection failed", str(value))
        self.root.after(100, self._process_events)

    def _log(self, message: str) -> None:
        self.log_text.configure(state="normal")
        self.log_text.insert("end", message + "\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def _set_log(self, message: str) -> None:
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.insert("end", message)
        self.log_text.configure(state="disabled")


if __name__ == "__main__":
    root = tk.Tk()
    CiscoInventoryApp(root)
    root.mainloop()
