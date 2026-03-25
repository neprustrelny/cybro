"""
Passive packet capture module for CYBRO WatchDog v7.0.

This module uses scapy's AsyncSniffer to observe ARP, DHCP, DNS, and mDNS
traffic without transmitting any probes. Captured packets are normalized into
NetworkObservation objects and forwarded to the event engine.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from queue import Queue
from typing import Any, Dict, Optional
import logging

try:
    from scapy.all import (
        AsyncSniffer,
        ARP,
        BOOTP,
        DHCP,
        DNS,
        DNSQR,
        DNSRR,
        Ether,
        IP,
    )
except Exception as exc:  # pragma: no cover - scapy missing at runtime
    AsyncSniffer = None
    SCAPY_IMPORT_ERROR = exc
else:
    SCAPY_IMPORT_ERROR = None


DHCP_MESSAGE_TYPES = {
    1: "DISCOVER",
    2: "OFFER",
    3: "REQUEST",
    4: "DECLINE",
    5: "ACK",
    6: "NAK",
    7: "RELEASE",
    8: "INFORM",
}


@dataclass(slots=True)
class NetworkObservation:
    """Normalized passive packet metadata."""

    mac: str
    protocol: str
    timestamp: datetime
    ip: Optional[str] = None
    hostname: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class PassiveCapture:
    """Continuous passive capture loop driven by AsyncSniffer."""

    BPF_FILTER = "arp or (udp and (port 67 or port 68)) or (udp and port 53)"

    def __init__(
        self,
        interface: Optional[str] = None,
        observation_queue: Optional[Queue] = None,
        logger: Optional[logging.Logger] = None,
    ):
        if AsyncSniffer is None:
            raise RuntimeError(
                "scapy is required for passive capture. Import error: "
                f"{SCAPY_IMPORT_ERROR}"
            )

        self.interface = interface
        self.observation_queue = observation_queue or Queue()
        self.logger = logger or logging.getLogger("cybro.passive_capture")
        self._sniffer: Optional[AsyncSniffer] = None

    def start(self) -> None:
        if self._sniffer and self._sniffer.running:
            return
        self.logger.info(
            "Starting passive capture on %s (promiscuous mode)",
            self.interface or "default interface",
        )
        self._sniffer = AsyncSniffer(
            iface=self.interface,
            prn=self._handle_packet,
            store=False,
            promisc=True,
            filter=self.BPF_FILTER,
        )
        self._sniffer.start()

    def stop(self) -> None:
        if not self._sniffer:
            return
        self.logger.info("Stopping passive capture loop")
        self._sniffer.stop()
        self._sniffer = None

    def _emit(self, observation: NetworkObservation) -> None:
        self.observation_queue.put(observation)

    def _handle_packet(self, packet: Any) -> None:
        try:
            if packet.haslayer(ARP):
                self._process_arp(packet)
            elif packet.haslayer(DHCP):
                self._process_dhcp(packet)
            elif packet.haslayer(DNS):
                self._process_dns(packet)
        except Exception as exc:  # pragma: no cover - defensive
            self.logger.debug("Failed to process packet: %s", exc, exc_info=True)

    def _process_arp(self, packet: Any) -> None:
        arp_layer = packet[ARP]
        mac = getattr(arp_layer, "hwsrc", None)
        ip = getattr(arp_layer, "psrc", None)
        if not mac:
            return

        operation = "REQUEST" if arp_layer.op == 1 else "REPLY"
        observation = NetworkObservation(
            mac=mac,
            ip=ip,
            protocol="ARP",
            hostname=None,
            timestamp=datetime.now(timezone.utc),
            metadata={
                "dst_ip": getattr(arp_layer, "pdst", None),
                "operation": operation,
            },
        )
        self._emit(observation)

    def _process_dhcp(self, packet: Any) -> None:
        ether = packet[Ether] if packet.haslayer(Ether) else None
        bootp = packet[BOOTP] if packet.haslayer(BOOTP) else None
        mac = getattr(ether, "src", None)
        timestamp = datetime.now(timezone.utc)

        options: Dict[str, Any] = {}
        for option in packet[DHCP].options:
            if isinstance(option, tuple) and len(option) == 2:
                key, value = option
                options[key] = self._decode_option(value)

        hostname = options.get("hostname")
        requested_ip = options.get("requested_addr")
        lease_ip = getattr(bootp, "yiaddr", None) if bootp else None
        current_ip = getattr(bootp, "ciaddr", None) if bootp else None
        ip = requested_ip or lease_ip or current_ip

        message_type_value = options.get("message-type")
        if isinstance(message_type_value, str):
            message_type = message_type_value.upper()
        elif isinstance(message_type_value, (bytes, bytearray)) and message_type_value:
            message_type = DHCP_MESSAGE_TYPES.get(message_type_value[0], "UNKNOWN")
        elif isinstance(message_type_value, int):
            message_type = DHCP_MESSAGE_TYPES.get(message_type_value, "UNKNOWN")
        else:
            message_type = "UNKNOWN"

        observation = NetworkObservation(
            mac=mac or getattr(bootp, "chaddr", None),
            ip=ip,
            protocol="DHCP",
            hostname=hostname,
            timestamp=timestamp,
            metadata={
                "dhcp_message_type": message_type,
                "requested_ip": requested_ip,
                "lease_ip": lease_ip,
                "transaction_id": getattr(bootp, "xid", None),
            },
        )
        if observation.mac:
            self._emit(observation)

    def _process_dns(self, packet: Any) -> None:
        if not packet.haslayer(Ether):
            return

        mac = packet[Ether].src
        ip = packet[IP].src if packet.haslayer(IP) else None
        dns_layer = packet[DNS]
        queries = self._extract_dns_queries(dns_layer)
        answers = self._extract_dns_answers(dns_layer)
        hostname = queries[0] if queries else None

        observation = NetworkObservation(
            mac=mac,
            ip=ip,
            protocol="mDNS" if self._is_mdns(packet) else "DNS",
            hostname=hostname,
            timestamp=datetime.now(timezone.utc),
            metadata={
                "queries": queries,
                "answers": answers,
                "transaction_id": dns_layer.id,
            },
        )
        self._emit(observation)

    @staticmethod
    def _decode_option(value: Any) -> Any:
        if isinstance(value, bytes):
            try:
                return value.decode("utf-8", errors="ignore").strip("\x00")
            except Exception:  # pragma: no cover - defensive
                return value.hex()
        return value

    @staticmethod
    def _extract_dns_queries(dns_layer: Any) -> list[str]:
        queries: list[str] = []
        qcount = int(getattr(dns_layer, "qdcount", 0))
        for index in range(qcount):
            try:
                query = dns_layer.qd[index] if qcount > 1 else dns_layer.qd
            except Exception:
                query = dns_layer.qd
            if isinstance(query, DNSQR):
                name = PassiveCapture._decode_dns_name(query.qname)
                if name:
                    queries.append(name)
        return queries

    @staticmethod
    def _extract_dns_answers(dns_layer: Any) -> list[str]:
        answers: list[str] = []
        for index in range(int(getattr(dns_layer, "ancount", 0))):
            try:
                answer = dns_layer.an[index] if dns_layer.ancount > 1 else dns_layer.an
            except Exception:
                answer = dns_layer.an
            if isinstance(answer, DNSRR):
                name = PassiveCapture._decode_dns_name(answer.rrname)
                rdata = getattr(answer, "rdata", None)
                answers.append(f"{name}->{rdata}")
        return answers

    @staticmethod
    def _decode_dns_name(value: Any) -> Optional[str]:
        if isinstance(value, bytes):
            try:
                return value.decode("utf-8", errors="ignore").rstrip(".")
            except Exception:  # pragma: no cover
                return None
        return value

    @staticmethod
    def _is_mdns(packet: Any) -> bool:
        if packet.haslayer(IP):
            return packet[IP].dst == "224.0.0.251"
        return False

