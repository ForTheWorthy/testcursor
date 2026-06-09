#!/usr/bin/env python3
"""Open a URL when keyboard-smash behavior is detected."""

from __future__ import annotations

import argparse
import math
import random
import string
import time
import webbrowser
from collections import Counter, deque
from dataclasses import dataclass, field
from typing import Deque


# Links opened on keyboard smash. One link is chosen at random per smash.
RANDOM_LINKS: list[tuple[str, float]] = [
    ("https://www.youtube.com/watch?v=9npgsPOMa5Q", 0.35),
    ("https://www.youtube.com/watch?v=2lR4xjvVMLE", 0.25),
    ("https://www.youtube.com/watch?v=iI-GoU3NCxc", 0.50),
    ("https://www.youtube.com/watch?v=aAUX5tV6EGo", 0.20),
    ("https://www.youtube.com/watch?v=nufdW7QovC8", 0.15),
    ("https://www.youtube.com/watch?v=JSPi95fKM-w", 0.30),
]


def open_random_link() -> str:
    """Pick and open a single weighted-random link from RANDOM_LINKS."""
    urls, weights = zip(*RANDOM_LINKS)
    url = random.choices(urls, weights=weights, k=1)[0]
    webbrowser.open(url, new=2)
    return url


@dataclass
class SmashDetector:
    """Detect probable keyboard-smash events from keypress activity."""

    simultaneous_keys: int = 10
    simultaneous_window_seconds: float = 0.1
    text_window_seconds: float = 2.0
    min_smash_text_length: int = 8
    cooldown_seconds: float = 5.0

    press_timestamps: Deque[float] = field(default_factory=deque)
    typed_chars: Deque[tuple[float, str]] = field(default_factory=deque)
    cooldown_until: float = 0.0

    def process_key_press(self, now: float) -> str | None:
        """Check if rapid multi-key presses indicate a smash."""
        self.press_timestamps.append(now)
        self._trim_old_presses(now)

        if len(self.press_timestamps) >= self.simultaneous_keys:
            if self._ready_to_trigger(now):
                self.cooldown_until = now + self.cooldown_seconds
                return (
                    f"Detected {len(self.press_timestamps)} presses within "
                    f"{self.simultaneous_window_seconds:.2f}s"
                )
        return None

    def process_text_character(self, char: str, now: float) -> str | None:
        """Check if typed text resembles keyboard smash gibberish."""
        if not char or not char.isprintable():
            return None

        self.typed_chars.append((now, char))
        self._trim_old_text(now)
        snippet = "".join(ch for _, ch in self.typed_chars)
        token = self._latest_token(snippet)

        if len(token) < self.min_smash_text_length:
            return None

        if self._looks_like_smash_text(token) and self._ready_to_trigger(now):
            self.cooldown_until = now + self.cooldown_seconds
            return f"Detected smash text token: {token!r}"
        return None

    def _ready_to_trigger(self, now: float) -> bool:
        return now >= self.cooldown_until

    def _trim_old_presses(self, now: float) -> None:
        cutoff = now - self.simultaneous_window_seconds
        while self.press_timestamps and self.press_timestamps[0] < cutoff:
            self.press_timestamps.popleft()

    def _trim_old_text(self, now: float) -> None:
        cutoff = now - self.text_window_seconds
        while self.typed_chars and self.typed_chars[0][0] < cutoff:
            self.typed_chars.popleft()

    @staticmethod
    def _latest_token(snippet: str) -> str:
        tokens = snippet.split()
        if not tokens:
            return ""
        return tokens[-1].strip(string.punctuation).lower()

    @staticmethod
    def _looks_like_smash_text(token: str) -> bool:
        letters = [ch for ch in token if ch.isalpha()]
        if not letters:
            return False

        vowel_count = sum(ch in "aeiou" for ch in letters)
        vowel_ratio = vowel_count / len(letters)

        max_repeat = 1
        current_repeat = 1
        for i in range(1, len(token)):
            if token[i] == token[i - 1]:
                current_repeat += 1
                max_repeat = max(max_repeat, current_repeat)
            else:
                current_repeat = 1

        entropy = SmashDetector._shannon_entropy(token)

        # Heuristics chosen to catch common smash patterns while avoiding words.
        if max_repeat >= 4:
            return True
        if vowel_ratio < 0.2 and len(letters) >= 7:
            return True
        if entropy > 2.9 and vowel_ratio < 0.35 and len(letters) >= 8:
            return True
        return False

    @staticmethod
    def _shannon_entropy(text: str) -> float:
        counts = Counter(text)
        length = len(text)
        return -sum((count / length) * math.log2(count / length) for count in counts.values())


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Watch for probable keyboard smashes and open a URL in the default browser."
        )
    )
    parser.add_argument(
        "--url",
        default=None,
        help=(
            "Optional single URL to open on smash. "
            "If omitted, links from RANDOM_LINKS in this file are opened randomly."
        ),
    )
    parser.add_argument(
        "--simultaneous-keys",
        type=int,
        default=10,
        help="Number of rapid key presses that count as a smash (default: 10).",
    )
    parser.add_argument(
        "--simultaneous-window-ms",
        type=float,
        default=100.0,
        help="Window for rapid key presses in milliseconds (default: 100).",
    )
    parser.add_argument(
        "--text-window-seconds",
        type=float,
        default=2.0,
        help="How far back to inspect typed text (default: 2.0).",
    )
    parser.add_argument(
        "--text-length",
        type=int,
        default=8,
        help="Minimum token length before gibberish checks (default: 8).",
    )
    parser.add_argument(
        "--cooldown-seconds",
        type=float,
        default=5.0,
        help="Wait time between browser opens (default: 5.0).",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        from pynput import keyboard
    except ImportError:
        print(
            "Missing dependency: pynput. Install it with:\n"
            "  python3 -m pip install pynput"
        )
        return 1

    detector = SmashDetector(
        simultaneous_keys=max(2, args.simultaneous_keys),
        simultaneous_window_seconds=max(0.01, args.simultaneous_window_ms / 1000.0),
        text_window_seconds=max(0.2, args.text_window_seconds),
        min_smash_text_length=max(3, args.text_length),
        cooldown_seconds=max(0.0, args.cooldown_seconds),
    )

    print("Keyboard smash detector is running. Press Ctrl+C to stop.")
    if args.url:
        print(f"Will open: {args.url}")
    else:
        print(f"Will randomly open one link from {len(RANDOM_LINKS)} configured URLs.")

    def trigger(reason: str) -> None:
        print(f"[{time.strftime('%H:%M:%S')}] {reason}. Opening browser...")
        if args.url:
            webbrowser.open(args.url, new=2)
            print(f"  Opened: {args.url}")
            return

        url = open_random_link()
        print(f"  Opened: {url}")

    def on_press(key: object) -> None:
        now = time.monotonic()

        reason = detector.process_key_press(now)
        if reason:
            trigger(reason)
            return

        char = getattr(key, "char", None)
        if isinstance(char, str):
            text_reason = detector.process_text_character(char, now)
            if text_reason:
                trigger(text_reason)

    with keyboard.Listener(on_press=on_press) as listener:
        listener.join()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
