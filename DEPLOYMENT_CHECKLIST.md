# Real Estate CRM - Deployment & Installation Checklist

## Pre-Installation Checklist

### System Requirements
- [ ] Windows 10 or Windows 11 (64-bit)
- [ ] At least 2 GB RAM available
- [ ] 500 MB disk space free (+ database size)
- [ ] .NET Framework 4.5+ (optional, for advanced features)
- [ ] Administrator access for firewall configuration

### Network Setup (for LAN/Multi-user)
- [ ] Local network available
- [ ] Server machine identified
- [ ] Static IP assigned to server (recommended)
- [ ] Firewall port 6090 accessible (local network)

## Installation Steps

### Step 1: Download Installer
1. Download: `RealEstateCRM_v2.1.0_Setup.exe`
2. Verify file integrity (if provided)
3. Save to a temporary location

### Step 2: Run Installer
1. Right-click installer → "Run as administrator"
2. Click "Next" to proceed through wizard
3. Read and accept license terms
4. Choose installation location (default recommended)

### Step 3: Select Components
- [ ] Create desktop shortcut
- [ ] Create Quick Launch icon
- [ ] Auto-start LAN server (if using LAN)
- [ ] Setup remote tunnel (optional)

### Step 4: Complete Installation
1. Click "Install"
2. Wait for completion (2-3 minutes)
3. Review post-install options
4. Click "Finish"

### Step 5: First Launch
1. **Desktop**: Double-click "Real Estate CRM" icon
2. **LAN Server**: Click "CRM LAN Web Server" in Start Menu

## Post-Installation Setup

### Desktop Application
1. **First Run**:
   - Application launches in local mode
   - Database initializes automatically
   - Create admin account

2. **Network Access** (optional):
   - Connect to LAN server
   - Enter server IP: `192.168.x.x:6090`

### LAN Web Server
1. **Start Server**:
   - Click "CRM LAN Web Server" shortcut
   - Console window appears showing port 6090
   - Server is ready when you see "Uvicorn running"

2. **Access from Client**:
   - Browser URL: `http://[SERVER_IP]:6090`
   - Login with admin credentials
   - Configure firewall if needed

3. **Auto-Start**:
   - Check "Auto-start on boot" option in installer
   - Or manually add to Windows Startup folder

## Firewall Configuration (for Network Access)

### Windows Firewall - Automatic
The installer attempts to configure firewall automatically. If it fails:

### Windows Firewall - Manual
1. **Open Windows Defender Firewall**:
   - Settings → Privacy & Security → Windows Defender Firewall
   - Click "Allow an app through firewall"

2. **Add Port 6090**:
   - Click "Allow another app"
   - Browse: `C:\Users\[User]\AppData\Local\Programs\Real Estate CRM\RealEstateCRM_LAN_Server.exe`
   - Check "Private" (LAN only)
   - Check "Public" (if needed for remote)
   - Click "Add"

3. **Test Connection**:
   - From another computer: `http://[SERVER_IP]:6090`
   - Should load login page

### Third-Party Firewall
Refer to your firewall documentation to allow:
- **Application**: RealEstateCRM_LAN_Server.exe
- **Port**: TCP 6090
- **Direction**: Inbound
- **Scope**: Local Network (or Any)

## Troubleshooting

### Application Won't Launch
**Symptom**: Clicking shortcut does nothing
**Solutions**:
1. Check antivirus hasn't quarantined the app
2. Run Command Prompt as admin:
   ```cmd
   cd "C:\Users\%USERNAME%\AppData\Local\Programs\Real Estate CRM"
   RealEstateCRM_Qt.exe -debug
   ```
3. Check error messages and report

### LAN Server Not Accessible
**Symptom**: Cannot connect from other computers
**Solutions**:
1. Verify server is running (console window open)
2. Check both computers on same network
3. Test with server's own IP:
   - On server: `http://localhost:6090`
   - Should work
4. Configure firewall (see above)
5. Check port isn't blocked:
   ```cmd
   netstat -an | findstr :6090
   ```

### Database Connection Error
**Symptom**: "Cannot connect to database"
**Solutions**:
1. Verify database file exists:
   ```
   C:\Users\%USERNAME%\AppData\Local\Programs\Real Estate CRM\real_estate_crm.db
   ```
2. Check file permissions (not read-only)
3. Restart application

### Performance Issues
**Symptom**: Application slow, sluggish
**Solutions**:
1. Check available RAM and disk space
2. Close other applications
3. Move database to faster drive (SSD)
4. Check database isn't corrupted:
   - Backup database
   - Delete and reinstall

### Data Loss or Corruption
**Recovery Steps**:
1. **Locate Backups**:
   ```
   C:\Users\%USERNAME%\AppData\Local\Programs\Real Estate CRM\database_backups\
   ```
2. **Restore from Backup**:
   - Stop application
   - Replace corrupted database with backup
   - Restart application

3. **If No Backup**:
   - Contact support with backup files
   - IT department may have system backups

## Uninstallation

### Remove Program
1. **Control Panel Method**:
   - Settings → Apps → Apps & features
   - Search "Real Estate CRM"
   - Click Uninstall

2. **Add/Remove Programs**:
   - Control Panel → Programs → Programs and Features
   - Select "Real Estate CRM"
   - Click Uninstall

### Data Preservation
The uninstaller will ask:
- [ ] Keep database files (recommended)
- [ ] Keep exported reports and backups
- [ ] Keep configuration files

**Recommended**: Answer YES to all

### Clean Uninstall
If complete removal is required:
1. Uninstall through Control Panel
2. Remove folder manually:
   ```
   C:\Users\%USERNAME%\AppData\Local\Programs\Real Estate CRM
   ```
3. Remove shortcuts from desktop/taskbar

## Multi-User Setup (LAN)

### Server Computer
1. Install application (steps above)
2. Start "CRM LAN Web Server" from Start Menu
3. Keep server running for client access
4. Configure firewall for network

### Client Computers
1. Install application on each client
2. First launch shows options:
   - "Connect to LAN server" checkbox
   - Enter server IP: `192.168.x.x`
   - Enter port: `6090` (default)

3. Login with network credentials

### Network Administration
- Users can have separate accounts
- Server manages all data
- Backups centralized on server
- Reports accessible from any client

## Remote Access (Optional)

### Cloudflare Tunnel Setup
1. **Download Cloudflared**:
   - Already included in installer
   - Located in Tools folder

2. **Configure Tunnel**:
   - In Start Menu: "Setup Remote CRM Tunnel"
   - Authenticate with Cloudflare account
   - Get remote URL

3. **Access from Anywhere**:
   - Share tunnel URL with authorized users
   - No public IP or port forwarding needed
   - Secure SSL encryption included

4. **Stop Tunnel**:
   - In Start Menu: "Stop Remote CRM Tunnel"

### VPN Alternative
If using corporate VPN:
1. Connect to VPN first
2. Then access: `http://[SERVER_IP]:6090`

## Support & Maintenance

### Regular Maintenance
- **Weekly**: Check available disk space
- **Monthly**: Backup database files
- **Monthly**: Review user accounts
- **Quarterly**: Update application

### Getting Help
- **Error Messages**: Note exact text and screenshots
- **Documentation**: Check README.md in application folder
- **Contact Support**: info@msxhan.online

### Reporting Issues
Include:
1. Windows version (Settings → System → About)
2. Application version (About menu in app)
3. Error message (exact text)
4. Steps to reproduce
5. Screenshots if applicable

## Version Updates

### Update Process
1. Download new installer: `RealEstateCRM_v2.2.0_Setup.exe`
2. Run installer (old version will be closed)
3. Click "Update" instead of new install
4. Database and settings preserved
5. Application ready to use

### Backup Before Update
1. Backup database:
   ```
   C:\Users\%USERNAME%\AppData\Local\Programs\Real Estate CRM\real_estate_crm.db
   ```
2. Backup reports in outputs folder
3. Keep backup until new version tested

## Quick Reference

| Task | Steps |
|------|-------|
| Start CRM | Click desktop shortcut or Start Menu |
| Start LAN Server | Click "CRM LAN Web Server" in Start Menu |
| Access Web (Local) | Browser: http://127.0.0.1:6090 |
| Access Web (Network) | Browser: http://[SERVER_IP]:6090 |
| Configure Firewall | Settings → Firewall → Allow app → Add RealEstateCRM_LAN_Server.exe |
| Uninstall | Settings → Apps → Apps & features → Real Estate CRM → Uninstall |
| Backup Data | Copy database and outputs folder to external drive |
| Restore Backup | Copy backup files back to application folder |
| Check Database | File explorer: C:\Users\%USERNAME%\AppData\Local\Programs\Real Estate CRM |

## Logs & Diagnostics

### Application Logs
Located in: `C:\Users\%USERNAME%\AppData\Local\Programs\Real Estate CRM\logs\`

### Server Logs
Console window shows live server activity when running

### Error Reports
Automatically saved in: `C:\Users\%USERNAME%\AppData\Local\Programs\Real Estate CRM\outputs\errors\`

### Collect Diagnostic Info
```cmd
# Create diagnostic bundle
cd "C:\Users\%USERNAME%\AppData\Local\Programs\Real Estate CRM"

# Copy important files
mkdir diagnostic_backup
copy *.db diagnostic_backup\
copy *.log diagnostic_backup\
copy outputs\*.* diagnostic_backup\ /S

# Send diagnostic_backup folder to support
```

---

**Document Version**: 2.1.0  
**Last Updated**: 2026-06-05  
**For Support**: info@msxhan.online
