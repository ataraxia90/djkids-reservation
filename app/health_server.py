from __future__ import annotations

import asyncio
import logging

logger = logging.getLogger(__name__)


async def start_health_server(port: int) -> asyncio.AbstractServer:
    server = await asyncio.start_server(_handle_health_request, host="0.0.0.0", port=port)
    logger.info("Health server started on port %s.", port)
    return server


async def _handle_health_request(
    reader: asyncio.StreamReader,
    writer: asyncio.StreamWriter,
) -> None:
    try:
        request_line = await reader.readline()
        path = _path_from_request_line(request_line)
        while True:
            line = await reader.readline()
            if line in {b"\r\n", b"\n", b""}:
                break

        if path in {"/", "/health"}:
            status = "200 OK"
            body = b"ok\n"
        else:
            status = "404 Not Found"
            body = b"not found\n"

        writer.write(
            b"HTTP/1.1 "
            + status.encode("ascii")
            + b"\r\n"
            + b"Content-Type: text/plain; charset=utf-8\r\n"
            + f"Content-Length: {len(body)}\r\n".encode("ascii")
            + b"Connection: close\r\n"
            + b"\r\n"
            + body
        )
        await writer.drain()
    finally:
        writer.close()
        await writer.wait_closed()


def _path_from_request_line(request_line: bytes) -> str:
    try:
        return request_line.decode("ascii").split(" ", maxsplit=2)[1]
    except (IndexError, UnicodeDecodeError):
        return ""
