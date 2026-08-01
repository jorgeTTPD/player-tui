# player-tui 🎵

Terminal music player with synchronized lyrics — Spotify-style TUI for Linux/macOS.

---

## ✨ Features

- 🎵 **Real-time synced lyrics** from LRCLIB database
- 🎮 **MPRIS2 support** — Works with Spotify, Firefox, ncspot, VLC, mpv, and any MPRIS2-compliant player
- 🎨 **Customizable themes** — 16 accent colors + 17 border colors (including white)
- 🔍 **Auto-detects** playing media via MPRIS2
- ⌨️ **Vim-like keybindings** — Intuitive keyboard controls
- 💾 **Persistent preferences** — Color choices saved to `~/.config/reproductorMusica/config.json`
- 🖥️ **True transparency** — Uses `ansi_default` for real terminal transparency
- 📱 **Responsive layout** — Adapts to terminal size

---

## 🚀 Installation

### Option 1: Standalone Binary (Recommended — No Python required)
```bash
# Linux
curl -L -o player-tui https://github.com/jorgeTTPD/player-tui/releases/latest/download/player-tui-linux
chmod +x player-tui
./player-tui

# macOS (Apple Silicon)
curl -L -o player-tui https://github.com/jorgeTTPD/player-tui/releases/latest/download/player-tui-macos
chmod +x player-tui
./player-tui
```

### Option 2: pipx (Recommended for Python users)
```bash
pipx install git+https://github.com/jorgeTTPD/player-tui.git
player-tui
```

### Option 3: From Source
```bash
git clone https://github.com/jorgeTTPD/player-tui.git
cd player-tui
pip install -e .
player-tui
```

### Option 4: Arch Linux (AUR)
```bash
yay -S player-tui-git
# or
makepkg -si
```

---

## ⌨️ Keybindings

| Key | Action |
|-----|--------|
| `space` | Play / Pause |
| `j` | Previous track (Ant) |
| `l` | Next track (Sig) |
| `i` | Volume up |
| `k` | Volume down |
| `m` | Mute toggle |
| `u` | Cycle accent color (Text) — 16 colors |
| `o` | Cycle border color (Edge) — 17 colors |
| `q` / `Esc` | Quit |

> **Footer keys** are always white. Press `Ctrl+P` for command palette.

---

## ⚙️ Configuration

Colors are persisted to `~/.config/reproductorMusica/config.json`:

```json
{
  "accent_index": 3,
  "border_index": 5
}
```

- Press `u` to cycle through 16 accent colors
- Press `o` to cycle through 17 border colors (includes white)

---

## 🖥️ Requirements

- **Linux/macOS** (MPRIS2 support)
- **Python 3.10+** (for source install)
- **Terminal with true color support** (most modern terminals)
- **MPRIS2-compatible media player** (Spotify, Firefox, ncspot, VLC, mpv, etc.)
- **D-Bus session bus** (standard on Linux desktop)

---

## 🔨 Building from Source

```bash
git clone https://github.com/jorgeTTPD/player-tui.git
cd player-tui
pip install -e .
player-tui
```

### Build Standalone Binary
```bash
pip install pyinstaller
pyinstaller --onefile --name player-tui player_tui/__main__.py
# Binary at dist/player-tui
```

---

## 📦 Packaging

| Format | Status |
|--------|--------|
| **Arch Linux (PKGBUILD)** | ✅ Included |
| **Debian/Ubuntu (.deb)** | ✅ `debian/` directory |
| **Python Wheel** | ✅ `pyproject.toml` |
| **Standalone Binary** | ✅ PyInstaller |

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

Based on [lyrics-on-panel](https://github.com/KangweiZhu/lyrics-on-panel) by KangweiZhu (MIT).

---

## 🙏 Acknowledgments

- [lyrics-on-panel](https://github.com/KangweiZhu/lyrics-on-panel) — Original lyrics backend
- [LRCLIB](https://lrclib.net/) — Lyrics database
- [Textual](https://textual.textualize.io/) — TUI framework
- [MPRIS2](https://specifications.freedesktop.org/mpris-spec/latest/) — Media Player Remote Interfacing Specification
