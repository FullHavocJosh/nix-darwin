#!/bin/bash
# Fix routing after plugging in the OPNsense LAN cable.
# Ensures internet traffic goes via WiFi/hotspot and only
# 192.168.144.0/24 traffic routes through the wired LAN.
#
# Key fix: switches the LAN interface from DHCP to MANUAL mode
# so macOS never re-adds a default route via OPNsense on DHCP renewal.
#
# To restore normal operation (OPNsense as default gateway), run:
#   sudo ipconfig set <lan_if> DHCP

set -euo pipefail

LAN_SUBNET="192.168.144.0/24"
LAN_GATEWAY="192.168.144.1"

# Find the LAN interface (has a 192.168.144.x IP)
LAN_IF=$(ifconfig -a | awk '/^en/{iface=$1} /inet 192\.168\.144\./{print iface}' | tr -d ':' | head -1)

if [[ -z "$LAN_IF" ]]; then
    echo "ERROR: No interface with 192.168.144.x IP found. Is the LAN cable plugged in?"
    exit 1
fi

# Get the DHCP-assigned IP and mask from the LAN interface
LAN_IP=$(ifconfig "$LAN_IF" | awk '/inet 192\.168\.144\./{print $2}')
LAN_MASK=$(ifconfig "$LAN_IF" | awk '/inet 192\.168\.144\./{print $4}')

echo "LAN interface: $LAN_IF  IP: $LAN_IP  Mask: $LAN_MASK"

# Find the WAN interface and gateway (any default route not on the LAN interface)
WAN_INFO=$(netstat -rn | awk '/^default/ && !/fe80/ && $NF != "'"$LAN_IF"'" {print $2, $NF; exit}')
WAN_GW=$(echo "$WAN_INFO" | awk '{print $1}')
WAN_IF=$(echo "$WAN_INFO" | awk '{print $2}')

# If WAN default is only available as ifscope, find it there
if [[ -z "$WAN_GW" ]]; then
    WAN_INFO=$(netstat -rn | awk '/^default/ && !/fe80/ {print $2, $NF; exit}')
    WAN_GW=$(echo "$WAN_INFO" | awk '{print $1}')
    WAN_IF=$(echo "$WAN_INFO" | awk '{print $2}')
fi

if [[ -z "$WAN_GW" ]]; then
    echo "ERROR: Could not find a WAN (non-LAN) default route. Is the hotspot connected?"
    exit 1
fi

echo "WAN interface: $WAN_IF  Gateway: $WAN_GW"
echo ""

# 1. Remove all default routes via the LAN interface/gateway
echo "Removing OPNsense default routes..."
sudo route delete default "$LAN_GATEWAY" 2>/dev/null && echo "  Deleted default via $LAN_GATEWAY" || true
sudo route delete default -ifscope "$LAN_IF" 2>/dev/null && echo "  Deleted ifscope default on $LAN_IF" || true

# 2. Switch LAN interface to MANUAL mode — prevents macOS from ever re-adding
#    a default route via OPNsense on DHCP renewal
echo "Switching $LAN_IF to manual IP (no gateway)..."
sudo ipconfig set "$LAN_IF" MANUAL "$LAN_IP" 255.255.255.0
sleep 1

# 3. Ensure the LAN subnet route exists (ipconfig MANUAL should add it, but be safe)
if ! netstat -rn | grep -q "192\.168\.144"; then
    echo "Adding LAN subnet route..."
    sudo route add -net "$LAN_SUBNET" -interface "$LAN_IF" 2>/dev/null || true
fi

# 4. Promote WAN default route to primary if it's still ifscope (has 'I' flag)
if netstat -rn | grep "^default" | grep "$WAN_IF" | grep -q "I"; then
    echo "Promoting WAN default route to primary..."
    sudo route delete default "$WAN_GW" 2>/dev/null || true
    sudo route add default "$WAN_GW"
fi

# Verify
echo ""
echo "Routing table (default routes):"
netstat -rn | grep "^default" | grep -v fe80

echo ""
echo "Testing internet connectivity..."
if curl -s --max-time 5 https://1.1.1.1 > /dev/null; then
    echo "  Internet OK via $WAN_IF ($WAN_GW)"
else
    echo "  WARNING: Internet not reachable — check WAN connection."
fi

echo ""
echo "Testing OPNsense reachability..."
if ping -c1 -t2 "$LAN_GATEWAY" > /dev/null 2>&1; then
    echo "  OPNsense OK ($LAN_GATEWAY via $LAN_IF)"
else
    echo "  WARNING: OPNsense ($LAN_GATEWAY) not reachable."
fi

echo ""
echo "Done. To restore OPNsense as default gateway: sudo ipconfig set $LAN_IF DHCP"
