"""Regenerate AgroDoctor's bundled spoken guidance from its bilingual phrase table.

Build-time only. Install piper-tts==1.8.0, Node >=22.18 and FFmpeg. Supply a
directory containing the two ONNX files and their adjacent .onnx.json files
listed in apps/web/public/advice-audio/credits.txt. No text leaves this machine.
"""

import argparse
import json
import subprocess
import tempfile
import wave
from pathlib import Path

from piper import PiperVoice, SynthesisConfig


WEB = Path(__file__).resolve().parents[1] / "apps" / "web"
MODELS = {"bn": "bn_BD-google-medium", "en": "en_US-ljspeech-medium"}


def clip_name(text):
    # Match the FNV-1a filename used by the browser. Iterate Unicode code points.
    value = 2166136261
    for char in text:
        value = ((value ^ ord(char)) * 16777619) & 0xFFFFFFFF
    return f"{value:08x}.mp3"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("models", type=Path)
    args = parser.parse_args()
    phrases = json.loads(subprocess.check_output([
        "node", "--input-type=module", "-e",
        "import {farmerGuidancePhrases} from './src/lib/farmer-guidance.ts';"
        "process.stdout.write(JSON.stringify(farmerGuidancePhrases));",
    ], cwd=WEB))

    with tempfile.TemporaryDirectory() as temporary:
        wav = Path(temporary) / "phrase.wav"
        for locale, model in MODELS.items():
            voice = PiperVoice.load(args.models / f"{model}.onnx")
            directory = WEB / "public" / "advice-audio" / locale
            directory.mkdir(parents=True, exist_ok=True)
            settings = SynthesisConfig(speaker_id=0 if locale == "bn" else None)
            for phrase in phrases:
                text = phrase[locale]
                with wave.open(str(wav), "wb") as audio:
                    voice.synthesize_wav(text, audio, syn_config=settings)
                subprocess.run([
                    "ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(wav),
                    "-codec:a", "libmp3lame", "-b:a", "64k", "-metadata", f"title={text}",
                    "-metadata", f"artist=AgroDoctor, Piper {model}",
                    "-metadata", "comment=Voice and dataset credits: /advice-audio/credits.txt",
                    "-metadata", "license=https://creativecommons.org/licenses/by-sa/4.0/" if locale == "bn"
                    else "license=Public-domain source dataset (LJ Speech)",
                    str(directory / clip_name(text)),
                ], check=True)
            print(f"{locale}: generated {len(phrases)} phrases", flush=True)


if __name__ == "__main__":
    main()
