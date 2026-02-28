#!/usr/bin/env python3
"""WebSocket test client for pydantic-deepagents that auto-answers ask_user questions.

Run with: python -u test_pydantic_ws.py
"""
import asyncio
import json
import sys
import aiohttp


SERVER = "http://127.0.0.1:8080"
WS_URL = "ws://127.0.0.1:8080/ws/chat"
PROMPT = "What are the latest breakthroughs in AI agent frameworks for deep research in 2025?"
TIMEOUT = 300  # 5 minutes total timeout


def log(msg: str) -> None:
    """Print with immediate flush."""
    print(msg, flush=True)


async def main():
    # 1. Health check
    async with aiohttp.ClientSession() as http:
        resp = await http.get(f"{SERVER}/health")
        health = await resp.json()
        log(f"[Health] {health}")

    # 2. WebSocket session
    # Server expects client to send the first message.
    # If no session_id provided, server creates one and sends session_created.
    async with aiohttp.ClientSession() as session:
        async with session.ws_connect(WS_URL, timeout=aiohttp.ClientWSTimeout(ws_close=TIMEOUT)) as ws:
            # Send user message first (triggers session creation)
            await ws.send_json({"message": PROMPT})
            log(f"[Sent] {PROMPT}")

            done = False
            full_text: list[str] = []
            start = asyncio.get_event_loop().time()

            while not done:
                elapsed = asyncio.get_event_loop().time() - start
                if elapsed > TIMEOUT:
                    log(f"[TIMEOUT] after {elapsed:.0f}s")
                    break

                try:
                    raw = await asyncio.wait_for(ws.receive(), timeout=120)
                except asyncio.TimeoutError:
                    log("[TIMEOUT] no message for 120s")
                    break

                if raw.type == aiohttp.WSMsgType.TEXT:
                    data = json.loads(raw.data)
                    msg_type = data.get("type", "")

                    if msg_type == "session_created":
                        log(f"[Session] {data.get('session_id', '?')}")

                    elif msg_type == "canvas_ready":
                        log("[Canvas ready]")

                    elif msg_type == "ask_user_question":
                        qid = data.get("question_id", "")
                        question = data.get("question", "")
                        options = data.get("options", [])
                        log(f"[ASK_USER] {question}")
                        if options:
                            answer = options[0].get("label", options[0].get("value", "A comprehensive overview"))
                            log(f"  -> Options: {[o.get('label', o.get('value', '?')) for o in options]}")
                        else:
                            answer = "A comprehensive technical deep-dive covering all major frameworks"
                        log(f"  -> Auto-answer: {answer}")
                        await ws.send_json({
                            "question_answer": {
                                "question_id": qid,
                                "answer": answer,
                            }
                        })

                    elif msg_type == "approval":
                        approval_id = data.get("approval_id", "")
                        tool_name = data.get("tool_name", "")
                        log(f"[APPROVAL] {tool_name} (id: {approval_id})")
                        await ws.send_json({
                            "approval": {
                                "approval_id": approval_id,
                                "approved": True,
                            }
                        })

                    elif msg_type == "text_delta":
                        text = data.get("content", "")
                        full_text.append(text)
                        sys.stdout.write(text)
                        sys.stdout.flush()

                    elif msg_type == "status":
                        content = data.get("content", "")
                        log(f"\n[status] {content}")

                    elif msg_type == "tool_call":
                        tool_name = data.get("tool_name", "")
                        log(f"\n[Tool] {tool_name}")

                    elif msg_type == "tool_result":
                        result = data.get("result", "")
                        preview = str(result)[:200]
                        log(f"[ToolResult] {preview}...")

                    elif msg_type == "error":
                        error = data.get("content", data.get("message", str(data)))
                        log(f"\n[ERROR] {error}")

                    elif msg_type == "done":
                        log("\n[DONE]")
                        done = True

                    elif msg_type == "tool_args_delta":
                        pass  # Skip verbose streaming of tool args

                    else:
                        preview = str(data)[:300]
                        log(f"[{msg_type}] {preview}")

                elif raw.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
                    log("[WS] Connection closed/error")
                    break

            report = "".join(full_text)
            log(f"\n{'='*60}")
            log(f"=== REPORT ({len(report)} chars) ===")
            log(f"{'='*60}")
            if report:
                log(report[:5000])
            else:
                log("(no text received)")
            log(f"\n=== Total: {len(report)} chars ===")


if __name__ == "__main__":
    asyncio.run(main())
