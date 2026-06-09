# LRC Generator

[English](README.md)

自动生成 LRC 歌词文件：Whisper AI 识别 MP3 音频，生成带时间戳的 LRC， 如果提供了歌词可以通过给定歌词进行生成。

## 功能特点

- **Whisper 语音识别** — 默认 `large-v3` 模型，中文识别大幅优于旧版；支持 `tiny` ~ `turbo` 多级精度
- **语言提示** — `--language zh` 传参给 Whisper 提升中文识别；`auto` 根据歌词自动检测
- **歌词合并** — 同一时间戳的连续歌词自动合并为一行，空格分隔
- **AI 人声分离** — 支持 `--separate` 用 demucs 提取人声后再识别，`--save-vocals` 保存分离后的人声
- **DTW 全局对齐** — 有歌词时用动态时间规整 + 拼音相似度做全局最优匹配
- **自动安装依赖** — demucs 首次使用时自动 `pip install`；ffmpeg 运行前检测
- **模型缓存复用** — 多次运行复用已加载的模型
- **批量处理** — `--batch` 批量处理整个目录
- **LRC 元信息** — 支持 `[ti:]`、`[ar:]`、`[al:]` 标签
- **Web 编辑器** — `edit/index.html` 支持 LRC 播放、歌词编辑、时间戳修改
- **MCP 支持** — 提供 MCP 服务器供 AI 助手调用

## 环境要求

- Python 3.8+
- ffmpeg
- PyTorch（Whisper 依赖）

### 安装

```bash
brew install ffmpeg                # macOS
sudo apt install ffmpeg            # Linux
pip install openai-whisper torch mcp pypinyin
```

## 使用方法

```bash
# 纯音频识别
python lrc_automaker.py song.mp3

# 带歌词对齐
python lrc_automaker.py song.mp3 lyrics.txt

# 中文歌曲（推荐）
python lrc_automaker.py song.mp3 lyrics.txt --language zh

# 人声分离（带伴奏的歌曲）
python lrc_automaker.py song.mp3 lyrics.txt --separate

# 人声分离并输出人声音频
python lrc_automaker.py song.mp3 lyrics.txt --separate --save-vocals

# 批量处理
python lrc_automaker.py /path/to/music/dir --batch
```

### 全部参数

| 参数 | 说明 | 默认 |
|------|------|------|
| `input` | MP3 文件或目录（配合 --batch） | 必需 |
| `lyrics_file` | 歌词文本（每行一句） | — |
| `output_file` | 输出 LRC 路径 | `<input>.lrc` |
| `--whisper-model` | tiny/base/small/medium/large/large-v3/turbo | large-v3 |
| `--language`, `-l` | zh/en/auto（传给 Whisper） | auto |
| `--title`, `-t` | 歌曲标题 | — |
| `--artist`, `-a` | 歌手名 | — |
| `--album`, `-al` | 专辑名 | — |
| `--separate`, `-s` | AI 人声分离（首次自动安装 demucs） | — |
| `--save-vocals` | 保存分离后的人声为 `<mp3>.vocals.wav` | — |
| `--batch`, `-b` | 批量模式 | — |
| `--output-dir`, `-o` | 批量输出目录 | 同输入目录 |
| `--verbose`, `-v` | 详细日志 | — |

## 工作原理

```
MP3 → [--separate] demucs 人声分离 → ffmpeg 16kHz WAV
     → Whisper 语音识别 → [{start, text}, ...] 片段
     → [有歌词] 拼音化 + DTW 全局对齐 → 同时间戳行自动合并
     → 写入 .lrc
```

## MCP Server

将 `mcp_config.json` 加入 AI 客户端 MCP 配置即可调用 `generate_lrc`。

| 参数 | 类型 | 说明 |
|------|------|------|
| `mp3_path` | string | MP3 绝对路径（必需） |
| `lyrics_path` | string | 歌词文件路径 |
| `output_path` | string | 输出路径 |
| `model_size` | string | tiny/base/small/medium/large/large-v3/turbo |
| `title` | string | LRC 标题 |
| `artist` | string | LRC 歌手 |
| `album` | string | LRC 专辑 |
| `separate` | boolean | 人声分离 |
| `save_vocals` | boolean | 保存人声文件 |
| `language` | string | auto/zh/en |

## 项目结构

```
├── lrc_automaker.py    # 主程序
├── mcp_server.py       # MCP 服务器
├── mcp_config.json     # MCP 配置
├── edit/index.html     # Web 编辑器
└── requirements.txt
```

## License

MIT
