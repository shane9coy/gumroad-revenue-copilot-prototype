from __future__ import annotations

import argparse
import base64
import re
import subprocess
import sys
from pathlib import Path

from openai import OpenAI

SCRIPT_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from gumroad_merchant.settings import PROJECT_ROOT, get_settings, load_local_env


DEFAULT_PROMPT = (
    "Small app icon test for Gumroad Merchant: a simple hooded merchant guide "
    "with a tiny cart, warm but not goofy, clean vector-like shapes, minimal detail, "
    "transparent background if supported."
)


def sanitize_error(error: Exception) -> str:
    message = f"{type(error).__name__}: {error}"
    message = re.sub(r"sk-[A-Za-z0-9_*\\-]+", "sk-REDACTED", message)
    return re.sub(r"api[_ -]?key[^,}]+", "api key redacted", message, flags=re.IGNORECASE)[:500]


def downscale_with_sips(path: Path, max_px: int) -> None:
    if max_px <= 0:
        return
    try:
        subprocess.run(
            ["/usr/bin/sips", "-Z", str(max_px), str(path)],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        print(f"saved original API output; local downscale to {max_px}px was unavailable")


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate one low-cost Gumroad Merchant test image.")
    parser.add_argument("--prompt", default=DEFAULT_PROMPT)
    parser.add_argument("--out", default="assets/generated/gumroad-merchant-test.png")
    parser.add_argument("--no-downscale", action="store_true")
    args = parser.parse_args()

    load_local_env()
    settings = get_settings()
    output_path = Path(args.out)
    if not output_path.is_absolute():
        output_path = PROJECT_ROOT / output_path
    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        response = OpenAI().images.generate(
            model=settings.openai_image_model,
            prompt=args.prompt,
            size=settings.openai_image_size,
            quality=settings.openai_image_quality,
            n=1,
            output_format="png",
            background="transparent",
        )
        image_b64 = response.data[0].b64_json
        if not image_b64:
            raise RuntimeError("OpenAI image response did not include base64 image data")
        output_path.write_bytes(base64.b64decode(image_b64))
        if not args.no_downscale:
            downscale_with_sips(output_path, settings.openai_image_output_max_px)
        print(f"saved {output_path}")
        print(
            "settings "
            f"model={settings.openai_image_model} "
            f"quality={settings.openai_image_quality} "
            f"api_size={settings.openai_image_size} "
            f"local_max_px={settings.openai_image_output_max_px}"
        )
        return 0
    except Exception as exc:
        print(sanitize_error(exc))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
