#!/usr/bin/env python3
"""
Web Terminal Server for Claude Trader
FastAPI + WebSocket + Voice
"""
import sys
import json
import asyncio
from pathlib import Path
from datetime import datetime

# Add parent for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse

from interactive import process_command, current_event, current_markets
from polymarket_api import get_positions, get_balances, show_orders
from memory import get_memory, get_mindmap

app = FastAPI(title="Claude Trader")

# Memory instances
memory = get_memory()
mindmap = get_mindmap()

# Serve static files
STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Store for connected clients
clients: list[WebSocket] = []


class TerminalSession:
    """Manages a terminal session with command history"""

    def __init__(self, ws: WebSocket):
        self.ws = ws
        self.history: list[str] = []

    async def send(self, text: str, msg_type: str = "output"):
        """Send message to client"""
        await self.ws.send_json({"type": msg_type, "content": text})

    async def send_prompt(self):
        """Send command prompt"""
        await self.send("trade> ", "prompt")

    async def process(self, cmd: str):
        """Process a command and send output"""
        cmd = cmd.strip()
        if not cmd:
            return

        self.history.append(cmd)

        # Capture stdout for command output
        import io
        from contextlib import redirect_stdout

        # Special commands for web
        if cmd.lower() in ['help', '?']:
            await self.send(HELP_TEXT)
            return

        if cmd.lower() == 'status':
            await self.send_status()
            return

        if cmd.lower() == 'clear':
            await self.send("", "clear")
            return

        if cmd.lower() == 'memory':
            await self.send_memory_context()
            return

        if cmd.lower() == 'insights':
            await self.send_insights()
            return

        # Check memory for similar past queries
        similar = memory.find_similar_query(cmd)
        if similar:
            await self.send(f"[Memory: {similar['result'][:60]}...]", "info")

        # Execute trading command
        try:
            output = io.StringIO()
            with redirect_stdout(output):
                process_command(cmd)
            result = output.getvalue()
            if result:
                await self.send(result)

            # Record in memory
            memory.record_query(cmd, result[:100] if result else "executed")
            if 'buy' in cmd.lower() or 'sell' in cmd.lower():
                memory.record_trade({"command": cmd})

        except Exception as e:
            await self.send(f"Error: {e}", "error")

    async def send_memory_context(self):
        """Send memory context"""
        context = memory.get_session_context()
        if context:
            await self.send(context)
        else:
            await self.send("No memory context yet. Trade more to build knowledge.")

    async def send_insights(self):
        """Send trading insights from memory"""
        best = memory.get_best_practices()
        avoid = memory.get_patterns_to_avoid()

        lines = ["=== Trading Insights ===\n"]
        if best:
            lines.append("What works:")
            for p in best[:5]:
                lines.append(f"  + {p}")
        if avoid:
            lines.append("\nAvoid:")
            for p in avoid[:5]:
                lines.append(f"  - {p}")
        if not best and not avoid:
            lines.append("No insights yet. Trade more to build knowledge.")

        await self.send("\n".join(lines))

    async def send_status(self):
        """Send current trading status"""
        try:
            positions = get_positions() or []
            balances = get_balances() or {}

            status = [
                "=== Trading Status ===",
                f"Positions: {len(positions)}",
                f"USDC: ${balances.get('usdc', 0):.2f}",
                f"Event: {current_event or 'None loaded'}",
                f"Markets: {len(current_markets)}",
            ]
            await self.send("\n".join(status))
        except Exception as e:
            await self.send(f"Status error: {e}", "error")


HELP_TEXT = """
Voice Commands (hold mic button or press V):
  "buy 10 shares at 35 cents"
  "sell 5 at 60 cents"
  "show orders" / "pokaż zamówienia"
  "cancel all" / "anuluj wszystko"

Text Commands:
  <URL>              - Load Polymarket event
  buy <n> at <price> - Buy shares
  sell <n> at <price>- Sell shares
  orders             - Show open orders
  positions          - Show positions
  cancel all         - Cancel all orders
  status             - Trading status
  memory             - Show memory context
  insights           - Show trading insights
  clear              - Clear terminal
  help               - This help

Polish supported: kup, sprzedaj, pokaż, anuluj

Memory learns from your trades and improves over time.
"""


@app.get("/")
async def root():
    """Serve main terminal page"""
    return FileResponse(STATIC_DIR / "terminal.html")


@app.get("/api/status")
async def api_status():
    """API endpoint for trading status"""
    try:
        positions = get_positions() or []
        balances = get_balances() or {}
        return {
            "positions": len(positions),
            "usdc": balances.get("usdc", 0),
            "event": current_event,
            "markets": len(current_markets),
        }
    except Exception as e:
        return {"error": str(e)}


@app.get("/api/orders")
async def api_orders():
    """API endpoint for open orders"""
    try:
        # Capture show_orders output
        import io
        from contextlib import redirect_stdout
        output = io.StringIO()
        with redirect_stdout(output):
            show_orders()
        return {"orders": output.getvalue()}
    except Exception as e:
        return {"error": str(e)}


@app.get("/api/positions")
async def api_positions():
    """API endpoint for positions"""
    try:
        positions = get_positions() or []
        return {"positions": positions}
    except Exception as e:
        return {"error": str(e)}


@app.get("/api/memory")
async def api_memory():
    """API endpoint for trading memory"""
    return {
        "best_practices": memory.get_best_practices(),
        "avoid": memory.get_patterns_to_avoid(),
        "context": memory.get_session_context(),
    }


@app.get("/api/mindmap")
async def api_mindmap():
    """API endpoint for trading mindmap"""
    return {
        "strategies": mindmap.get_best_strategies(5),
        "context": mindmap.export_context(500),
    }


@app.post("/api/memory/insight")
async def api_add_insight(insight: str, confidence: float = 0.5):
    """Add a trading insight"""
    memory.remember_insight(insight, confidence)
    return {"status": "ok"}


@app.post("/api/memory/pattern")
async def api_add_pattern(pattern: str, success: bool):
    """Record a pattern result"""
    if success:
        memory.record_successful_pattern(pattern, {})
    else:
        memory.record_failed_pattern(pattern, "user marked as failed")
    return {"status": "ok"}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for terminal"""
    await websocket.accept()
    clients.append(websocket)
    session = TerminalSession(websocket)

    try:
        # Welcome message
        await session.send("=== Claude Trader Web Terminal ===")
        await session.send("Type 'help' for commands, speak or type to trade")
        await session.send("")
        await session.send_prompt()

        while True:
            data = await websocket.receive_json()

            if data.get("type") == "command":
                cmd = data.get("content", "")
                await session.send(f"trade> {cmd}\n", "echo")
                await session.process(cmd)
                await session.send_prompt()

            elif data.get("type") == "voice":
                # Voice transcript from Web Speech API
                transcript = data.get("content", "")
                await session.send(f"🎤 {transcript}\n", "voice")
                await session.process(transcript)
                await session.send_prompt()

    except WebSocketDisconnect:
        clients.remove(websocket)
    except Exception as e:
        await session.send(f"Connection error: {e}", "error")
        if websocket in clients:
            clients.remove(websocket)


def run():
    """Run the server"""
    import uvicorn
    print("Starting Claude Trader Web Terminal...")
    print("Open http://localhost:8000 in your browser")
    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    run()
