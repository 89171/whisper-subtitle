# Whisper LRC Generator

使用 OpenAI Whisper 自动语音识别技术，将 MP3 音频与歌词文本对齐，生成 LRC 格式的歌词文件。

## 功能特点

- **自动时间戳对齐** - 无需手动标记，Whisper AI 自动识别语音并同步歌词
- **智能修正** - 使用文本相似度算法匹配歌词与识别结果，自动修正 Whisper 识别偏差
- **多语言支持** - 基于 Whisper 模型，支持中文、英文、日文等多种语言
- **灵活模型选择** - 可选择 base/small/medium/large 等不同精度的模型
- **音频自动处理** - 自动将 MP3 转换为 16kHz WAV 格式
- **批量处理** - 支持命令行批量转换
- **MCP 支持** - 提供 MCP (Model Context Protocol) 服务器，可供 AI 助手直接调用
- **歌词标签过滤** - 自动过滤 [Intro]、[Verse]、[Chorus] 等非歌词标签
- **在线预览播放器** - 提供 Web 在线播放器，支持 LRC 歌词同步展示

## 环境要求

- Python 3.8+
- ffmpeg (用于音频格式转换)
- OpenAI Whisper
- torch (Whisper 依赖)

## 安装

### 1. 安装 ffmpeg

**macOS (Homebrew):**
```bash
brew install ffmpeg
```

**Ubuntu/Debian:**
```bash
sudo apt update && sudo apt install ffmpeg
```

**Windows:** 从 [ffmpeg官网](https://ffmpeg.org/download.html) 下载并配置

### 2. 安装 Python 依赖

```bash
pip install openai-whisper torch
```

或使用 requirements.txt:
```bash
pip install -r requirements.txt
```

## 使用方法

### 纯音频识别（无歌词文件）

不提供歌词文件时，直接从音频识别演唱内容生成LRC：

```bash
python lrc_automaker.py song.mp3
python lrc_automaker.py song.mp3 small
```

### 带歌词文件

提供歌词文件时，将歌词与音频时间戳对齐：

```bash
python lrc_automaker.py <mp3文件> <歌词文件> [输出文件] [模型大小]
```

### 参数说明

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `<mp3文件>` | 输入的 MP3 音频文件 | 必需 |
| `<歌词文件>` | 歌词文本文件（每行一句） | 必需 |
| `[输出文件]` | 生成的 LRC 文件路径 | `<mp3文件>.lrc` |
| `[模型大小]` | Whisper 模型: base/small/medium/large | large |

### 模型选择指南

> **推荐**: 默认使用 `large` 模型以获得最佳的时间戳和识别效果。

| 模型 | 精度 | 速度 | 内存需求 | 推荐场景 |
|------|------|------|----------|----------|
| base | 一般 | 最快 | ~1GB | 快速测试 |
| small | 较好 | 快 | ~2GB | 日常使用 |
| medium | 很好 | 较慢 | ~5GB | **日常推荐** |
| large | 最佳 | 慢 | ~10GB | **默认推荐** |

### 使用示例

**示例 1：基本用法（默认 large 模型）**
```bash
python lrc_automaker.py song.mp3 lyrics.txt song.lrc
```

**示例 2：使用 medium 模型**
```bash
python lrc_automaker.py song.mp3 lyrics.txt song.lrc medium
```

**示例 3：使用 small 模型（快速测试）**
```bash
python lrc_automaker.py song.mp3 lyrics.txt song.lrc small
```

## 歌词文件格式

歌词文件应为纯文本格式，每行一句歌词：

```
床前明月光
疑是地上霜
举头望明月
低头思故乡
```

支持带时间标注的歌词行（如 `[00:30.30]当年杨柳依依`）或纯文本歌词。

## 工作原理

1. **音频预处理** - 使用 ffmpeg 将输入音频转换为 16kHz WAV 格式
2. **语音识别** - 使用 Whisper 模型进行语音转文字，获取每个词/句的时间戳
3. **歌词对齐** - 将歌词文本的每一行与识别出的时间戳按顺序对应
4. **LRC 生成** - 将对齐后的歌词和时间戳写入标准 LRC 格式文件

## 注意事项

- 歌词行数应与演唱句数相近，否则多余的歌词行将没有时间戳
- 建议使用较小模型先测试，确认格式正确后再使用大模型
- 首次运行时会自动下载 Whisper 模型（约 1-10GB）
- 音频质量会影响识别效果，建议使用清晰的人声录音

## MCP Server

本项目提供 MCP (Model Context Protocol) 服务器，可供 AI 助手直接调用。

### 安装 MCP 依赖

```bash
pip install mcp openai-whisper torch
```

### 配置 AI 客户端

#### Claude CLI
```bash
# 将 mcp_config.json 内容添加到 ~/.claude/mcp.json
```

#### Cursor / Windsurf 等编辑器
在设置中添加 MCP 服务器，配置同上。

### MCP 工具使用

**工具名称:** `generate_lrc`

**参数:**
| 参数 | 类型 | 说明 |
|------|------|------|
| `mp3_path` | string | MP3 音频文件的绝对路径（必需） |
| `lyrics_path` | string | 歌词文件路径（可选），不提供则直接从音频识别 |
| `output_path` | string | 输出 LRC 文件路径（可选） |
| `model_size` | string | Whisper 模型: base/small/medium/large（默认: large） |

**使用示例:**
```
帮我把 /path/to/song.mp3 生成 LRC 文件

用 /path/to/song.mp3 和 /path/to/lyrics.txt 生成 LRC，输出到 /path/to/output.lrc
```

## 项目结构

```
lrc_automaker/
├── lrc_automaker.py    # 命令行主程序
├── mcp_server.py      # MCP 服务器
├── mcp_config.json    # MCP 配置文件
├── README.md           # 项目文档
└── requirements.txt    # Python 依赖
```

## License

MIT License
