#!/usr/bin/env python3
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from lrc_automaker import generate_lrc


server = Server("whisper-lrc-generator")


@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="generate_lrc",
            description="使用 Whisper AI 将 MP3 音频转换为 LRC 歌词文件",
            inputSchema={
                "type": "object",
                "properties": {
                    "mp3_path": {
                        "type": "string",
                        "description": "MP3 音频文件的绝对路径"
                    },
                    "lyrics_path": {
                        "type": "string",
                        "description": "歌词文件路径（可选），不提供则直接从音频识别"
                    },
                    "output_path": {
                        "type": "string",
                        "description": "输出 LRC 文件路径（可选）"
                    },
                    "model_size": {
                        "type": "string",
                        "description": "Whisper 模型: base/small/medium/large",
                        "default": "large"
                    }
                },
                "required": ["mp3_path"]
            }
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    if name != "generate_lrc":
        raise ValueError(f"Unknown tool: {name}")

    mp3_path = arguments["mp3_path"]
    lyrics_path = arguments.get("lyrics_path")
    output_path = arguments.get("output_path")
    model_size = arguments.get("model_size", "base")

    try:
        result_path = generate_lrc(mp3_path, lyrics_path, output_path, model_size)
        return [TextContent(type="text", text=f"LRC 文件已生成: {result_path}")]
    except Exception as e:
        return [TextContent(type="text", text=f"生成 LRC 文件失败: {str(e)}")]


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())