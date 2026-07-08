#!/bin/bash
# Auto-revert netplan to the snapshot taken before a web-initiated change.
# Fires via a transient systemd timer unless cancelled by "Keep".
if [ -d /run/netplan.rollback ]; then
    rm -f /etc/netplan/*.yaml
    cp -a /run/netplan.rollback/. /etc/netplan/ 2>/dev/null
    chmod 600 /etc/netplan/*.yaml 2>/dev/null
    netplan apply
    logger -t net-rollback "network config auto-reverted to pre-change snapshot"
    rm -rf /run/netplan.rollback
fi
