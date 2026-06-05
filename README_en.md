# Whisper LRC Generator

[中文](README.md)

Auto-generate LRC lyric files from MP3 audio using OpenAI Whisper.

## Features

- **Whisper ASR** — Default `large-v3` model with excellent Chinese recognition; supports `tiny` ~ `turbo`
- **Language hint** — `--language zh` passes hint to Whisper; `auto` detects from lyrics
- **Lyric merging** — Consecutive lyrics at identical timestamps are merged into one line
- **Vocal separation** — `--separate` extracts vocals with demucs before recognition
- **DTW alignment** — Global optimal alignment via dynamic time warping + pinyin similarity for Chinese
- **Auto-install** — demucs automatically installed on first use; ffmpeg checked at startup
- **Model caching** — Whisper models are cached across runs
- **Batch processing** — `--batch` processes all MP3s in a directory
- **LRC metadata** — Supports `[ti:]`, `[ar:]`, `[al:]` tags
- **Web player** — `preview/index.html` for synced LRC playback
- **MCP support** — MCP server for AI assistant integration

## Prerequisites

- Python 3.8+
- ffmpeg
- PyTorch (Whisper dependency)

### Installation

```bash
brew install ffmpeg                     # macOS
sudo apt install ffmpeg                 # Linux
pip install openai-whisper torch mcp pypinyin
```

## Usage

```bash
# Audio only (no lyrics)
python lrc_automaker.py song.mp3

# With lyric file
python lrc_automaker.py song.mp3 lyrics.txt

# Chinese songs (recommended)
python lrc_automaker.py song.mp3 lyrics.txt --language zh

# Vocal separation
python lrc_automaker.py song.mp3 lyrics.txt --separate

# Batch processing
python lrc_automaker.py /path/to/music --batch
```

### All options

| Option | Description | Default |
|--------|-------------|---------|
| `input` | MP3 file or directory (with --batch) | required |
| `lyrics_file` | Lyric text file (one line per sentence) | — |
| `output_file` | Output LRC path | `<input>.lrc` |
| `--whisper-model` | tiny/base/small/medium/large/large-v3/turbo | large-v3 |
| `--language`, `-l` | zh/en/auto (hint to Whisper) | auto |
| `--title`, `-t` | Song title (LRC metadata) | — |
| `--artist`, `-a` | Artist name | — |
| `--album`, `-al` | Album name | — |
| `--separate`, `-s` | Vocal separation (auto-installs demucs) | — |
| `--batch`, `-b` | Batch mode | — |
| `--output-dir`, `-o` | Batch output directory | same as input |
| `--verbose`, `-v` | Verbose logging | — |

## How it works

```
MP3 → [--separate] demucs vocal isolation → ffmpeg 16kHz WAV
     → Whisper speech recognition → [{start, text}, ...] segments
     → [has lyrics] pinyin + DTW global alignment → merge same-timestamp lines
     → write .lrc
```

## MCP Server

Add `mcp_config.json` to your AI client's MCP configuration to use the `generate_lrc` tool.

| Parameter | Type | Description |
|-----------|------|-------------|
| `mp3_path` | string | Absolute path to MP3 (required) |
| `lyrics_path` | string | Path to lyric file |
| `output_path` | string | Output path |
| `model_size` | string | tiny/base/small/medium/large/large-v3/turbo |
| `title` | string | LRC title |
| `artist` | string | LRC artist |
| `album` | string | LRC album |
| `separate` | boolean | Enable vocal separation |
| `language` | string | auto/zh/en |

## Project structure

```
├── lrc_automaker.py    # Main program
├── mcp_server.py       # MCP server
├── mcp_config.json     # MCP configuration
├── preview/index.html  # Web player
└── requirements.txt
```

## License

MIT
