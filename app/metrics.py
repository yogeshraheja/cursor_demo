import socket
import time
from datetime import datetime, timezone

import psutil
from flask import current_app


def read_metrics():
    previous = current_app.extensions.get("net_previous")
    payload, snapshot = collect_metrics(previous)
    current_app.extensions["net_previous"] = snapshot
    return payload


def clear_rate_snapshot():
    current_app.extensions.pop("net_previous", None)


def collect_metrics(previous):
    now = time.monotonic()
    load_1, load_5, load_15 = psutil.getloadavg()
    memory = psutil.virtual_memory()
    swap = psutil.swap_memory()
    addresses = psutil.net_if_addrs()
    counters = psutil.net_io_counters(pernic=True)
    previous_counters = previous["counters"] if previous else {}
    elapsed = (now - previous["time"]) if previous else 0

    network = []
    stored = {}
    for name in sorted(counters):
        if _is_loopback(name, addresses.get(name, ())):
            continue
        stats = counters[name]
        received = int(stats.bytes_recv)
        sent = int(stats.bytes_sent)
        stored[name] = (received, sent)
        recv_rate = None
        sent_rate = None
        if name in previous_counters and elapsed > 0:
            old_received, old_sent = previous_counters[name]
            recv_rate = (received - old_received) / elapsed
            sent_rate = (sent - old_sent) / elapsed
        network.append(
            {
                "name": name,
                "bytes_recv": received,
                "bytes_sent": sent,
                "recv_rate": recv_rate,
                "sent_rate": sent_rate,
            }
        )

    return {
        "read_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "cpu": {
            "busy_percent": psutil.cpu_percent(interval=None),
            "load_average": [load_1, load_5, load_15],
        },
        "memory": {
            "total": int(memory.total),
            "used": int(memory.used),
            "available": int(memory.available),
            "used_percent": memory.percent,
            "swap_total": int(swap.total),
            "swap_used": int(swap.used),
        },
        "network": network,
        "ports": _listening_ports(),
    }, {"time": now, "counters": stored}


def _is_loopback(name, addresses):
    if name == "lo" or name.startswith("lo"):
        return True
    ips = []
    for address in addresses:
        if address.family in (socket.AF_INET, socket.AF_INET6):
            ips.append(address.address.split("%", 1)[0])
    if not ips:
        return False
    return all(ip.startswith("127.") or ip == "::1" for ip in ips)


def _listening_ports():
    try:
        connections = psutil.net_connections(kind="inet")
    except psutil.Error:
        return []

    ports = []
    for conn in connections:
        protocol = _listen_protocol(conn)
        if protocol is None or not conn.laddr:
            continue
        ports.append(
            {
                "port": int(conn.laddr.port),
                "protocol": protocol,
                "address": conn.laddr.ip,
                "process": _process_name(conn.pid),
                "pid": conn.pid,
            }
        )
    ports.sort(key=lambda item: (item["protocol"], item["port"], item["address"]))
    return ports


def _listen_protocol(conn):
    if conn.status == psutil.CONN_LISTEN:
        return "TCP"
    if conn.type == socket.SOCK_DGRAM and conn.laddr and not conn.raddr:
        return "UDP"
    return None


def _process_name(pid):
    if not pid:
        return ""
    try:
        return psutil.Process(pid).name()
    except psutil.Error:
        return ""
