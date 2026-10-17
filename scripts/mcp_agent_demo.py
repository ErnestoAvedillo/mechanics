"""
Demo agent: Nemotron (Nebius Token Factory) calling the specs MCP server.

Run inside the django container:
  docker exec -w /app/src django python -W ignore /app/scripts/mcp_agent_demo.py <user_id> "<question>"
"""
import asyncio
import json
import os
import sys

if os.path.isdir("/tmp/mcp_lib"):  # temporary: remove once mcp is installed in the image
    sys.path.append("/tmp/mcp_lib")

from mcp import Client  # noqa: E402
from mcp.client.stdio import StdioServerParameters  # noqa: E402
from openai import OpenAI  # noqa: E402

MODEL = os.environ.get("NEBIUS_LLM_MODEL", "nvidia/nemotron-3-super-120b-a12b")
SYSTEM = (
    "You are an engineering assistant. For any requirement or value from a standard, use the "
    "search tool and never invent values. For spring calculations, use the calculation tools "
    "and compare the result with the limits found in the standards. Never state that a design "
    "is acceptable or not unless a limit from a retrieved standard supports it; if no limit was "
    "found, report the calculated values and say that no limit was found. "
    "Answer in the same language as the user's question. "
    "Cite every requirement with the exact file name of its source document in parentheses, "
    "for example (TL 245 - 2025.pdf). Do not use any other citation markers or footnotes."
)
MAX_STEPS = 5


def msg(es, en):
    """Console messages are shown in Spanish and English."""
    return f"{es} / {en}"


async def main(user_id, question):
    llm = OpenAI(base_url=os.environ.get("NEBIUS_BASE_URL", "https://api.tokenfactory.nebius.com/v1/"),
                 api_key=os.environ["NEBIUS_API_KEY"])
    params = StdioServerParameters(
        command=sys.executable,
        args=["-W", "ignore", "-m", "specs.mcp_server"],
        env={**os.environ, "SPECS_MCP_USER_ID": str(user_id)},
    )
    async with Client(params) as client:
        listed = await client.list_tools()
        tools = [
            {"type": "function", "function": {
                "name": t.name, "description": t.description or "", "parameters": t.input_schema}}
            for t in listed.tools
        ]
        print(msg("Herramientas MCP", "MCP tools"), [t["function"]["name"] for t in tools])

        messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": question}]
        for _ in range(MAX_STEPS):
            reply = llm.chat.completions.create(model=MODEL, messages=messages, tools=tools).choices[0].message
            messages.append(reply.model_dump(exclude_none=True))
            if not reply.tool_calls:
                print("\n" + msg("RESPUESTA", "ANSWER") + ":\n" + (reply.content or "").strip())
                return
            for call in reply.tool_calls:
                args = json.loads(call.function.arguments or "{}")
                print(f"-> {call.function.name}({args})")
                result = await client.call_tool(call.function.name, args)
                text = "".join(getattr(c, "text", "") for c in result.content)
                print("  ", msg(f"{len(text)} caracteres de contexto recuperados",
                                f"{len(text)} characters of context retrieved"))
                messages.append({"role": "tool", "tool_call_id": call.id, "content": text})
        print(msg(f"Sin respuesta final tras {MAX_STEPS} pasos", f"No final answer after {MAX_STEPS} steps"))


if __name__ == "__main__":
    asyncio.run(main(int(sys.argv[1]), sys.argv[2]))
