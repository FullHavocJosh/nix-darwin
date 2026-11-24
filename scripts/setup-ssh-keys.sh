#!/usr/bin/env bash

# Script to configure SSH key authentication for all ssh* aliases
# This will copy your local public key to the authorized_keys on remote servers

# Don't exit on error - we want to continue with other hosts if one fails
set +e

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if public key exists
PUBLIC_KEY="$HOME/.ssh/id_ed25519.pub"
PRIVATE_KEY="$HOME/.ssh/id_ed25519"

if [[ ! -f "$PUBLIC_KEY" ]]; then
	echo -e "${RED}Error: Public key not found at $PUBLIC_KEY${NC}"
	exit 1
fi

echo -e "${GREEN}Using public key: $PUBLIC_KEY${NC}"
echo "Public key contents:"
cat "$PUBLIC_KEY"
echo ""

# Define SSH targets extracted from aliases
# Format: "user@host"
declare -A SSH_TARGETS=(
	["macbook"]="havoc@MacBookProM2Pro.rollet.family"
	["g14"]="havoc@Joshs-G14.rollet.family"
	["azeroth"]="root@azerothcore.rollet.family"
	["testazeroth"]="root@testing-azerothcore.rollet.family"
	["mini"]="havoc@macminim1.rollet.family"
	["truenas"]="admin@truenas.rollet.family"
	["6rx26x1"]="havoc@6rx26x1.rollet.family"
	["caitsg14"]="nesheri@Caits-G14.rollet.family"
	["xps13"]="havoc@xps13.rollet.family"
	["opnsense"]="root@192.168.144.1"
	["705g4"]="havoc@705g4.rollet.family"
	["4kfjsn2"]="havoc@4kfjsn2.rollet.family"
	["2fgjsn2"]="havoc@2fgjsn2.rollet.family"
	["k3sworkervm0"]="havoc@k3sworkervm0.rollet.family"
	["k3sworkervm1"]="havoc@k3sworkervm1.rollet.family"
	["ha"]="root@homeassistant.rollet.family"
	["steamdeck"]="deck@joshs-steamdeck.rollet.family"
	["novadeck"]="armada@novadeck.rollet.family"
	["trashcan"]="havoc@TrashCan.rollet.family"
)

echo -e "${YELLOW}This script will copy your SSH public key to the following servers:${NC}"
for name in "${!SSH_TARGETS[@]}"; do
	echo "  - $name: ${SSH_TARGETS[$name]}"
done
echo ""

read -p "Continue? (y/n) " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
	echo "Aborted."
	exit 0
fi

# Function to check if host is reachable
check_host_reachable() {
	local target=$1
	local hostname=$(echo "$target" | cut -d'@' -f2)

	# nc uses the system resolver (host and bash /dev/tcp fail on IPs and on
	# mDNS/Tailscale-resolved names); fall back to /dev/tcp only without nc
	if command -v nc &>/dev/null; then
		nc -z -w 3 "$hostname" 22 &>/dev/null
	else
		timeout 3 bash -c "cat < /dev/null > /dev/tcp/$hostname/22" 2>/dev/null
	fi
}

# Function to setup SSH key on a remote server
setup_ssh_key() {
	local name=$1
	local target=$2

	echo -e "\n${YELLOW}Setting up SSH key for $name ($target)...${NC}"

	# SSH options for better timeout handling
	local SSH_OPTS="-o ConnectTimeout=10 -o ConnectionAttempts=1 -o BatchMode=no"

	# Use ssh-copy-id which handles everything properly
	if command -v ssh-copy-id &>/dev/null; then
		# Capture output to determine if key was already installed
		local output
		output=$(ssh-copy-id -i "$PRIVATE_KEY" -o ConnectTimeout=10 -o ConnectionAttempts=1 "$target" 2>&1)
		local exit_code=$?

		if [[ $exit_code -eq 0 ]]; then
			if echo "$output" | grep -q "already installed"; then
				echo -e "${GREEN}✓ Key already configured for $name${NC}"
			else
				echo -e "${GREEN}✓ Successfully configured $name${NC}"
			fi
			return 0
		else
			# Check for specific error types
			if echo "$output" | grep -qi "connection.*refused\|connection.*timed out\|no route to host\|could not resolve hostname"; then
				echo -e "${YELLOW}⚠ Could not connect to $name - host may be offline${NC}"
				return 2
			elif echo "$output" | grep -qi "permission denied\|authentication failed"; then
				echo -e "${RED}✗ Authentication failed for $name - check credentials${NC}"
				return 1
			else
				echo -e "${RED}✗ Failed to configure $name${NC}"
				echo "$output" | tail -n 3
				return 1
			fi
		fi
	else
		# Fallback method if ssh-copy-id is not available
		echo -e "${YELLOW}ssh-copy-id not found, using manual method...${NC}"

		# Read the public key
		local pubkey=$(cat "$PUBLIC_KEY")

		# Create .ssh directory and add key to authorized_keys
		if ssh $SSH_OPTS -i "$PRIVATE_KEY" "$target" "mkdir -p ~/.ssh && chmod 700 ~/.ssh && echo '$pubkey' >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys && echo 'Key added successfully'" 2>&1; then
			echo -e "${GREEN}✓ Successfully configured $name${NC}"
			return 0
		else
			echo -e "${RED}✗ Failed to configure $name${NC}"
			return 1
		fi
	fi
}

# Probe all hosts up front so online hosts can be configured without
# waiting for offline hosts to time out
PROBE_DIR=$(mktemp -d)
trap 'rm -rf "$PROBE_DIR"' EXIT

for name in "${!SSH_TARGETS[@]}"; do
	(
		target=${SSH_TARGETS[$name]}
		if check_host_reachable "$target"; then
			echo online > "$PROBE_DIR/$name.tmp"
		else
			echo offline > "$PROBE_DIR/$name.tmp"
		fi
		mv "$PROBE_DIR/$name.tmp" "$PROBE_DIR/$name"
	) &
done
echo -e "${YELLOW}Probing ${#SSH_TARGETS[@]} hosts in background...${NC}"

# Track success/failure/skipped
SUCCESS_COUNT=0
FAILED_COUNT=0
SKIPPED_COUNT=0
declare -a FAILED_HOSTS
declare -a SKIPPED_HOSTS

# Configure hosts as their probes report, online first
PENDING=("${!SSH_TARGETS[@]}")
while [[ ${#PENDING[@]} -gt 0 ]]; do
	progressed=0
	STILL=()
	for name in "${PENDING[@]}"; do
		status=$(cat "$PROBE_DIR/$name" 2>/dev/null)
		if [[ $status == online ]]; then
			setup_ssh_key "$name" "${SSH_TARGETS[$name]}"
			result=$?

			if [[ $result -eq 0 ]]; then
				((SUCCESS_COUNT++))
			elif [[ $result -eq 2 ]]; then
				((SKIPPED_COUNT++))
				SKIPPED_HOSTS+=("$name")
			else
				((FAILED_COUNT++))
				FAILED_HOSTS+=("$name")
			fi
			progressed=1
		elif [[ $status == offline ]]; then
			((SKIPPED_COUNT++))
			SKIPPED_HOSTS+=("$name")
			echo -e "${YELLOW}⚠ $name appears to be offline or unreachable - skipping${NC}"
			progressed=1
		else
			STILL+=("$name")
		fi
	done
	if [[ ${#STILL[@]} -gt 0 ]]; then
		PENDING=("${STILL[@]}")
	else
		PENDING=()
	fi
	[[ $progressed -eq 0 ]] && sleep 0.2
done

# Summary
echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}Summary:${NC}"
echo -e "  ${GREEN}✓ Successful: $SUCCESS_COUNT${NC}"
echo -e "  ${YELLOW}⚠ Skipped (offline/unreachable): $SKIPPED_COUNT${NC}"
echo -e "  ${RED}✗ Failed: $FAILED_COUNT${NC}"

if [[ $SKIPPED_COUNT -gt 0 ]]; then
	echo -e "\n${YELLOW}Skipped hosts (offline or unreachable):${NC}"
	for host in "${SKIPPED_HOSTS[@]}"; do
		echo "  - $host"
	done
fi

if [[ $FAILED_COUNT -gt 0 ]]; then
	echo -e "\n${RED}Failed hosts (authentication or other errors):${NC}"
	for host in "${FAILED_HOSTS[@]}"; do
		echo "  - $host"
	done
fi

echo -e "${GREEN}========================================${NC}"
echo ""
echo "You can now test the connections with your aliases:"
echo "  sshmacbook, sshg14, sshazeroth, sshtestazeroth, sshmini, sshtruenas, ssh6rx26x1, sshcaitsg14, sshxps13, sshopnsense, ssh705g4, ssh4kfjsn2, ssh2fgjsn2, sshk3sworkervm0, sshk3sworkervm1, sshha, sshsteamdeck, sshnovadeck, sshtrash"
