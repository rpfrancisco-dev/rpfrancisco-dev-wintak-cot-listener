"""Streaming client for the TAK Server WebSocket API (mutual TLS + protobuf)."""
from __future__ import annotations

import asyncio
import logging
import os
import socket
import ssl
import struct
import tempfile
from pathlib import Path
from urllib.parse import urlparse

import websockets
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
    pkcs12,
)
from django.conf import settings

from . import cot
from .registry import object_registry, registry

log = logging.getLogger("monitor.tak")


def build_ssl_context() -> ssl.SSLContext:
    """TLS context with the client identity from the configured PKCS#12."""
    p12_path = Path(settings.TAK_CLIENT_P12)
    password = settings.TAK_P12_PASSWORD.encode() or None
    key, cert, chain = pkcs12.load_key_and_certificates(
        p12_path.read_bytes(), password
    )

    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    if settings.TAK_VERIFY_SSL and settings.TAK_CA_FILE:
        ctx.load_verify_locations(settings.TAK_CA_FILE)
    else:
        # TAK servers commonly run self-signed certs; don't hard-fail on them.
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

    # load_cert_chain only takes files, so round-trip the p12 through a
    # temporary PEM that is deleted immediately after loading.
    fd, pem_path = tempfile.mkstemp(suffix=".pem")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(
                key.private_bytes(
                    Encoding.PEM, PrivateFormat.PKCS8, NoEncryption()
                )
            )
            f.write(cert.public_bytes(Encoding.PEM))
            for extra in chain or []:
                f.write(extra.public_bytes(Encoding.PEM))
        ctx.load_cert_chain(pem_path)
    finally:
        os.unlink(pem_path)
    return ctx


def _handle_frame(frame, transport: str | None = None, src_ip: str | None = None) -> None:
    result = cot.parse_frame(frame)
    if not result:
        return
    kind, payload = result
    if kind == "device":
        registry.upsert(payload, transport=transport, src_ip=src_ip)
    elif kind == "object":
        object_registry.upsert(payload, source=transport or "stream")
    elif kind == "delete":
        object_registry.remove(payload)


async def _stream_websocket(url: str, ssl_ctx, transport: str) -> None:
    """TAK Server WebSocket API (wss://host:8443/takproto/1)."""
    async with websockets.connect(
        url,
        ssl=ssl_ctx,
        open_timeout=15,
        ping_interval=30,
        ping_timeout=30,
        max_size=2**22,
    ) as ws:
        log.info("Connected to %s", url)
        registry.set_tak_state("connected")
        async for frame in ws:
            _handle_frame(frame, transport)


def split_cot_events(buffer: bytes):
    """Yield complete <event>…</event> chunks; return the leftover buffer.

    Raw TAK feeds (FreeTAKServer 8087/8089) are a byte stream of
    concatenated XML documents with no framing, so split on the close tag.
    """
    events = []
    while True:
        end = buffer.find(b"</event>")
        if end == -1:
            break
        start = buffer.find(b"<event")
        if start == -1 or start > end:
            buffer = buffer[end + 8:]
            continue
        events.append(buffer[start : end + 8])
        buffer = buffer[end + 8:]
    if len(buffer) > 2**20:  # garbage with no close tag — don't grow forever
        buffer = b""
    return events, buffer


async def _stream_raw(host: str, port: int, ssl_ctx, transport: str) -> None:
    """Raw CoT socket, XML framing (FreeTAKServer tcp 8087 / tls 8089)."""
    reader, writer = await asyncio.wait_for(
        asyncio.open_connection(host, port, ssl=ssl_ctx), timeout=15
    )
    log.info("Connected to %s:%s (raw CoT)", host, port)
    registry.set_tak_state("connected")
    buffer = b""
    try:
        while True:
            chunk = await reader.read(65536)
            if not chunk:
                raise ConnectionError("server closed the connection")
            buffer += chunk
            events, buffer = split_cot_events(buffer)
            for event in events:
                _handle_frame(event.decode("utf-8", errors="replace"), transport)
    finally:
        writer.close()


async def run_tak_stream() -> None:
    """Connect to the TAK server and feed CoT events into the registry.

    TAK_WS_URL scheme picks the transport:
      wss:// | ws://   TAK Server WebSocket API (protobuf frames)
      tls:// | ssl://  raw CoT over TLS (FreeTAKServer SSL port 8089)
      tcp://           raw CoT, no TLS (FreeTAKServer port 8087)
    Reconnects forever with capped exponential backoff.
    """
    url = urlparse(settings.TAK_WS_URL)
    scheme = url.scheme.lower()
    # How devices from this stream are labelled in the protocol column.
    transport = {"wss": "SSL", "tls": "SSL", "ssl": "SSL", "tcp": "TCP"}.get(
        scheme, "WS"
    )

    ssl_ctx = None
    if scheme in ("wss", "tls", "ssl"):
        try:
            ssl_ctx = build_ssl_context()
        except Exception as exc:
            log.exception(
                "Cannot load client certificate %s", settings.TAK_CLIENT_P12
            )
            registry.set_tak_state("error", f"certificate: {exc}")
            return

    backoff = 1
    while True:
        registry.set_tak_state("connecting")
        try:
            if scheme in ("ws", "wss"):
                await _stream_websocket(settings.TAK_WS_URL, ssl_ctx, transport)
            elif scheme in ("tcp", "tls", "ssl"):
                await _stream_raw(url.hostname, url.port or 8087, ssl_ctx, transport)
            else:
                registry.set_tak_state("error", f"unsupported scheme: {scheme}")
                return
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            log.warning("TAK stream dropped: %s", exc)
            if registry.tak_state == "connected":
                backoff = 1  # fresh drop after a good session, retry fast
            registry.set_tak_state("disconnected", str(exc))
        await asyncio.sleep(backoff)
        backoff = min(backoff * 2, 30)


# --- UDP listener ----------------------------------------------------------
def _is_multicast(host: str) -> bool:
    try:
        return 224 <= int(host.split(".")[0]) <= 239
    except (ValueError, IndexError, AttributeError):
        return False


def _handle_datagram(data: bytes, src_ip: str) -> None:
    """Parse one UDP datagram (XML or TAK protobuf) into the registries."""
    stripped = data.lstrip()
    if stripped[:1] == b"<":
        # A datagram may carry one or several concatenated <event>s.
        events, _ = split_cot_events(data)
        for event in events or [data]:
            _handle_frame(event.decode("utf-8", errors="replace"), transport="UDP", src_ip=src_ip)
    else:
        _handle_frame(bytes(data), transport="UDP", src_ip=src_ip)


def _bind_udp_socket(host: str, port: int) -> tuple[socket.socket, str]:
    """Bind a UDP socket per the host semantics; return (socket, description)."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    if _is_multicast(host):
        sock.bind(("", port))
        mreq = struct.pack(
            "4s4s", socket.inet_aton(host), socket.inet_aton("0.0.0.0")
        )
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
        return sock, f"multicast {host}:{port}"
    try:
        sock.bind((host, port))
        return sock, f"{host}:{port}"
    except OSError:
        # host isn't a local interface (e.g. it's the remote server IP) —
        # listen on every interface so datagrams to that port still arrive.
        sock.bind(("0.0.0.0", port))
        return sock, f"0.0.0.0:{port} (host {host} not local — all interfaces)"


async def run_udp_listener() -> None:
    """Receive CoT over UDP and feed it into the registry, alongside the stream."""
    if not settings.TAK_UDP_URL:
        return
    url = urlparse(settings.TAK_UDP_URL)
    host, port = url.hostname, url.port or 6969
    loop = asyncio.get_running_loop()

    while True:
        sock = None
        try:
            sock, desc = _bind_udp_socket(host, port)
            sock.setblocking(False)
            registry.set_udp_state("listening", None)
            log.info("UDP listener bound to %s", desc)
            while True:
                data, addr = await loop.sock_recvfrom(sock, 65535)
                if data:
                    _handle_datagram(data, addr[0])
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            log.warning("UDP listener error: %s", exc)
            registry.set_udp_state("error", str(exc))
        finally:
            if sock is not None:
                sock.close()
        await asyncio.sleep(5)
