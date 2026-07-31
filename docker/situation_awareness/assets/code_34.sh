#!/usr/bin/env bash
set -uo pipefail

LOG_FILE="/data/print_monitor.log"
echo "$(date) [INFO] Print/Scan Monitor Started" >> "$LOG_FILE"

while true; do
    # Monitor CUPS (Common Unix Printing System)
    if command -v lpstat >/dev/null 2>&1; then
        # Check for active print jobs
        print_jobs=$(lpstat -o 2>/dev/null | wc -l)
        if [[ $print_jobs -gt 0 ]]; then
            jobs=$(lpstat -o 2>/dev/null)
            echo "$jobs" | while read -r job; do
                if [[ ! -f /tmp/print_job_logged ]]; then
                    echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [ALERT] Print job: $job" >> "$LOG_FILE"
                fi
            done
            touch /tmp/print_job_logged
        else
            rm -f /tmp/print_job_logged 2>/dev/null
        fi

        # Check for available printers
        printers=$(lpstat -p 2>/dev/null | grep "printer" | wc -l)
        if [[ $printers -gt 0 && ! -f /tmp/printers_logged ]]; then
            printer_list=$(lpstat -p 2>/dev/null)
            echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [INFO] Printers available: $printers" >> "$LOG_FILE"
            echo "$printer_list" | while read -r line; do
                echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [INFO] $line" >> "$LOG_FILE"
            done
            touch /tmp/printers_logged
        fi
    fi

    # Monitor lp/lpr commands (print commands)
    if ps aux | grep -v grep | grep -qE " lp | lpr "; then
        print_cmds=$(ps aux | grep -v grep | grep -E " lp | lpr " | awk '{for(i=11;i<=NF;i++) printf $i" "; print ""}')
        echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [ALERT] Print command executed: $print_cmds" >> "$LOG_FILE"
    fi

    # Monitor CUPS logs if accessible
    if [[ -r /var/log/cups/access_log ]]; then
        recent_prints=$(tail -5 /var/log/cups/access_log 2>/dev/null | grep -i "POST")
        if [[ -n "$recent_prints" ]]; then
            echo "$recent_prints" | while read -r line; do
                if [[ ! -f /tmp/cups_access_logged ]]; then
                    echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [INFO] CUPS access: $line" >> "$LOG_FILE"
                fi
            done
            touch /tmp/cups_access_logged
            sleep 1
            rm -f /tmp/cups_access_logged
        fi
    fi

    # Monitor scanner access (SANE)
    if ps aux | grep -v grep | grep -qE "scanimage|simple-scan|xsane"; then
        scan_procs=$(ps aux | grep -v grep | grep -E "scanimage|simple-scan|xsane" | awk '{print $2, $11}')
        echo "$scan_procs" | while read -r pid cmd; do
            if [[ ! -f "/tmp/scanner_${pid}" ]]; then
                echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [ALERT] Scanner access: $cmd (PID:$pid)" >> "$LOG_FILE"
                touch "/tmp/scanner_${pid}"
            fi
        done
    fi

    # Monitor scanner device access
    for scanner_dev in /dev/bus/usb/*/*; do
        if [[ -e "$scanner_dev" ]]; then
            if lsof "$scanner_dev" 2>/dev/null | grep -q "usb"; then
                accessor=$(lsof "$scanner_dev" 2>/dev/null | tail -n +2 | awk '{print $1, $2}' | head -1)
                if [[ -n "$accessor" ]]; then
                    proc=$(echo "$accessor" | awk '{print $1}')
                    pid=$(echo "$accessor" | awk '{print $2}')
                    # Check if it's a scanner process
                    if echo "$proc" | grep -qE "scan|sane"; then
                        if [[ ! -f "/tmp/scandev_${pid}" ]]; then
                            echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [WARN] Scanner device access: $scanner_dev by $proc (PID:$pid)" >> "$LOG_FILE"
                            touch "/tmp/scandev_${pid}"
                        fi
                    fi
                fi
            fi
        fi
    done 2>/dev/null

    # Monitor print spooler directory
    if [[ -d /var/spool/cups ]]; then
        spool_files=$(find /var/spool/cups -type f -mmin -1 2>/dev/null | wc -l)
        if [[ $spool_files -gt 0 ]]; then
            echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [INFO] Active print spool files: $spool_files" >> "$LOG_FILE"
        fi
    fi

    # Clean up old markers
    find /tmp -name "scanner_*" -mmin +5 -delete 2>/dev/null
    find /tmp -name "scandev_*" -mmin +5 -delete 2>/dev/null
    find /tmp -name "printers_logged" -mmin +60 -delete 2>/dev/null

    sleep 5
done
