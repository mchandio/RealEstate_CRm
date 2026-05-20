# Real Estate CRM Multiuser LAN Setup

Run the CRM on the main office computer that holds `real_estate_crm.db`.
Other computers on the same router can open the CRM in a browser at port `6090`.

## Start the Server

Recommended host mode: start the Qt CRM on the main/server computer. After login,
the desktop app automatically starts the browser portal on:

```text
http://<server-ip-address>:6090
```

You can also run only the browser server by double-clicking:

```text
start_lan_server.bat
```

Keep the server computer and CRM/server window open while staff are using the CRM.

The server shows URLs like:

```text
Local browser:  http://127.0.0.1:6090
Office network: http://192.168.x.x:6090
```

Staff on other computers should open the `Office network` URL.

## Login

Use the same users created in the Qt CRM Users screen.

Default current test users in this database:

```text
admin / admin
staf / staf
```

Change default passwords before real office use.

## Firewall

If other computers cannot open the CRM URL, right-click this file and choose
`Run as administrator`:

```text
enable_crm_firewall_6090.bat
```

It opens inbound TCP port `6090` for the CRM.

Your server network should normally be `Private`, not `Public`, for office LAN
sharing. The firewall script will show the current profile and can switch the
connected office network to `Private` when you confirm it.

## If Only Some Computers Connect

On the server computer, double-click:

```text
diagnose_lan_server.bat
```

Then check each client:

- Client must be on the same office Wi-Fi/LAN as the server, not Guest Wi-Fi.
- Client should open the server IP shown by the diagnostics, for example `http://192.168.10.3:6090`.
- On the client, run PowerShell: `Test-NetConnection 192.168.10.3 -Port 6090`.
- If the port test fails but the client is on the same network, run `enable_crm_firewall_6090.bat` as Administrator on the server.
- If ping/port both fail, the router may have Guest Wi-Fi, AP isolation, VLAN isolation, or a different subnet blocking client-to-client traffic.

## Important

Port `6090` can be used by only one program at a time. The Qt desktop app now
uses `6091` for its internal desktop API and `6090` for the browser login
server. If `start_lan_server.bat` is already running, the Qt app will detect
that port `6090` is already in use and will leave the existing browser server
running.
