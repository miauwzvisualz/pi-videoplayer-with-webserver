#!/bin/bash
# Captive Portal Setup Script for PiPlayer AP (NetworkManager)
# This script configures DNS hijacking and port redirection
# so that devices connecting to the AP automatically see the upload UI.
#
# Prerequisites:
#   - NetworkManager AP connection (ap0) already configured
#   - Flask server running on port 5000
#   - Run as root: sudo bash setup_captive_portal.sh

set -e

PI_IP="192.168.4.1"
FAKE_IP="4.3.2.1"  # Public IP for DNS hijacking (Android ignores private IPs)
FLASK_PORT="5000"
IFACE="wlan0"
NM_CONNECTION="ap0"

echo "=== PiPlayer Captive Portal Setup ==="
echo ""

# --- 1. Configure DNS hijacking via NetworkManager's dnsmasq ---
echo "[1/4] Configuring DNS hijacking for NetworkManager's dnsmasq..."

# NetworkManager uses its own dnsmasq instance in "shared" mode.
# Drop-in config files go in /etc/NetworkManager/dnsmasq-shared.d/
DNSMASQ_DROPIN_DIR="/etc/NetworkManager/dnsmasq-shared.d"
DNSMASQ_DROPIN="${DNSMASQ_DROPIN_DIR}/captive-portal.conf"

mkdir -p "$DNSMASQ_DROPIN_DIR"

cat > "$DNSMASQ_DROPIN" << EOF
# Captive Portal - DNS hijacking
# Resolve ALL domain names to a fake public IP
# (Android ignores captive portal responses from private/local IPs)
address=/#/${FAKE_IP}
EOF

echo "  Created $DNSMASQ_DROPIN"

# --- 2. Configure nftables for port 80 -> 5000 redirect ---
echo "[2/4] Configuring nftables port redirect (80 -> ${FLASK_PORT})..."

NFTABLES_CONF="/etc/nftables-captive-portal.conf"

cat > "$NFTABLES_CONF" << EOF
#!/usr/sbin/nft -f
# Captive Portal nftables rules

# Remove old table if it exists (prevents duplicate rules)
table ip captive_portal
delete table ip captive_portal

table ip captive_portal {
    chain prerouting {
        type nat hook prerouting priority dstnat; policy accept;
        # Redirect traffic to fake public IP back to the Pi's Flask server
        iifname "${IFACE}" ip daddr ${FAKE_IP} tcp dport 80 dnat to ${PI_IP}:${FLASK_PORT}
        # Also redirect any other HTTP to Flask
        iifname "${IFACE}" tcp dport 80 redirect to :${FLASK_PORT}
        # Redirect all DNS to the Pi's dnsmasq
        iifname "${IFACE}" udp dport 53 redirect to :53
        iifname "${IFACE}" tcp dport 53 redirect to :53
    }

    chain filter_forward {
        type filter hook forward priority filter; policy accept;
        # Block HTTPS so devices can't reach the real internet check
        # This forces Android/iOS to detect "no internet" and show sign-in prompt
        iifname "${IFACE}" tcp dport 443 reject
        # Block DNS-over-TLS (Android Private DNS) to force plain DNS
        iifname "${IFACE}" tcp dport 853 reject
        # Block QUIC/HTTP3 (some browsers use this for DNS)
        iifname "${IFACE}" udp dport 443 reject
    }
}
EOF

echo "  Created $NFTABLES_CONF"

# Apply nftables rules now
nft -f "$NFTABLES_CONF"
echo "  Applied nftables rules"

# --- 3. Create systemd service to apply nftables rules on boot ---
echo "[3/4] Creating systemd service for persistent nftables rules..."

SERVICE_FILE="/etc/systemd/system/captive-portal.service"

cat > "$SERVICE_FILE" << EOF
[Unit]
Description=Captive Portal nftables rules
After=network-pre.target
Before=network.target

[Service]
Type=oneshot
ExecStart=/usr/sbin/nft -f ${NFTABLES_CONF}
ExecStop=/usr/sbin/nft delete table ip captive_portal
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable captive-portal.service
echo "  Created and enabled captive-portal.service"

# --- 4. Restart the AP connection to pick up DNS changes ---
echo "[4/4] Restarting AP connection to apply DNS hijacking..."

# Bring the AP connection down and up to reload dnsmasq with new config
if nmcli connection show --active | grep -q "${NM_CONNECTION}"; then
    nmcli connection down "${NM_CONNECTION}" 2>/dev/null || true
    sleep 1
fi
nmcli connection up "${NM_CONNECTION}" 2>/dev/null && \
    echo "  AP connection restarted with captive portal DNS" || \
    echo "  WARNING: Could not start AP connection '${NM_CONNECTION}'."
echo "  (If the AP is not running yet, the DNS hijacking will apply next time it starts.)"

echo ""
echo "=== Captive Portal Setup Complete ==="
echo ""
echo "How it works:"
echo "  1. NetworkManager's dnsmasq resolves ALL DNS queries to ${PI_IP}"
echo "  2. nftables redirects port 80 traffic to Flask on port ${FLASK_PORT}"
echo "  3. Flask responds to OS captive portal check URLs with a redirect"
echo "  4. The device shows a 'Sign in to network' popup with your upload UI"
echo ""
echo "To disable the captive portal:"
echo "  sudo systemctl stop captive-portal"
echo "  sudo nft delete table ip captive_portal"
echo "  sudo rm ${DNSMASQ_DROPIN}"
echo "  sudo nmcli connection down ${NM_CONNECTION} && sudo nmcli connection up ${NM_CONNECTION}"
