#!/usr/bin/env bash
set -uo pipefail

LOG_FILE="/data/net_traffic.log"
echo "$(date) [INFO] Enhanced Network Monitor Started" >> "$LOG_FILE"

# Store baseline state
ARP_HASH=""
ROUTE_HASH=""

while true; do
    # Basic network connection monitoring
    connections=$(netstat -tuln 2>/dev/null | grep -v "127.0.0.1" | wc -l)
    if [[ $connections -gt 10 ]]; then
        echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [WARN] High network activity: $connections connections" >> "$LOG_FILE"
    fi

    # Monitor DNS queries (if dig available)
    if ps aux | grep -v grep | grep -qE "dig|nslookup|host "; then
        dns_queries=$(ps aux | grep -v grep | grep -E "dig|nslookup|host " | awk '{for(i=11;i<=NF;i++) printf $i" "; print ""}')
        echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [INFO] DNS query: $dns_queries" >> "$LOG_FILE"
    fi

    # Monitor ARP cache changes
    current_arp=$(arp -n 2>/dev/null | md5sum | awk '{print $1}')
    if [[ -n "$ARP_HASH" && "$current_arp" != "$ARP_HASH" ]]; then
        echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [WARN] ARP cache changed" >> "$LOG_FILE"
        new_entries=$(arp -n 2>/dev/null | tail -5)
        echo "$new_entries" | while read -r line; do
            echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [INFO] ARP: $line" >> "$LOG_FILE"
        done
    fi
    ARP_HASH="$current_arp"

    # Monitor routing table changes
    current_route=$(ip route show 2>/dev/null | md5sum | awk '{print $1}')
    if [[ -n "$ROUTE_HASH" && "$current_route" != "$ROUTE_HASH" ]]; then
        echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [ALERT] Routing table modified!" >> "$LOG_FILE"
        ip route show 2>/dev/null | while read -r line; do
            echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [INFO] Route: $line" >> "$LOG_FILE"
        done
    fi
    ROUTE_HASH="$current_route"

    # Monitor NAT rules
    if command -v iptables >/dev/null 2>&1; then
        nat_rules=$(iptables -t nat -L -n 2>/dev/null | grep -v "^Chain\|^target" | wc -l)
        if [[ $nat_rules -gt 0 ]]; then
            if [[ ! -f /tmp/nat_rules_logged ]]; then
                echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [WARN] NAT rules active: $nat_rules" >> "$LOG_FILE"
                touch /tmp/nat_rules_logged
            fi
        fi
    fi

    # Monitor external IP detection (geo-location checks)
    if ps aux | grep -v grep | grep -qE "curl.*ip|wget.*ip|ipinfo|geoip"; then
        geo_check=$(ps aux | grep -v grep | grep -E "curl.*ip|wget.*ip|ipinfo|geoip" | awk '{for(i=11;i<=NF;i++) printf $i" "; print ""}')
        echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [INFO] Geo-location check: $geo_check" >> "$LOG_FILE"
    fi

    # Monitor /etc/resolv.conf changes (DNS)
    if [[ -f /etc/resolv.conf ]]; then
        resolv_mtime=$(stat -c %Y /etc/resolv.conf 2>/dev/null)
        if [[ -n "${RESOLV_MTIME:-}" && "$resolv_mtime" != "$RESOLV_MTIME" ]]; then
            echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [WARN] DNS configuration changed" >> "$LOG_FILE"
            nameservers=$(grep "^nameserver" /etc/resolv.conf 2>/dev/null)
            echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [INFO] Nameservers: $nameservers" >> "$LOG_FILE"
        fi
        RESOLV_MTIME="$resolv_mtime"
    fi

    # Monitor SSL/TLS certificate operations
    if ps aux | grep -v grep | grep -qE "openssl.*x509|openssl.*s_client"; then
        cert_ops=$(ps aux | grep -v grep | grep -E "openssl.*x509|openssl.*s_client" | awk '{for(i=11;i<=NF;i++) printf $i" "; print ""}')
        echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [INFO] Certificate operation: $cert_ops" >> "$LOG_FILE"
    fi

    # Monitor external connections by IP
    external_ips=$(netstat -tn 2>/dev/null | grep ESTABLISHED | awk '{print $5}' | cut -d: -f1 | grep -v "127.0.0.1\|^$" | sort -u)
    if [[ -n "$external_ips" ]]; then
        echo "$external_ips" | while read -r ip; do
            if [[ ! -f "/tmp/extip_${ip//[.:]/}" ]]; then
                echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [INFO] External connection to: $ip" >> "$LOG_FILE"
                touch "/tmp/extip_${ip//[.:]/}"
            fi
        done
    fi

    # Clean up old markers
    find /tmp -name "extip_*" -mmin +60 -delete 2>/dev/null

    sleep 4
done
