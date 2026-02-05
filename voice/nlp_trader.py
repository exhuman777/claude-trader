#!/usr/bin/env python3
"""
Natural Language Voice Trading
Uses Claude API to interpret voice commands and execute trades
"""
import sys
import os
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from anthropic import Anthropic
from recorder import record_push_to_talk
from transcribe import transcribe, detect_language
from polymarket_api import (
    show_event, place_order, get_best_prices, show_orders,
    cancel_all_orders, get_positions, get_balances, search_markets
)
from memory import get_memory, get_mindmap

# Initialize Claude client
client = Anthropic()

SYSTEM_PROMPT = """You are a Polymarket trading assistant. Convert natural language to trading actions.

Available functions:
- search_markets(query) - Search for markets by keyword
- show_event(slug) - Load event from Polymarket URL slug
- place_order(market_id, side, price, size) - Place limit order (side: "BUY" or "SELL", price: decimal like 0.35)
- get_best_prices(market_id) - Get current bid/ask
- show_orders() - Show open orders
- cancel_all_orders() - Cancel all orders
- get_positions() - Show positions
- get_balances() - Show USDC balance

When user gives a natural language command:
1. Determine what action they want
2. If they mention a market/event, search for it first
3. Return a JSON action plan

Response format (JSON only):
{
  "thought": "brief analysis of request",
  "actions": [
    {"function": "search_markets", "args": {"query": "Trump Iran"}},
    {"function": "place_order", "args": {"market_id": "ID", "side": "BUY", "price": 0.35, "size": 10}}
  ],
  "need_confirmation": true,
  "summary": "human readable summary"
}

Price rules:
- "5 dollars" on a 35c market = ~14 shares (5 / 0.35)
- Always convert dollars to shares based on price
- Prices are decimals: 35 cents = 0.35

If you need more info, set actions to [{"function": "ask", "args": {"question": "..."}}]
"""


def interpret_command(transcript: str, context: str = "") -> dict:
    """Use Claude to interpret natural language command"""

    messages = [
        {"role": "user", "content": f"Context:\n{context}\n\nUser command: {transcript}"}
    ]

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=messages
    )

    # Parse JSON response
    text = response.content[0].text
    try:
        # Find JSON in response
        start = text.find('{')
        end = text.rfind('}') + 1
        if start >= 0 and end > start:
            return json.loads(text[start:end])
    except json.JSONDecodeError:
        pass

    return {"thought": "Could not parse", "actions": [], "summary": text}


def execute_action(action: dict) -> str:
    """Execute a single trading action"""
    func = action.get("function")
    args = action.get("args", {})

    try:
        if func == "search_markets":
            results = search_markets(args.get("query", ""))
            return f"Found {len(results)} markets: {results[:3]}"

        elif func == "show_event":
            markets = show_event(args.get("slug", ""))
            return f"Loaded {len(markets) if markets else 0} markets"

        elif func == "place_order":
            result = place_order(
                args["market_id"],
                args["side"],
                args["price"],
                args["size"]
            )
            return f"Order: {result.get('status', 'unknown')}"

        elif func == "get_best_prices":
            prices = get_best_prices(args["market_id"])
            return f"Bid: {prices['best_bid']*100:.0f}¢, Ask: {prices['best_ask']*100:.0f}¢"

        elif func == "show_orders":
            show_orders()
            return "Orders displayed"

        elif func == "cancel_all_orders":
            result = cancel_all_orders()
            return f"Cancelled: {result}"

        elif func == "get_positions":
            positions = get_positions()
            return f"Positions: {len(positions) if positions else 0}"

        elif func == "get_balances":
            balances = get_balances()
            return f"USDC: ${balances.get('usdc', 0):.2f}"

        elif func == "ask":
            return f"Question: {args.get('question', '?')}"

        else:
            return f"Unknown function: {func}"

    except Exception as e:
        return f"Error: {e}"


def voice_trading_loop():
    """Main NLP voice trading loop"""
    memory = get_memory()
    mindmap = get_mindmap()

    print("=" * 60)
    print("  Natural Language Voice Trading")
    print("=" * 60)
    print("Speak naturally - Claude interprets your commands")
    print("Hold SPACE to speak, 'q' to quit")
    print()

    # Build context from memory
    context = memory.get_session_context()

    while True:
        try:
            audio_path = record_push_to_talk()

            if audio_path is None:
                memory.save_all()
                print("Bye!")
                break

            # Transcribe
            print("Transcribing...")
            transcript = transcribe(audio_path, language="auto")
            print(f'\nYou said: "{transcript}"')

            if not transcript or len(transcript) < 3:
                print("(No speech detected)")
                continue

            # Interpret with Claude
            print("\nInterpreting...")
            plan = interpret_command(transcript, context)

            print(f"\nThought: {plan.get('thought', '')}")
            print(f"Plan: {plan.get('summary', '')}")

            actions = plan.get("actions", [])
            if not actions:
                print("No actions to execute")
                continue

            # Show actions
            print("\nActions:")
            for i, a in enumerate(actions):
                print(f"  {i+1}. {a['function']}({a.get('args', {})})")

            # Confirm if needed
            if plan.get("need_confirmation", True):
                confirm = input("\nExecute? [y/N]: ").strip().lower()
                if confirm != 'y':
                    print("Cancelled")
                    continue

            # Execute actions
            print("\nExecuting...")
            for action in actions:
                result = execute_action(action)
                print(f"  → {result}")

                # Update context with results
                context += f"\nExecuted {action['function']}: {result}"

            # Record in memory
            memory.record_query(transcript, plan.get("summary", ""))

            print()

        except KeyboardInterrupt:
            print("\n(Ctrl+C) Press q to quit")
        except Exception as e:
            print(f"Error: {e}")


if __name__ == "__main__":
    voice_trading_loop()
