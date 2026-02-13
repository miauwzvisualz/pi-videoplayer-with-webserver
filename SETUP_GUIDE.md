# Complete Raspberry Pi Setup Guide

Full setup guide for the Video/Audio Player with Web Upload Server.

This system lets you:
- **Video mode**: Play videos in a loop on a connected display (for LED strip art, etc.)
- **Audio mode**: Play audio files in a loop through the Pi's audio output
- **Web interface**: Upload/delete files and switch modes from any device on your network

---

## 1. Prerequisites

### Hardware
- Raspberry Pi (tested on Pi 3/4/5)
- MicroSD card with Raspberry Pi OS Lite (no desktop needed)
- Network connection (Wi-Fi or Ethernet)
- For video mode: HDMI display
- For audio mode: speakers connected via 3.5mm jack, HDMI, or USB audio

### Initial Pi Setup
If starting from scratch, flash Raspberry Pi OS Lite using the Raspberry Pi Imager. Enable SSH during flashing so you can connect remotely.

---

## 2. System Dependencies

SSH into your Pi and install everything:

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Core dependencies
sudo apt install -y python3 python3-pip ffmpeg

# Audio playback (install at least one)
sudo apt install -y mpv

# Video playback requires X11 (minimal)
sudo apt install -y xserver-xorg xinit

# Python dependencies
pip3 install flask werkzeug
```

---

## 3. Copy Project Files to the Pi

From your computer, copy the project to the Pi:

```bash
# From your local machine (adjust paths as needed)
scp -r ./* pi@<PI_IP>:/home/pi/
```

Or if using git:

```bash
# On the Pi
cd /home/pi
git clone <your-repo-url> .
```

### Verify files are in place

```bash
ls -la /home/pi/
```

You should see:
```
/home/pi/
├── audio_player.py
├── video_player.py
├── video_upload_server.py
├── video_config.sh
├── .xinitrc
├── html/
│   ├── index.html
│   ├── style.css
│   └── camcat_BW.svg
├── audio-player.service
├── requirements.txt
└── ...
```

---

## 4. Create Required Folders

```bash
mkdir -p /home/pi/videos/uploads
mkdir -p /home/pi/audio
```

---

## 5. Install Systemd Services

### 5a. Video Player Service

This should already exist if you had the previous setup. If not:

```bash
sudo cp /home/pi/audio-player.service /etc/systemd/system/audio-player.service
```

For reference, the video player service at `/etc/systemd/system/video-player-x11.service` should contain:

```ini
[Unit]
Description=Video Player with X11
After=multi-user.target

[Service]
Type=simple
User=pi
Group=pi
WorkingDirectory=/home/pi
ExecStart=/usr/bin/xinit /home/pi/.xinitrc -- :0 -nolisten tcp vt1
Restart=always
RestartSec=10
Environment=HOME=/home/pi

[Install]
WantedBy=multi-user.target
```

If it doesn't exist yet:

```bash
sudo nano /etc/systemd/system/video-player-x11.service
# Paste the content above, save with Ctrl+O, exit with Ctrl+X
```

### 5b. Audio Player Service

```bash
sudo cp /home/pi/audio-player.service /etc/systemd/system/audio-player.service
```

### 5c. Web Upload Server Service

```bash
sudo nano /etc/systemd/system/video-upload.service
```

Paste:

```ini
[Unit]
Description=Video/Audio Upload Web Server
After=network.target

[Service]
Type=simple
User=pi
Group=pi
WorkingDirectory=/home/pi
ExecStart=/usr/bin/python3 /home/pi/video_upload_server.py
Restart=always
RestartSec=10
Environment=HOME=/home/pi

[Install]
WantedBy=multi-user.target
```

Save and exit.

---

## 6. Configure X11 (Video Mode Only)

Allow systemd to start X11 without a logged-in user:

```bash
sudo nano /etc/X11/Xwrapper.config
```

Set:
```
allowed_users=anybody
```

---

## 7. Allow Service Switching Without Password

The web server uses `sudo systemctl` to start/stop/restart services and to reboot/shutdown. The `pi` user needs passwordless sudo for these specific commands:

```bash
sudo visudo -f /etc/sudoers.d/player-services
```

Paste:

```
pi ALL=(ALL) NOPASSWD: /bin/systemctl start video-player-x11.service
pi ALL=(ALL) NOPASSWD: /bin/systemctl stop video-player-x11.service
pi ALL=(ALL) NOPASSWD: /bin/systemctl restart video-player-x11.service
pi ALL=(ALL) NOPASSWD: /bin/systemctl start audio-player.service
pi ALL=(ALL) NOPASSWD: /bin/systemctl stop audio-player.service
pi ALL=(ALL) NOPASSWD: /bin/systemctl restart audio-player.service
pi ALL=(ALL) NOPASSWD: /sbin/reboot
pi ALL=(ALL) NOPASSWD: /sbin/shutdown
```

Save with Ctrl+O, exit with Ctrl+X.

---

## 8. Enable and Start Services

```bash
# Reload systemd to pick up new service files
sudo systemctl daemon-reload

# Enable services to start on boot
sudo systemctl enable video-upload.service
sudo systemctl enable video-player-x11.service
# Don't enable audio-player - it's started/stopped by the web server based on mode

# Start the web server (always runs)
sudo systemctl start video-upload.service

# Start the video player (default mode)
sudo systemctl start video-player-x11.service
```

Set the default mode:

```bash
echo "video" > /home/pi/.player_mode
```

---

## 9. Configure Audio Output (Audio Mode)

### 3.5mm Jack
```bash
# Force audio to 3.5mm jack
sudo raspi-config
# Advanced Options > Audio > Force 3.5mm
```

Or via command line:
```bash
amixer cset numid=3 1   # 1 = 3.5mm jack, 2 = HDMI
```

### Set Volume
```bash
amixer set Master 80%
# or
alsamixer   # Interactive volume control
```

### USB Audio
If using a USB audio device, check it's detected:
```bash
aplay -l
```

For mpv, you can specify the audio device in `/home/pi/audio_player.py` if needed.

---

## 10. Using the System

### Web Interface

Open a browser on any device on your network and go to:

```
http://<PI_IP>:5000
```

Find your Pi's IP with:
```bash
hostname -I
```

The web interface lets you:
- **Switch modes** between Video Player and Audio Player (buttons at top)
- **Upload files** via drag-and-drop
- **Delete files** from the file list
- **Reboot/Shutdown** the Pi

### What Happens When You Switch Modes

- **Video → Audio**: Stops `video-player-x11.service`, starts `audio-player.service`
- **Audio → Video**: Stops `audio-player.service`, starts `video-player-x11.service`
- The mode is persisted in `/home/pi/.player_mode` and survives reboots

### File Locations

| Content | Folder | Notes |
|---------|--------|-------|
| Raw video uploads | `/home/pi/videos/uploads/` | Original files before processing |
| Processed videos | `/home/pi/videos/` | What the video player actually plays |
| Audio files | `/home/pi/audio/` | Played directly, no processing needed |

---

## 11. Quick Command Reference

### Service Management
```bash
# Web server (always running)
sudo systemctl status video-upload.service
sudo systemctl restart video-upload.service

# Video player
sudo systemctl status video-player-x11.service
sudo systemctl start video-player-x11.service
sudo systemctl stop video-player-x11.service

# Audio player
sudo systemctl status audio-player.service
sudo systemctl start audio-player.service
sudo systemctl stop audio-player.service
```

### Logs
```bash
# Web server logs
sudo journalctl -u video-upload.service -f
cat /tmp/video_upload_server.log

# Video player logs
sudo journalctl -u video-player-x11.service -f
cat /tmp/video_player.log

# Audio player logs
sudo journalctl -u audio-player.service -f
cat /tmp/audio_player.log
```

### Manual Testing
```bash
# Test audio player manually
python3 /home/pi/audio_player.py /home/pi/audio

# Test video player manually
python3 /home/pi/video_player.py /home/pi/videos

# Test web server manually
python3 /home/pi/video_upload_server.py
```

---

## 12. Troubleshooting

### Web interface not loading
```bash
# Check if server is running
sudo systemctl status video-upload.service

# Check firewall
sudo ufw allow 5000

# Check the IP
hostname -I
```

### No audio output
```bash
# Check audio devices
aplay -l

# Test audio output
speaker-test -t wav -c 2

# Check volume
alsamixer

# Check if mpv works
mpv --no-video /home/pi/audio/test.mp3
```

### Mode switch not working
```bash
# Check mode file
cat /home/pi/.player_mode

# Check sudoers
sudo -l -U pi

# Try manually
sudo systemctl stop video-player-x11.service
sudo systemctl start audio-player.service
```

### Video not displaying
```bash
# Check X11
ps aux | grep Xorg

# Check display
echo $DISPLAY   # Should be :0

# Check X11 permissions
cat /etc/X11/Xwrapper.config
```

### Disk space
```bash
df -h
# Clean up if needed
du -sh /home/pi/videos/uploads/
```

---

## 13. Supported Formats

### Video
MP4, AVI, MKV, MOV, WMV, FLV, WebM, M4V, MPG, MPEG

**Required resolution for upload**: 3072x64 pixels (LED strip format)

### Audio
MP3, WAV, FLAC, OGG, M4A, AAC, WMA, OPUS, AIFF, ALAC

No resolution/format restrictions — any audio file is accepted and played directly.

---

## 14. Setting Up a Wi-Fi Access Point

If you want to connect to the Pi directly (e.g. at an installation without existing Wi-Fi), you can turn it into its own Access Point.

> **Which method to use?**
> - **Bookworm / Trixie** (2023+): Use **Method A** — NetworkManager handles everything.
> - **Bullseye or older**: Use **Method B** — the classic hostapd + dnsmasq approach.
>
> Check your version with: `cat /etc/os-release`

---

### Method A: NetworkManager (Bookworm / Trixie)

This is a single command. NetworkManager handles the AP, DHCP, and IP assignment — no extra packages needed.

#### A1. Create the Access Point

```bash
sudo nmcli connection add \
  con-name ap0 \
  type wifi \
  ifname wlan0 \
  ssid PiPlayer \
  802-11-wireless.mode ap \
  802-11-wireless.band bg \
  wifi-sec.key-mgmt wpa-psk \
  wifi-sec.psk "YourPasswordHere" \
  wifi-sec.pairwise ccmp \
  wifi-sec.proto rsn \
  ipv4.method shared \
  ipv4.address 192.168.4.1/24 \
  autoconnect yes
```

> Change `PiPlayer` and `YourPasswordHere` to your liking. The password must be at least 8 characters.

#### A2. Activate the Access Point

```bash
sudo nmcli connection up ap0
```

That's it. The AP is now active and will auto-start on boot.

#### A3. Connect and Use

Connect to the **PiPlayer** Wi-Fi network, then open:

```
http://192.168.4.1:5000
```

#### A4. Managing the Access Point

```bash
# Check AP status
nmcli connection show ap0

# Stop the AP
sudo nmcli connection down ap0

# Start the AP
sudo nmcli connection up ap0

# Remove the AP entirely
sudo nmcli connection delete ap0

# Change the password
sudo nmcli connection modify ap0 wifi-sec.psk "NewPassword"

# Change the SSID
sudo nmcli connection modify ap0 ssid "NewName"
```

#### A5. Troubleshooting (NetworkManager)

```bash
# Check if wlan0 has the static IP
ip addr show wlan0

# Check NetworkManager logs
sudo journalctl -u NetworkManager -f

# List all connections
nmcli connection show

# Check Wi-Fi device state
nmcli device status
```

---

### Method B: hostapd + dnsmasq (Bullseye and older)

For older Raspberry Pi OS versions that use `dhcpcd` instead of NetworkManager.

#### B1. Install Required Packages

```bash
sudo apt install -y hostapd dnsmasq
```

Stop both services while configuring:

```bash
sudo systemctl stop hostapd
sudo systemctl stop dnsmasq
```

#### B2. Configure a Static IP for the Wireless Interface

```bash
sudo nano /etc/dhcpcd.conf
```

Add at the bottom:

```
interface wlan0
    static ip_address=192.168.4.1/24
    nohook wpa_supplicant
```

#### B3. Configure the DHCP Server (dnsmasq)

Back up the original config and create a new one:

```bash
sudo mv /etc/dnsmasq.conf /etc/dnsmasq.conf.orig
sudo nano /etc/dnsmasq.conf
```

Paste:

```
interface=wlan0
dhcp-range=192.168.4.2,192.168.4.50,255.255.255.0,24h
```

This hands out IPs in the `192.168.4.2–50` range to connected clients.

#### B4. Configure the Access Point (hostapd)

```bash
sudo nano /etc/hostapd/hostapd.conf
```

Paste (adjust `ssid` and `wpa_passphrase` to your liking):

```
interface=wlan0
driver=nl80211
ssid=PiPlayer
hw_mode=g
channel=7
wmm_enabled=0
macaddr_acl=0
auth_algs=1
ignore_broadcast_ssid=0
wpa=2
wpa_passphrase=YourPasswordHere
wpa_key_mgmt=WPA-PSK
wpa_pairwise=TKIP
rsn_pairwise=CCMP
```

> Change `ssid` and `wpa_passphrase` to whatever you want. The password must be at least 8 characters.

Now tell hostapd where to find this config:

```bash
sudo nano /etc/default/hostapd
```

Find the line `#DAEMON_CONF=""` and replace it with:

```
DAEMON_CONF="/etc/hostapd/hostapd.conf"
```

#### B5. Enable and Start the Services

```bash
sudo systemctl unmask hostapd
sudo systemctl enable hostapd
sudo systemctl enable dnsmasq

sudo systemctl start hostapd
sudo systemctl start dnsmasq
```

Reboot to make sure everything comes up cleanly:

```bash
sudo reboot
```

#### B6. Connect and Use

After reboot, you should see a Wi-Fi network called **PiPlayer** (or whatever you set as `ssid`). Connect to it with the password you configured, then open:

```
http://192.168.4.1:5000
```

#### B7. Troubleshooting (hostapd)

```bash
# Check hostapd status
sudo systemctl status hostapd

# Check dnsmasq status
sudo systemctl status dnsmasq

# Check if wlan0 has the static IP
ip addr show wlan0

# View hostapd logs
sudo journalctl -u hostapd -f

# If hostapd fails, test config manually
sudo hostapd -dd /etc/hostapd/hostapd.conf
```

#### B8. Captive Portal (Auto-Open Upload UI)

When enabled, devices connecting to the PiPlayer AP will automatically get a **"Sign in to network"** popup that opens the upload UI — no need to manually type the IP address.

**How it works:**
1. **DNS hijacking** — dnsmasq resolves all domain names to `192.168.4.1`
2. **Port redirect** — nftables redirects HTTP port 80 → Flask port 5000
3. **Portal detection** — Flask responds to OS captive portal check URLs with a redirect to the upload UI

**Automated setup:**

```bash
sudo bash setup_captive_portal.sh
```

**Manual setup (if you prefer):**

**Step 1: Add DNS hijacking to dnsmasq**

Add this line to `/etc/dnsmasq.conf`:

```
address=/#/192.168.4.1
```

This tells dnsmasq to resolve *every* domain name to the Pi's IP.

**Step 2: Add port 80 → 5000 redirect**

Create `/etc/nftables-captive-portal.conf`:

```
#!/usr/sbin/nft -f
table ip captive_portal {
    chain prerouting {
        type nat hook prerouting priority dstnat; policy accept;
        iifname "wlan0" tcp dport 80 redirect to :5000
    }
}
```

Apply it:

```bash
sudo nft -f /etc/nftables-captive-portal.conf
```

**Step 3: Make it persistent across reboots**

Create `/etc/systemd/system/captive-portal.service`:

```ini
[Unit]
Description=Captive Portal nftables rules
After=network-pre.target
Before=network.target

[Service]
Type=oneshot
ExecStart=/usr/sbin/nft -f /etc/nftables-captive-portal.conf
ExecStop=/usr/sbin/nft delete table ip captive_portal
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
```

Enable it:

```bash
sudo systemctl daemon-reload
sudo systemctl enable captive-portal.service
sudo systemctl restart dnsmasq
```

**Disabling the captive portal:**

```bash
sudo systemctl stop captive-portal
sudo nft delete table ip captive_portal
# Remove the "address=/#/192.168.4.1" line from /etc/dnsmasq.conf
sudo systemctl restart dnsmasq
```

**Troubleshooting captive portal:**

```bash
# Check if DNS hijacking is working (should return 192.168.4.1)
nslookup google.com 192.168.4.1

# Check if nftables redirect is active
sudo nft list table ip captive_portal

# Check captive portal service
sudo systemctl status captive-portal

# Test manually from a connected device
curl -v http://captive.apple.com/hotspot-detect.html
```

---

> **Note**: When running as an AP, the Pi's `wlan0` is no longer connected to your home Wi-Fi. If you need internet access on the Pi (e.g. for updates), connect via Ethernet or temporarily disable the AP and reconnect to Wi-Fi.
