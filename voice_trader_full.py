#!/usr/bin/env python3
"""
Claude Voice Trader - Complete System
Voice → Transcribe → Claude AI → Research → Trade

One integrated system with all features.
"""
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from anthropic import Anthropic

# Voice
from voice.recorder import record_push_to_talk
from voice.transcribe import transcribe

# Trading - ALL features
from polymarket_api import (
    show_event, place_order, place_ladder, quick_buy, quick_sell,
    get_best_prices, show_orders, cancel_order, cancel_all_orders,
    get_positions, get_balances, get_orderbook, search_markets
)
from auto import whale_follow, top_volume_bet, fetch_recent_trades
from memory import get_memory, get_mindmap

# Initialize
client = Anthropic()
memory = get_memory()
mindmap = get_mindmap()
conversation_history = []

TOOLS = [
    {
        "name": "search_markets",
        "description": "Search Polymarket for markets matching a query",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query (e.g. 'Trump', 'Bitcoin', 'election')"}
            },
            "required": ["query"]
        }
    },
    {
        "name": "show_event",
        "description": "Load and display a Polymarket event by slug",
        "input_schema": {
            "type": "object",
            "properties": {
                "slug": {"type": "string", "description": "Event slug from URL (e.g. 'trump-election-2024')"}
            },
            "required": ["slug"]
        }
    },
    {
        "name": "get_whale_trades",
        "description": "Get recent large trades (whale trades) above a USD threshold",
        "input_schema": {
            "type": "object",
            "properties": {
                "min_usd": {"type": "number", "description": "Minimum trade size in USD", "default": 5000}
            }
        }
    },
    {
        "name": "place_order",
        "description": "Place a limit order. Price is decimal (0.35 = 35 cents)",
        "input_schema": {
            "type": "object",
            "properties": {
                "market_id": {"type": "string", "description": "Market ID"},
                "side": {"type": "string", "enum": ["BUY", "SELL"]},
                "price": {"type": "number", "description": "Price as decimal (0.35 = 35 cents)"},
                "size": {"type": "number", "description": "Number of shares"}
            },
            "required": ["market_id", "side", "price", "size"]
        }
    },
    {
        "name": "quick_buy",
        "description": "Buy at current best ask price",
        "input_schema": {
            "type": "object",
            "properties": {
                "market_id": {"type": "string"},
                "size": {"type": "number", "description": "Number of shares"}
            },
            "required": ["market_id", "size"]
        }
    },
    {
        "name": "quick_sell",
        "description": "Sell at current best bid price",
        "input_schema": {
            "type": "object",
            "properties": {
                "market_id": {"type": "string"},
                "size": {"type": "number", "description": "Number of shares"}
            },
            "required": ["market_id", "size"]
        }
    },
    {
        "name": "place_ladder",
        "description": "Place multiple orders as a ladder",
        "input_schema": {
            "type": "object",
            "properties": {
                "market_id": {"type": "string"},
                "side": {"type": "string", "enum": ["BUY", "SELL"]},
                "start_price": {"type": "number"},
                "end_price": {"type": "number"},
                "num_orders": {"type": "integer"},
                "size_per_order": {"type": "number"}
            },
            "required": ["market_id", "side", "start_price", "end_price", "num_orders", "size_per_order"]
        }
    },
    {
        "name": "show_orders",
        "description": "Show all open orders",
        "input_schema": {"type": "object", "properties": {}}
    },
    {
        "name": "cancel_all_orders",
        "description": "Cancel all open orders",
        "input_schema": {"type": "object", "properties": {}}
    },
    {
        "name": "get_positions",
        "description": "Get current positions",
        "input_schema": {"type": "object", "properties": {}}
    },
    {
        "name": "get_balances",
        "description": "Get USDC balance",
        "input_schema": {"type": "object", "properties": {}}
    },
    {
        "name": "get_best_prices",
        "description": "Get current bid/ask for a market",
        "input_schema": {
            "type": "object",
            "properties": {
                "market_id": {"type": "string"}
            },
            "required": ["market_id"]
        }
    }
]

SYSTEM = """You are a Polymarket trading assistant with voice input.
User speaks commands, you research and execute trades.

You have access to:
- Market search and research
- Whale trade monitoring
- Order placement (limit, market, ladder)
- Position and balance checking

Guidelines:
- ALWAYS search/research before trading unknown markets
- Show user what you found before executing trades
- Ask for confirmation before placing orders
- Prices are decimals: 0.35 = 35 cents
- When user says "$X" calculate shares: shares = dollars / price

Be conversational - user is speaking to you."""


def execute_tool(name: str, args: dict) -> str:
    """Execute a trading tool and return result"""
    try:
        if name == "search_markets":
            results = search_markets(args.get("query", ""))
            if results:
                return json.dumps(results[:5], indent=2)
            return "No markets found"

        elif name == "show_event":
            markets = show_event(args["slug"])
            if markets:
                return f"Loaded {len(markets)} markets:\n" + "\n".join(
                    f"- {m.get('question', m.get('id'))[:60]}" for m in markets[:5]
                )
            return "Event not found"

        elif name == "get_whale_trades":
            trades = fetch_recent_trades(limit=100)
            # Filter by min_usd
            min_usd = args.get("min_usd", 5000)
            whale_trades = [t for t in trades if float(t.get('size', 0)) * float(t.get('price', 0)) >= min_usd]
            if whale_trades:
                return json.dumps(whale_trades[:10], indent=2)
            return "No whale trades found above ${:.0f}".format(min_usd)

        elif name == "place_order":
            result = place_order(args["market_id"], args["side"], args["price"], args["size"])
            return f"Order result: {result}"

        elif name == "quick_buy":
            result = quick_buy(args["market_id"], args["size"])
            return f"Quick buy result: {result}"

        elif name == "quick_sell":
            result = quick_sell(args["market_id"], args["size"])
            return f"Quick sell result: {result}"

        elif name == "place_ladder":
            results = place_ladder(
                args["market_id"], args["side"],
                args["start_price"], args["end_price"],
                args["num_orders"], args["size_per_order"]
            )
            return f"Ladder placed: {len(results)} orders"

        elif name == "show_orders":
            import io
            from contextlib import redirect_stdout
            out = io.StringIO()
            with redirect_stdout(out):
                show_orders()
            return out.getvalue() or "No open orders"

        elif name == "cancel_all_orders":
            result = cancel_all_orders()
            return f"Cancelled: {result}"

        elif name == "get_positions":
            positions = get_positions()
            if positions:
                return json.dumps(positions, indent=2)
            return "No positions"

        elif name == "get_balances":
            balances = get_balances()
            return f"USDC: ${balances.get('usdc', 0):.2f}"

        elif name == "get_best_prices":
            prices = get_best_prices(args["market_id"])
            return f"Bid: {prices['best_bid']*100:.1f}¢, Ask: {prices['best_ask']*100:.1f}¢"

        else:
            return f"Unknown tool: {name}"

    except Exception as e:
        return f"Error: {e}"


def chat(user_message: str) -> str:
    """Send message to Claude and handle tool calls"""
    conversation_history.append({"role": "user", "content": user_message})

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        system=SYSTEM,
        tools=TOOLS,
        messages=conversation_history
    )

    # Process response
    assistant_content = []
    final_text = ""

    for block in response.content:
        if block.type == "text":
            final_text += block.text
            assistant_content.append(block)
        elif block.type == "tool_use":
            assistant_content.append(block)
            print(f"\n🔧 {block.name}({json.dumps(block.input)})")

            # Execute tool
            result = execute_tool(block.name, block.input)
            print(f"   → {result[:200]}...")

            # Add to conversation
            conversation_history.append({"role": "assistant", "content": assistant_content})
            conversation_history.append({
                "role": "user",
                "content": [{"type": "tool_result", "tool_use_id": block.id, "content": result}]
            })

            # Continue conversation
            return chat("")  # Recurse to get final response

    conversation_history.append({"role": "assistant", "content": assistant_content})
    return final_text


def main():
    print("=" * 60)
    print("  Claude Voice Trader - Full System")
    print("=" * 60)
    print("Voice → Transcribe → Research → Trade")
    print()
    print("ENTER = start recording (ENTER again to stop)")
    print("Type text = send as command")
    print("q = quit")
    print()

    # Load memory context
    context = memory.get_session_context()
    if context:
        print("[Memory loaded]")

    while True:
        try:
            mode = input("\n[ENTER=voice, or type command]: ").strip()

            if mode.lower() in ['q', 'quit', 'exit']:
                memory.save_all()
                print("Memory saved. Bye!")
                break

            if mode == '' or mode.lower() == 'v':
                # Voice mode - record until ENTER
                from voice.recorder import record_until_enter
                audio = record_until_enter()
                if audio is None:
                    continue

                print("Transcribing...")
                text = transcribe(audio, "auto")
                if not text or len(text) < 3:
                    print("(No speech detected)")
                    continue
                print(f'\n🎤 "{text}"')
            else:
                # Text mode
                text = mode

            # Send to Claude
            print("\n" + "-" * 40)
            response = chat(text)
            print(f"\n{response}")

            # Save to memory
            memory.record_query(text, response[:100])

        except KeyboardInterrupt:
            print("\n(Ctrl+C) Type 'q' to quit")
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    main()
