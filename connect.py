import sys
import subprocess
from subprocess import check_output

out = check_output(["wpa_cli", "list_networks"]).decode(sys.stdout.encoding)
lines = out.splitlines()

ssid = 'Galaxy'
password = 'mkmg6228'

for i in range(len(lines)):
    if i > 1:
        parts = lines[i].split('\t')
        id = parts[0].strip()
        print('Removing existing network ', id)
        out = check_output(["wpa_cli", "remove_network", id]).decode(sys.stdout.encoding)
        print(out)

print('Adding a new network')
out = check_output(["wpa_cli", "add_network"]).decode(sys.stdout.encoding)
parts = out.splitlines()
id = parts[1]
print(out)

print('Setting SSID')
out = check_output(["wpa_cli", "set_network", id, "ssid", '"' + ssid + '"']).decode(sys.stdout.encoding)
print(out)

print('Setting password')
out = check_output(["wpa_cli", "set_network", id, "psk", '"' + password + '"']).decode(sys.stdout.encoding)
print(out)

print('Selecting network')
out = check_output(["wpa_cli", "select_network", id]).decode(sys.stdout.encoding)
print(out)

print('Enabling network')
out = check_output(["wpa_cli", "enable_network", id]).decode(sys.stdout.encoding)
print(out)

print('Saving configuration')
out = check_output(["wpa_cli", "save_config"]).decode(sys.stdout.encoding)
print(out)

print('Reconfiguring supplicant')
out = check_output(["wpa_cli", "reconfigure"]).decode(sys.stdout.encoding)
print(out)

print('Restarting daemon')
out = check_output(["sudo", "systemctl", "daemon-reload"]).decode(sys.stdout.encoding)
print(out)

print('Stopping network')
out = check_output(["sudo", "systemctl", "stop", "dhcpcd"]).decode(sys.stdout.encoding)
print(out)

print('Starting network')
out = check_output(["sudo", "systemctl", "start", "dhcpcd"]).decode(sys.stdout.encoding)
print(out)


