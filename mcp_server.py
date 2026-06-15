#!/usr/bin/env python3
import logging
import sys
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from subtitle_maker import generate_subtitle, generate_lrc, setup_logging

setup_logging()
logger = logging.getLogger("mcp_server")

server = Server("subtitle-maker")


@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="generate_subtitle",
            description="使用 Whisper AI 将音频/视频文件转换为 LRC 歌词或 SRT 外挂字幕",
            inputSchema={
                "type": "object",
                "properties": {
                    "media_path": {
                        "type": "string",
                        "description": "媒体文件绝对路径 (MP3/MP4/MKV 等)"
                    },
                    "lyrics_path": {
                        "type": "string",
                        "description": "歌词文件路径（可选），不提供则直接从音频识别"
                    },
                    "output_path": {
                        "type": "string",
                        "description": "输出文件路径（可选）"
                    },
                    "model_size": {
                        "type": "string",
                        "description": "Whisper 模型: tiny/base/small/medium/large",
                        "default": "large"
                    },
                    "title": {
                        "type": "string",
                        "description": "歌曲标题（LRC 元信息，可选）"
                    },
                    "artist": {
                        "type": "string",
                        "description": "歌手名（LRC 元信息，可选）"
                    },
                    "album": {
                        "type": "string",
                        "description": "专辑名（LRC 元信息，可选）"
                    },
                    "separate": {
                        "type": "boolean",
                        "description": "是否用 demucs 分离人声与伴奏后再识别（需安装 demucs）",
                        "default": False
                    },
                    "save_vocals": {
                        "type": "boolean",
                        "description": "将分离后的人声保存为 <文件>.vocals.wav",
                        "default": False
                    },
                    "language": {
                        "type": "string",
                        "enum": ["auto", "zh", "en"],
                        "description": "语言: zh=中文(FunASR), en=英文(Whisper), auto=自动(默认)",
                        "default": "auto"
                    },
                    "format": {
                        "type": "string",
                        "enum": ["lrc", "srt"],
                        "description": "输出格式: lrc=歌词文件, srt=外挂字幕 (默认 lrc)",
                        "default": "lrc"
                    }
                },
                "required": ["media_path"]
            }
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    if name != "generate_subtitle":
        raise ValueError(f"Unknown tool: {name}")

    media_path = arguments["media_path"]
    lyrics_path = arguments.get("lyrics_path")
    output_path = arguments.get("output_path")
    model_size = arguments.get("model_size", "large")

    from subtitle_maker import LrcMeta
    meta = LrcMeta(
        title=arguments.get("title"),
        artist=arguments.get("artist"),
        album=arguments.get("album"),
    )
    separate = arguments.get("separate", False)
    save_vocals = arguments.get("save_vocals", False)
    language = arguments.get("language", "auto")
    output_format = arguments.get("format", "lrc")

    try:
        result_path = generate_subtitle(media_path, lyrics_path, output_path, model_size, meta=meta, separate=separate, language=language, save_vocals=save_vocals, output_format=output_format)
        return [TextContent(type="text", text=f"文件已生成: {result_path}")]
    except Exception as e:
        logger.error("生成字幕失败: %s", e)
        return [TextContent(type="text", text=f"生成失败: {str(e)}")]


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())