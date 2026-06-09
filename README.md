# testcursor

Automatically open a URL in your default browser when keyboard-smash behavior is detected.

## Setup

```bash
python3 -m pip install -r requirements.txt
```

## Run

```bash
python3 keyboard_smash_opener.py --url "https://example.com"
```

The program listens globally for keypresses and triggers when it detects:

- **Rapid/simultaneous key activity** (default: at least 4 presses within 120ms)
- **Likely gibberish text tokens** (default: token length >= 8 with smash-like patterns)

Use `Ctrl+C` in the terminal to stop.

## Optional tuning

```bash
python3 keyboard_smash_opener.py \
  --url "https://example.com" \
  --simultaneous-keys 5 \
  --simultaneous-window-ms 150 \
  --text-window-seconds 2.5 \
  --text-length 9 \
  --cooldown-seconds 10
```

Cooldown prevents repeated browser opens from a single smash streak.
