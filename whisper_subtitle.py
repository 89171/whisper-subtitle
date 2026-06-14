#!/usr/bin/env python3
import argparse
import logging
import os
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

import whisper

logger = logging.getLogger("lrc_automaker")

_TAG_PATTERNS = [
    re.compile(p, re.IGNORECASE)
    for p in [
        r'\[Intro\]', r'\[Verse\]', r'\[Verse\s*\d*\]', r'\[Chorus\]', r'\[Bridge\]',
        r'\[Pre-Chorus\]', r'\[Post-Chorus\]', r'\[Hook\]', r'\[Outro\]',
        r'\[Instrumental\]', r'\[Interlude\]', r'\[Solo\]', r'\[Break\]',
        r'\[Ending\]', r'\[Rap\]', r'\[Spoken\]', r'\[Ad-lib\]', r'\[Vocal\]',
        r'\[Pre-?Verse\]', r'\[Vocal\s*Break\]', r'\[Melodic\s*Break\]',
        r'\[Guitar\]', r'\[Synth\]', r'\[Drums\]', r'\[Bass\]',
        r'\[Bridge\s*#?\d*\]', r'\[Hook\s*#?\d*\]', r'\[Pre-Chorus\s*\d*\]',
        r'\[Chorus\s*\d*\]', r'\[Verse\s*\d*\]', r'\[Outro\s*\d*\]',
    ]
]
_TAG_BRACKET = re.compile(r'\[[^\]]+\]$')
_TIMESTAMP_BRACKET = re.compile(r'\[\d{2}:\d{2}')
_PAREN_BRACKET_CONTENT = re.compile(r'\s*[\[\(][^\)\]]*[\]\)]\s*')

_MODEL_CACHE: dict[str, whisper.Whisper] = {}


@dataclass
class LrcMeta:
    title: Optional[str] = None
    artist: Optional[str] = None
    album: Optional[str] = None


def is_lyric_tag(line: str) -> bool:
    line = line.strip()
    for pat in _TAG_PATTERNS:
        if pat.match(line):
            return True
    if _TAG_BRACKET.match(line) and not _TIMESTAMP_BRACKET.match(line):
        return True
    return False


def filter_lyrics(lines: list[str]) -> list[str]:
    return [line for line in lines if line.strip() and not is_lyric_tag(line)]


def timestamp_to_lrc(seconds: float) -> str:
    minutes = int(seconds // 60)
    secs = seconds % 60
    return f"[{minutes:02d}:{secs:05.2f}]"


def _lrc_ts(seconds: float) -> str:
    minutes = int(seconds // 60)
    secs = seconds % 60
    return f"{minutes:02d}:{secs:05.2f}"


def timestamp_to_srt(start: float, end: float) -> str:
    def _fmt(t: float) -> str:
        h = int(t // 3600)
        m = int((t % 3600) // 60)
        s = int(t % 60)
        ms = int((t % 1) * 1000)
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
    return f"{_fmt(start)} --> {_fmt(end)}"


_VIDEO_EXTENSIONS = {'.mp4', '.mkv', '.webm', '.mov', '.avi', '.flv', '.wmv', '.m4v', '.ts'}


def _is_video_file(path: str) -> bool:
    return Path(path).suffix.lower() in _VIDEO_EXTENSIONS


def extract_main_lyric(line: str) -> str:
    return _PAREN_BRACKET_CONTENT.sub('', line).strip()


def _check_ffmpeg() -> bool:
    return shutil.which('ffmpeg') is not None


def _pip_install(package: str, verify_module: Optional[str] = None):
    logger.info("正在自动安装 %s ...", package)
    result = subprocess.run(
        [sys.executable, '-m', 'pip', 'install', '--force-reinstall', package],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"自动安装 {package} 失败:\n  pip install {package}\n错误: {result.stderr.strip()}"
        )
    if verify_module:
        __import__(verify_module)
        logger.info("安装完成: %s", package)


def _get_model(model_size: str) -> whisper.Whisper:
    if model_size not in _MODEL_CACHE:
        logger.info("正在加载 Whisper %s 模型...", model_size)
        _MODEL_CACHE[model_size] = whisper.load_model(model_size)
    return _MODEL_CACHE[model_size]


def _text_similarity(a: str, b: str) -> float:
    from difflib import SequenceMatcher
    try:
        from pypinyin import lazy_pinyin
        a_py = ''.join(lazy_pinyin(a))
        b_py = ''.join(lazy_pinyin(b))
    except ImportError:
        a_py = a
        b_py = b
    return SequenceMatcher(None, a_py, b_py).ratio()


_CHINESE_RE = re.compile(r'[\u4e00-\u9fff]')


def _contains_chinese(text: str) -> bool:
    return bool(_CHINESE_RE.search(text))


def _transcribe_whisper(wav_path: str, model_size: str) -> dict:
    model = _get_model(model_size)
    return model.transcribe(wav_path, word_timestamps=False)


def _detect_language_from_audio(wav_path: str) -> str:
    """用 FunASR 取音频前 15 秒做快速识别，根据识别结果含不含中文判断语言。"""
    try:
        from funasr import AutoModel
    except ImportError:
        _pip_install('funasr', verify_module='funasr')
        from funasr import AutoModel

    clip_path = tempfile.NamedTemporaryFile(suffix='.wav', delete=False).name
    try:
        subprocess.run([
            'ffmpeg', '-y', '-i', wav_path,
            '-t', '15',
            '-ar', '16000', '-ac', '1', '-c:a', 'pcm_s16le',
            clip_path,
        ], check=True, capture_output=True)

        model = AutoModel(
            model="paraformer-zh",
            vad_model="fsmn-vad",
            punc_model="ct-punc",
            disable_update=True,
        )
        raw = model.generate(input=clip_path, batch_size_s=60)
        items = raw if isinstance(raw, list) else [raw]
        text = ' '.join((item.get('text') or '').strip() for item in items)

        if _contains_chinese(text):
            return 'zh'
        return 'en'
    except Exception:
        return 'en'
    finally:
        if os.path.exists(clip_path):
            os.unlink(clip_path)


def _get_audio_duration(wav_path: str) -> float:
    """用 ffprobe 获取音频时长（秒）"""
    r = subprocess.run([
        'ffprobe', '-v', 'error',
        '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1',
        wav_path,
    ], capture_output=True, text=True)
    if r.returncode == 0 and r.stdout.strip():
        return float(r.stdout.strip())
    return 0.0


def _transcribe_paraformer(wav_path: str) -> dict:
    logger.info("正在使用 FunASR Paraformer 识别中文音频...")
    try:
        from funasr import AutoModel
    except ImportError:
        _pip_install('funasr', verify_module='funasr')
        from funasr import AutoModel

    model = AutoModel(
        model="paraformer-zh",
        vad_model="fsmn-vad",
        punc_model="ct-punc",
        disable_update=True,
    )
    raw = model.generate(input=wav_path, batch_size_s=60)

    items = raw if isinstance(raw, list) else [raw]
    full_text = ' '.join((it.get('text') or '').strip() for it in items)

    # Use ffprobe for accurate total duration
    duration = _get_audio_duration(wav_path)
    if duration <= 0:
        duration = 240.0  # fallback

    # Split text into sentences by punctuation
    sentences = re.split(r'[，。！？；：]+', full_text)
    sentences = [s.strip() for s in sentences if s.strip()]
    n = len(sentences)

    segments = []
    for i, sent in enumerate(sentences):
        t = duration * i / max(n, 1)
        segments.append({
            'start': round(t, 2),
            'end': round(t, 2),
            'text': sent,
        })

    if not segments and full_text:
        segments.append({
            'start': 0.0,
            'end': 0.0,
            'text': full_text,
        })

    return {
        'text': full_text,
        'segments': segments,
        'language': 'zh',
    }


def transcribe_audio(
    wav_path: str,
    model_size: str,
    language: str = 'auto',
    lyrics_path: Optional[str] = None,
) -> dict:
    lang_param: Optional[str] = None
    if language == 'zh':
        lang_param = 'zh'
    elif language == 'en':
        lang_param = 'en'
    elif language == 'auto' and lyrics_path:
        with open(lyrics_path, 'r', encoding='utf-8') as f:
            content = f.read()
        if _contains_chinese(content):
            lang_param = 'zh'
            logger.info("检测到歌词含中文")

    model = _get_model(model_size)
    return model.transcribe(wav_path, word_timestamps=False, language=lang_param or None)


def convert_audio_to_whisper_wav(audio_path: str) -> str:
    output_path = tempfile.NamedTemporaryFile(suffix='.wav', delete=False).name
    cmd = [
        'ffmpeg', '-y', '-i', audio_path,
        '-ar', '16000',
        '-ac', '1',
        '-c:a', 'pcm_s16le',
        output_path,
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    return output_path


def separate_vocals(mp3_path: str) -> str:
    try:
        import demucs  # noqa: F401
    except ImportError:
        _pip_install("demucs", verify_module="demucs")
    logger.info("正在使用 demucs 分离人声与伴奏...")
    output_dir = tempfile.mkdtemp()
    cmd = [
        sys.executable, '-m', 'demucs',
        '--two-stems=vocals',
        '-o', output_dir,
        mp3_path,
    ]
    with subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        bufsize=1, text=True,
    ) as proc:
        for line in proc.stdout or []:
            logger.info("demucs: %s", line.rstrip())
        proc.wait()
    if proc.returncode != 0:
        raise RuntimeError("demucs 人声分离失败")

    mp3_stem = Path(mp3_path).stem
    vocals_path = Path(output_dir) / 'htdemucs' / mp3_stem / 'vocals.wav'
    if not vocals_path.exists():
        raise FileNotFoundError(
            f"人声分离失败，未找到输出文件: {vocals_path}\n"
            f"请确认已安装 demucs: pip install 'demucs[all]'"
        )
    return str(vocals_path)


def align_lyrics(
    lyrics: list[str],
    segments: list[dict],
) -> list[tuple[str, float]]:
    if not lyrics or not segments:
        return []

    n, m = len(lyrics), len(segments)

    sim = [[0.0] * m for _ in range(n)]
    for i, lyric in enumerate(lyrics):
        l_main = extract_main_lyric(lyric)
        for j, seg in enumerate(segments):
            seg_text = seg['text'].strip()
            sim[i][j] = _text_similarity(l_main, seg_text) if seg_text else 0.0

    dp = [[-1.0] * m for _ in range(n)]
    back = [[-1] * m for _ in range(n)]

    for j in range(m):
        dp[0][j] = sim[0][j]

    for i in range(1, n):
        best_sofar = -1.0
        best_k = -1
        for j in range(m):
            if dp[i - 1][j] > best_sofar:
                best_sofar = dp[i - 1][j]
                best_k = j
            if best_sofar >= 0:
                dp[i][j] = best_sofar + sim[i][j]
                back[i][j] = best_k

    best_j = 0
    for j in range(1, m):
        if dp[n - 1][j] > dp[n - 1][best_j]:
            best_j = j

    result = []
    i, j = n - 1, best_j
    while i >= 0:
        result.append((lyrics[i], segments[j]['start']))
        j = back[i][j]
        i -= 1
    result.reverse()
    return result


def generate_subtitle(
    media_path: str,
    lyrics_path: Optional[str] = None,
    output_path: Optional[str] = None,
    whisper_model: str = 'large',
    meta: Optional[LrcMeta] = None,
    progress_callback: Optional[Callable] = None,
    separate: bool = False,
    language: str = 'auto',
    save_vocals: bool = False,
    output_format: str = 'lrc',
) -> str:
    media = Path(media_path)
    if not media.exists():
        raise FileNotFoundError(f"文件不存在: {media_path}")

    if not _check_ffmpeg():
        raise RuntimeError("未找到 ffmpeg，请先安装: brew install ffmpeg 或 sudo apt install ffmpeg")

    is_video = _is_video_file(media_path)

    if output_path is None:
        ext = '.srt' if output_format == 'srt' else '.lrc'
        output_path = media.with_suffix(ext)
    else:
        output_path = Path(output_path)

    if meta is None:
        meta = LrcMeta()

    def progress(msg: str, pct: Optional[float] = None):
        logger.info(msg)
        if progress_callback:
            progress_callback(msg, pct)

    audio_source = str(media)
    vocab_stem_dir: Optional[str] = None
    video_audio_temp: Optional[str] = None

    if is_video:
        progress("正在从视频中提取音频...", 3)
        video_audio_temp = tempfile.NamedTemporaryFile(suffix='.wav', delete=False).name
        subprocess.run([
            'ffmpeg', '-y', '-i', str(media),
            '-vn', '-ar', '16000', '-ac', '1', '-c:a', 'pcm_s16le',
            video_audio_temp,
        ], check=True, capture_output=True)
        audio_source = video_audio_temp

    if separate:
        progress("正在使用 AI 分离人声与伴奏...", 5)
        vocal_wav = separate_vocals(audio_source)
        vocab_stem_dir = str(Path(vocal_wav).parent.parent.parent)
        audio_source = vocal_wav
        if save_vocals:
            vocals_output = media.with_suffix('.vocals.wav')
            shutil.copy(vocal_wav, vocals_output)
            progress(f"人声已保存: {vocals_output}", 8)

    progress("正在转换音频格式...", 10)
    wav_path = convert_audio_to_whisper_wav(audio_source)

    try:
        lyrics: list[str] = []
        if lyrics_path:
            progress(f"正在读取歌词文件: {lyrics_path}", 15)
            with open(lyrics_path, 'r', encoding='utf-8') as f:
                content = f.read().replace('\\n', '\n')
            all_lines = content.split('\n')
            logger.info("原始文件共 %d 行", len(all_lines))
            lyrics = filter_lyrics(all_lines)
            logger.info("过滤后有效歌词: %d 行 (原始: %d 行)", len(lyrics), len(all_lines))
            progress(f"读取到 {len(lyrics)} 行有效歌词", 18)

        progress("正在识别音频...", 20)
        result = transcribe_audio(wav_path, whisper_model, language, lyrics_path)

        recognized_path = media.parent / (media.stem + '_recognized.txt')
        with open(recognized_path, 'w', encoding='utf-8') as f:
            for seg in result['segments']:
                f.write(f"{timestamp_to_lrc(seg['start'])}{seg['text'].strip()}\n")
        progress(f"识别结果已保存: {recognized_path}", 75)

        if lyrics:
            progress("正在对齐歌词与时间戳 (DTW 全局匹配)...", 80)
            raw_aligned = align_lyrics(lyrics, result['segments'])
            aligned = []
            for i, (text, ts) in enumerate(raw_aligned):
                if i < len(raw_aligned) - 1:
                    end = raw_aligned[i + 1][1]
                else:
                    end = ts + 3.0
                aligned.append((text, ts, end))
        else:
            aligned = [
                (seg['text'].strip(), seg['start'], seg['end'])
                for seg in result['segments']
                if seg['text'].strip()
            ]

        # Merge consecutive lyrics that share the same timestamp
        merged = []
        for text, ts, te in aligned:
            if merged and abs(ts - merged[-1][1]) < 0.01:
                prev = merged[-1]
                merged[-1] = (prev[0] + ' ' + text, ts, max(prev[2], te))
            else:
                merged.append((text, ts, te))

        if output_format == 'srt':
            progress(f"正在写入 SRT 字幕文件: {output_path}", 90)
            with open(output_path, 'w', encoding='utf-8') as f:
                for i, (text, ts, te) in enumerate(merged, 1):
                    f.write(f"{i}\n")
                    f.write(timestamp_to_srt(ts, te) + '\n')
                    f.write(text + '\n\n')
        else:
            progress(f"正在写入 LRC 文件: {output_path}", 90)
            with open(output_path, 'w', encoding='utf-8') as f:
                if meta.title:
                    f.write(f"[ti:{meta.title}]\n")
                if meta.artist:
                    f.write(f"[ar:{meta.artist}]\n")
                if meta.album:
                    f.write(f"[al:{meta.album}]\n")
                for text, ts, te in merged:
                    f.write(f"{timestamp_to_lrc(ts)}<{_lrc_ts(te)}>{text}\n")

        progress("完成!", 100)
        return str(output_path)

    finally:
        if os.path.exists(wav_path):
            os.unlink(wav_path)
        if vocab_stem_dir and os.path.isdir(vocab_stem_dir):
            shutil.rmtree(vocab_stem_dir, ignore_errors=True)
        if video_audio_temp and os.path.exists(video_audio_temp):
            os.unlink(video_audio_temp)


def batch_generate_subtitle(
    input_dir: str,
    output_dir: Optional[str] = None,
    whisper_model: str = 'large',
    separate: bool = False,
    language: str = 'auto',
    save_vocals: bool = False,
    output_format: str = 'lrc',
) -> list[str]:
    src = Path(input_dir)
    if not src.is_dir():
        raise NotADirectoryError(f"输入路径不是目录: {input_dir}")

    out = Path(output_dir) if output_dir else src
    out.mkdir(parents=True, exist_ok=True)

    media_exts = ['*.mp3'] + [f'*{ext}' for ext in sorted(_VIDEO_EXTENSIONS)]
    media_files = []
    for pattern in media_exts:
        media_files.extend(sorted(src.glob(pattern)))

    if not media_files:
        logger.warning("目录中没有找到支持的媒体文件 (.mp3/.mp4/.mkv 等): %s", input_dir)
        return []

    ext = '.srt' if output_format == 'srt' else '.lrc'
    results = []
    for media_path in media_files:
        lyrics_path = media_path.with_suffix('.txt')
        if not lyrics_path.exists():
            lyrics_path = None

        output_path = out / media_path.with_suffix(ext).name
        logger.info("处理: %s (歌词: %s)", media_path.name, lyrics_path.name if lyrics_path else '无')
        try:
            result = generate_subtitle(
                str(media_path),
                str(lyrics_path) if lyrics_path else None,
                str(output_path),
                whisper_model,
                separate=separate,
                language=language,
                save_vocals=save_vocals,
                output_format=output_format,
            )
            results.append(result)
            logger.info("  -> %s", result)
        except Exception as e:
            logger.error("  !! 失败: %s", e)
    return results


def setup_logging(verbose: bool = False):
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level, format="%(message)s", stream=sys.stderr)


def main():
    parser = argparse.ArgumentParser(
        description='使用 Whisper AI 将 MP3/视频文件转换为 LRC 歌词或 SRT 字幕文件'
    )
    parser.add_argument('input', help='输入的媒体文件 (MP3/MP4/MKV 等) 或目录 (配合 --batch)')
    parser.add_argument('lyrics_file', nargs='?', default=None,
                        help='歌词文本文件（每行一句，可选）')
    parser.add_argument('output_file', nargs='?', default=None,
                        help='输出的 LRC/SRT 文件路径（可选）')
    parser.add_argument('--whisper-model', default='large-v3',
                        choices=['tiny', 'base', 'small', 'medium', 'large', 'large-v3', 'turbo'],
                        help='Whisper 模型大小 (默认 large-v3)')
    parser.add_argument('--title', '-t', default=None, help='歌曲标题 (LRC 元信息)')
    parser.add_argument('--artist', '-a', default=None, help='歌手名 (LRC 元信息)')
    parser.add_argument('--album', '-al', default=None, help='专辑名 (LRC 元信息)')
    parser.add_argument('--batch', '-b', action='store_true',
                        help='批量处理模式: 将 input 作为目录处理所有媒体文件')
    parser.add_argument('--language', '-l', default='auto',
                        choices=['auto', 'zh', 'en'],
                        help='语言提示: zh/en/auto，帮助 Whisper 更精准识别 (默认 auto)')
    parser.add_argument('--separate', '-s', action='store_true',
                        help='使用 demucs AI 分离人声与伴奏后再识别（需安装 demucs）')
    parser.add_argument('--save-vocals', action='store_true',
                        help='将分离后的人声保存为 <文件>.vocals.wav')
    parser.add_argument('--format', '-f', default='lrc', choices=['lrc', 'srt'],
                        help='输出格式: lrc=歌词文件, srt=外挂字幕 (默认 lrc)')
    parser.add_argument('--verbose', '-v', action='store_true', help='显示详细日志')
    parser.add_argument('--output-dir', '-o', default=None,
                        help='批量模式下的输出目录（默认与输入目录相同）')

    args = parser.parse_args()
    setup_logging(args.verbose)

    try:
        if args.batch:
            results = batch_generate_subtitle(
                args.input, args.output_dir, args.whisper_model,
                separate=args.separate,
                language=args.language,
                save_vocals=args.save_vocals,
                output_format=args.format,
            )
            if results:
                logger.info("批量处理完成，共生成 %d 个文件", len(results))
            return

        meta = LrcMeta(title=args.title, artist=args.artist, album=args.album)
        output_path = generate_subtitle(
            args.input,
            args.lyrics_file,
            args.output_file,
            args.whisper_model,
            meta=meta,
            separate=args.separate,
            language=args.language,
            save_vocals=args.save_vocals,
            output_format=args.format,
        )
        logger.info("文件已生成: %s", output_path)
    except Exception as e:
        logger.error("错误: %s", e)
        sys.exit(1)


if __name__ == '__main__':
    main()


generate_lrc = generate_subtitle
batch_generate_lrc = batch_generate_subtitle
