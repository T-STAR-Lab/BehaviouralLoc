#!/usr/bin/env bash
set -uo pipefail

LOG_FILE="/data/db_monitor.log"
echo "$(date) [INFO] Database Monitor Started" >> "$LOG_FILE"

while true; do
    # Monitor MySQL/MariaDB connections
    mysql_port=3306
    if ss -tuln | grep -q ":$mysql_port "; then
        mysql_conns=$(ss -tn state established "( dport = :$mysql_port or sport = :$mysql_port )" 2>/dev/null | tail -n +2 | wc -l)
        if [[ $mysql_conns -gt 0 && ! -f /tmp/mysql_conn_logged ]]; then
            echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [INFO] MySQL connections active: $mysql_conns" >> "$LOG_FILE"
            touch /tmp/mysql_conn_logged
        elif [[ $mysql_conns -eq 0 ]]; then
            rm -f /tmp/mysql_conn_logged 2>/dev/null
        fi
    fi

    # Monitor PostgreSQL connections
    pgsql_port=5432
    if ss -tuln | grep -q ":$pgsql_port "; then
        pgsql_conns=$(ss -tn state established "( dport = :$pgsql_port or sport = :$pgsql_port )" 2>/dev/null | tail -n +2 | wc -l)
        if [[ $pgsql_conns -gt 0 && ! -f /tmp/pgsql_conn_logged ]]; then
            echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [INFO] PostgreSQL connections active: $pgsql_conns" >> "$LOG_FILE"
            touch /tmp/pgsql_conn_logged
        elif [[ $pgsql_conns -eq 0 ]]; then
            rm -f /tmp/pgsql_conn_logged 2>/dev/null
        fi
    fi

    # Monitor MongoDB connections
    mongo_port=27017
    if ss -tuln | grep -q ":$mongo_port "; then
        mongo_conns=$(ss -tn state established "( dport = :$mongo_port or sport = :$mongo_port )" 2>/dev/null | tail -n +2 | wc -l)
        if [[ $mongo_conns -gt 0 && ! -f /tmp/mongo_conn_logged ]]; then
            echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [INFO] MongoDB connections active: $mongo_conns" >> "$LOG_FILE"
            touch /tmp/mongo_conn_logged
        elif [[ $mongo_conns -eq 0 ]]; then
            rm -f /tmp/mongo_conn_logged 2>/dev/null
        fi
    fi

    # Monitor Redis connections
    redis_port=6379
    if ss -tuln | grep -q ":$redis_port "; then
        redis_conns=$(ss -tn state established "( dport = :$redis_port or sport = :$redis_port )" 2>/dev/null | tail -n +2 | wc -l)
        if [[ $redis_conns -gt 0 && ! -f /tmp/redis_conn_logged ]]; then
            echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [INFO] Redis connections active: $redis_conns" >> "$LOG_FILE"
            touch /tmp/redis_conn_logged
        elif [[ $redis_conns -eq 0 ]]; then
            rm -f /tmp/redis_conn_logged 2>/dev/null
        fi
    fi

    # Monitor database client processes
    if ps aux | grep -v grep | grep -qE "mysql|psql|mongo|redis-cli|sqlite3"; then
        db_clients=$(ps aux | grep -v grep | grep -E "mysql|psql|mongo|redis-cli|sqlite3" | awk '{print $2, $11}')
        echo "$db_clients" | while read -r pid cmd; do
            if [[ ! -f "/tmp/dbclient_${pid}" ]]; then
                echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [WARN] Database client: $cmd (PID:$pid)" >> "$LOG_FILE"
                touch "/tmp/dbclient_${pid}"
            fi
        done
    fi

    # Monitor database dump commands
    if ps aux | grep -v grep | grep -qE "mysqldump|pg_dump|mongodump"; then
        dump_cmds=$(ps aux | grep -v grep | grep -E "mysqldump|pg_dump|mongodump" | awk '{for(i=11;i<=NF;i++) printf $i" "; print ""}')
        echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [ALERT] Database dump command: $dump_cmds" >> "$LOG_FILE"
    fi

    # Monitor database server processes
    db_servers="mysqld|postgres|mongod|redis-server"
    if ps aux | grep -v grep | grep -qE "$db_servers"; then
        servers=$(ps aux | grep -v grep | grep -E "$db_servers" | awk '{print $11}' | sort -u)
        echo "$servers" | while read -r server; do
            if [[ ! -f "/tmp/dbserver_$(basename "$server")" ]]; then
                echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [INFO] Database server running: $server" >> "$LOG_FILE"
                touch "/tmp/dbserver_$(basename "$server")"
            fi
        done
    fi

    # Monitor SQL injection attempts in process arguments
    for pid_dir in /proc/[0-9]*/cmdline; do
        if [[ -f "$pid_dir" ]]; then
            cmdline=$(cat "$pid_dir" 2>/dev/null | tr '\0' ' ')
            if echo "$cmdline" | grep -qiE "select.*from|union.*select|drop.*table|insert.*into.*values"; then
                pid=$(echo "$pid_dir" | grep -oP '\d+')
                if [[ ! -f "/tmp/sqlinj_${pid}" ]]; then
                    echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [CRITICAL] Possible SQL injection pattern: PID=$pid CMD=$cmdline" >> "$LOG_FILE"
                    touch "/tmp/sqlinj_${pid}"
                fi
            fi
        fi
    done 2>/dev/null

    # Clean up old markers
    find /tmp -name "dbclient_*" -mmin +5 -delete 2>/dev/null
    find /tmp -name "dbserver_*" -mmin +60 -delete 2>/dev/null
    find /tmp -name "sqlinj_*" -mmin +5 -delete 2>/dev/null
    find /tmp -name "*_conn_logged" -mmin +10 -delete 2>/dev/null

    sleep 5
done
