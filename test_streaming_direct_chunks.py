#!/usr/bin/env python3
"""
Test that the SSE endpoint streams chunks directly (no buffering),
by asserting we receive multiple content events before end.

This test targets a running dev server and defaults to port 8002,
but can be overridden with TEST_API_BASE_URL.
"""
import os
import time
import json
import requests

BASE_URL = os.getenv("TEST_API_BASE_URL", "http://0.0.0.0:8002")
ENDPOINT = f"{BASE_URL}/chat/stream-sse"


def test_sse_stream_direct_chunks():
    # Construct a payload that encourages longer output
    payload = {
        "chatHistory": [],
        "message": (
            "Write a detailed, multi-paragraph explanation of what a 'double bubble bath' could be, "
            "including playful descriptions and at least 2 lists with 5 bullet points each."
        ),
        "userAttributes": {
            "userId": "test-user-stream",
            "operationIds": ["TEST_READ"],
            "userTenants": [
                {"tenantId": "tenant-abc", "tenantRole": "viewer"}
            ],
        },
    }

    headers = {
        "Accept": "text/event-stream",
        "Content-Type": "application/json",
        # Authorization optional for local dev; add if your server requires it
        # "Authorization": "Bearer <token>",
        "Cache-Control": "no-cache",
    }

    resp = requests.post(ENDPOINT, json=payload, headers=headers, stream=True, timeout=90)
    assert resp.status_code == 200, f"Unexpected status: {resp.status_code}, body={resp.text}"

    content_events = 0
    sources_seen = False
    end_seen = False

    first_chunk_time = None
    second_chunk_time = None

    # Iterate server-sent events
    for raw_line in resp.iter_lines(decode_unicode=True):
        if not raw_line:
            continue

        if raw_line.startswith("event:"):
            # Not strictly needed for assertions, but useful for debugging
            event_type = raw_line.split(":", 1)[1].strip()
            # print(f"event: {event_type}")
            continue

        if raw_line.startswith("data:"):
            data = raw_line.split(":", 1)[1].strip()
            try:
                obj = json.loads(data)
            except json.JSONDecodeError:
                # Non-JSON data line; skip
                continue

            t = obj.get("type")
            if t == "content":
                content_events += 1
                now = time.time()
                if first_chunk_time is None:
                    first_chunk_time = now
                elif second_chunk_time is None:
                    second_chunk_time = now
            elif t == "sources":
                sources_seen = True
            elif t == "end":
                end_seen = True
                break

    # Basic streaming assertions
    assert content_events >= 2, f"Expected >=2 content events, got {content_events}"
    assert end_seen, "Expected an end event to terminate the stream"

    # Optional responsiveness check: ensure second chunk arrived promptly (within 3s)
    if first_chunk_time and second_chunk_time:
        delta = second_chunk_time - first_chunk_time
        assert delta < 3.0, f"Second chunk arrived too slowly ({delta:.2f}s), streaming may be buffering"

    # Sources are expected at the end per implementation; validate presence
    assert sources_seen, "Expected a sources event before end"


if __name__ == "__main__":
    # Allow running directly for quick manual validation
    test_sse_stream_direct_chunks()
    print("OK: SSE direct chunk streaming test passed")