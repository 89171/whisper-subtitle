# Subtitle Maker

[English](README.md)

基于 OpenAI Whisper 的 AI 字幕/歌词生成工具，支持从音频和视频文件自动生成 LRC 歌词或 SRT 外挂字幕。

## 它能做什么

丢入音频或视频文件，自动产出带时间轴的 **LRC** 歌词（音乐播放器用）或 **SRT** 外挂字幕（视频播放器用）。可以自带歌词文本获得最佳对齐精度，也可以让 Whisper 完全自主识别。

## 核心功能

| 功能 | 说明 |
|------|------|
| **视频 → SRT 外挂字幕** | 支持 MP4/MKV/MOV/WebM/AVI 等，自动提取音频，输出标准 SRT |
| **音频 → LRC 歌词** | MP3 → Whisper 语音识别 → 带时间戳的 LRC 文件 |
| **歌词对齐** | 提供 `.txt` 歌词文件，DTW + 拼音相似度精准对齐 |
| **AI 人声分离** | `--separate` 调用 demucs 分离人声后识别，排除伴奏干扰 |
| **批量处理** | 一键处理整个文件夹的音频和视频混排媒体 |
| **中文优化** | 拼音对齐、FunASR 中文备选引擎、`--language zh` 提示 |
| **自动安装依赖** | demucs、funasr 等缺失依赖首次使用自动安装 |
| **MCP 集成** | 内置 MCP 服务器，AI 助手可直接调用 |
| **Playground** | `playground/index.html` — 加载视频+SRT 或音频+LRC，播放、双击编辑、拖拽加载、导出 |

## 快速开始

```bash
pip install openai-whisper torch mcp pypinyin
brew install ffmpeg      # macOS；Linux 用 apt install ffmpeg
```

### 音频 → LRC 歌词

```bash
python subtitle_maker.py song.mp3                        # 纯语音识别
python subtitle_maker.py song.mp3 lyrics.txt              # 带歌词对齐
python subtitle_maker.py song.mp3 lyrics.txt --language zh  # 中文歌曲
```

### 视频 → SRT 外挂字幕

```bash
python subtitle_maker.py video.mp4 -f srt                  # 纯语音识别字幕
python subtitle_maker.py video.mp4 lyrics.txt -f srt       # 带歌词对齐字幕
python subtitle_maker.py video.mp4 -f srt --separate       # 先人声分离
```

### 进阶用法

```bash
python subtitle_maker.py video.mp4 -f srt --separate --save-vocals  # 保留人声音轨
python subtitle_maker.py /path/to/files --batch -f srt              # 批量生成 SRT
python subtitle_maker.py /path/to/files --batch -f lrc              # 批量生成 LRC
```

## 支持格式

| 类型 | 输入 | 输出 |
|------|------|------|
| 音频 | `.mp3` | `.lrc` / `.srt` |
| 视频 | `.mp4` `.mkv` `.webm` `.mov` `.avi` `.flv` `.wmv` `.m4v` `.ts` | `.srt` / `.lrc` |

### 输出示例

**LRC** — 增强格式，含结束时间戳，支持卡拉OK逐字变色：
```
[ti:月光]
[ar:歌手名]
[00:12.50]<00:18.30>第一行歌词
[00:18.30]<00:24.00>第二行歌词
```

**SRT** — 视频播放器外挂字幕（VLC、IINA、mpv 等）：
```
1
00:00:12,500 --> 00:00:18,300
第一行字幕

2
00:00:18,300 --> 00:00:24,000
第二行字幕
```

## Playground

浏览器打开 `playground/index.html` 即可使用，无需服务器：

- **拖拽或点击**加载媒体和字幕文件
- **视频模式**：视频播放 + 字幕叠加层
- **音频模式**：波形动画 + 大字歌词（前/当前/后三行）
- **可编辑表格**：双击编辑时间戳和字幕文本
- **工具栏**：插入行、删除行、设当前播放时间为时间戳
- **导出**为 LRC 或 SRT（自动根据加载格式判定）
- **键盘快捷键**：空格 播放/暂停，← → 快退/快进，↑ ↓ 切行，Enter 编辑，T 设时间，Delete 删除

## 命令行参数

```
python subtitle_maker.py <输入> [歌词] [输出] [选项]
```

| 参数 | 可选值 | 默认值 | 说明 |
|------|--------|--------|------|
| `<输入>` | 路径 | *必需* | 媒体文件或目录（配合 `--batch`） |
| `[歌词]` | 路径 | — | 歌词文本文件，每行一句 |
| `[输出]` | 路径 | `<输入>.lrc` 或 `.srt` | 输出文件路径 |
| `-f, --format` | `lrc` / `srt` | `lrc` | 输出格式：歌词 / 外挂字幕 |
| `-l, --language` | `auto` / `zh` / `en` | `auto` | Whisper 语言提示 |
| `-s, --separate` | 开关 | — | demucs AI 人声分离 |
| `--save-vocals` | 开关 | — | 保存分离后的人声为 `<文件>.vocals.wav` |
| `-b, --batch` | 开关 | — | 批量处理整个目录 |
| `-o, --output-dir` | 路径 | 同输入目录 | 批量输出目录 |
| `--whisper-model` | tiny~turbo | `large-v3` | Whisper 模型精度 |
| `-t, --title` | 字符串 | — | 歌曲标题（LRC 元信息） |
| `-a, --artist` | 字符串 | — | 歌手名（LRC 元信息） |
| `-al, --album` | 字符串 | — | 专辑名（LRC 元信息） |
| `-v, --verbose` | 开关 | — | 详细日志输出 |

## 工作流程

```
媒体文件 ──→ [视频?] ffmpeg 提取音频
         ──→ [--separate?] demucs 人声分离
         ──→ 16kHz 单声道 WAV → Whisper 语音识别
         ──→ [有歌词?] DTW + 拼音全局对齐
         ──→ 写入 .lrc 或 .srt
```

## MCP 服务器

将 `mcp_config.json` 加入 AI 客户端 MCP 配置，即可使用 `generate_subtitle` 工具。

| 参数 | 类型 | 说明 |
|------|------|------|
| `media_path` | string | 媒体文件路径（必需） |
| `lyrics_path` | string | 歌词文件路径（可选） |
| `output_path` | string | 输出文件路径 |
| `model_size` | string | Whisper 模型：`tiny` ~ `turbo` |
| `format` | string | `lrc` 或 `srt` |
| `language` | string | `auto` / `zh` / `en` |
| `separate` | boolean | 人声分离 |
| `save_vocals` | boolean | 保存人声文件 |
| `title` / `artist` / `album` | string | LRC 元信息 |

## 项目结构

```
├── subtitle_maker.py       # 核心引擎
├── mcp_server.py           # MCP 服务器
├── mcp_config.json         # MCP 客户端配置
├── playground/index.html   # Playground（视频/音频 + 字幕，支持编辑）
└── requirements.txt
```

## License

MIT
