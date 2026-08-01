#!/usr/bin/env python3
"""Reproductor de música estilo Spotify, v2 con Textual.

Versión Textual del reproductor de la consigna de
~/Escritorio/reproductorMusica/consigna.text. Reutiliza la lógica de letras de
lyrics-on-panel (backend/src) y helpers de la v1 (player/main.py).

Ejecutar:
    player-tui

Teclas:
    espacio  play/pausa        j  anterior        i  volumen +
    q        salir             l  siguiente       k  volumen -
    m        silenciar
    u        color acento      o  color borde
"""

import time
import json
from pathlib import Path

from .lyrics_backend.lyrics_manager import LyricsManager
from .main import active_index, badge_of, clamp, fmt_time

from textual.app import App, ComposeResult  # noqa: E402
from textual.binding import Binding  # noqa: E402
from textual.containers import Horizontal, Vertical  # noqa: E402
from textual.reactive import reactive  # noqa: E402
from textual.widgets import Label, Static  # noqa: E402

POLL_INTERVAL = 0.5
RENDER_INTERVAL = 0.1
LYRIC_MIN = 3
LYRIC_MAX = 15

DIM = "#6b6b6b"

ACCENT_PALETTE = [
    "#1DB954",
    "#1E90FF",
    "#9B59B6",
    "#E67E22",
    "#E74C3C",
    "#00BCD4",
    "#E91E63",
    "#8BC34A",
    "#FFFFFF",
    "#FF5722",
    "#00E676",
    "#FFD600",
    "#FF6D00",
    "#651FFF",
    "#FF1744",
    "#00B8D4",
]
BORDER_PALETTE = [
    "#333333",
    "#1DB954",
    "#1E90FF",
    "#9B59B6",
    "#E67E22",
    "#E74C3C",
    "#00BCD4",
    "#E91E63",
    "#FF5722",
    "#00E676",
    "#FFD600",
    "#FF6D00",
    "#651FFF",
    "#FF1744",
    "#00B8D4",
    "#AEEA00",
    "#FFFFFF",
]

CONFIG_DIR = Path.home() / ".config" / "reproductorMusica"
CONFIG_FILE = CONFIG_DIR / "config.json"


class NowPlaying(Static):
    status = reactive("stopped")
    title = reactive("")
    artist = reactive("")
    album = reactive("")
    badge = reactive("")
    volume = reactive(None)
    accent_color = reactive("#1DB954")

    def render(self):
        icon = {"playing": "▶", "paused": "⏸", "stopped": "⏹"}.get(self.status, "⏹")
        header = f"{icon} {self.title}" if self.title else f"{icon} Sin reproducción"
        right = f"vol {int(self.volume * 100)}%" if self.volume is not None else ""
        if self.badge:
            right = (self.badge + " · " + right) if right else self.badge
        header_color = self.accent_color if self.status == "playing" else DIM
        sub = " — ".join(x for x in (self.artist, self.album) if x)
        return (
            f"[{header_color}]{header}[/]"
            + f"    [{DIM}]{sub}[/]" * bool(sub)
            + ("    " + right if right else "")
        )


class LyricsView(Static):
    lyrics = reactive(None)
    active_idx = reactive(None)
    accent_color = reactive("#1DB954")

    def on_resize(self) -> None:
        self.refresh()

    def render(self):
        if not self.lyrics:
            return f"[{DIM}]    Buscando letras…[/]"
        window = clamp(self.size.height - 2, LYRIC_MIN, LYRIC_MAX)
        center = window // 2
        active = self.active_idx if self.active_idx is not None else 0
        start = active - center
        lines = []
        for k in range(window):
            idx = start + k
            if 0 <= idx < len(self.lyrics):
                text = self.lyrics[idx]["lyric"]
                if idx == active:
                    lines.append(f"[bold {self.accent_color}]▶ {text}[/]")
                else:
                    lines.append(f"[{DIM}]  {text}[/]")
            else:
                lines.append("")
        return "\n".join(lines)


class ProgressBarView(Static):
    """Barra de progreso dibujada con caracteres (fondo transparente)."""

    progress = reactive(0.0)
    fill_color = reactive("#1DB954")

    def on_resize(self) -> None:
        self.refresh()

    def render(self):
        width = max(self.size.width, 1)
        fill = round(width * self.progress)
        if fill > width:
            fill = width
        filled = "━" * fill
        empty = "━" * (width - fill)
        return f"[{self.fill_color}]{filled}[/][{DIM}]{empty}[/]"


class PlayerApp(App):
    TITLE = "Reproductor"
    native_ansi_color = True
    accent_index = reactive(0)
    border_index = reactive(0)

    CSS = """
    App,
    Screen {
        background: ansi_default;
    }
    Screen {
        layout: vertical;
    }
    #nowplaying,
    #lyrics,
    #progress-row,
    #time-cur,
    #time-dur,
    #progress {
        background: ansi_default;
    }
    #nowplaying {
        border: round #333333;
        padding: 1 2;
        height: auto;
    }
    #progress-row {
        height: auto;
        padding: 0 1;
        align: center middle;
    }
    #progress {
        width: 1fr;
        height: 1;
    }
    #lyrics {
        border: round #333333;
        padding: 1 2;
        height: 1fr;
        content-align: center middle;
    }
    #lyrics-label {
        width: 1fr;
        height: auto;
    }
    """

    BINDINGS = [
        Binding("space", "play_pause", "Play/Pausa"),
        Binding("j", "prev", "Ant"),
        Binding("l", "next", "Sig"),
        Binding("i", "vol_up", "Vol+"),
        Binding("k", "vol_down", "Vol-"),
        Binding("m", "mute", "Mute"),
        Binding("q", "quit", "Quit"),
        Binding("u", "cycle_accent", "Text"),
        Binding("o", "cycle_border", "Edge"),
    ]

    def __init__(self):
        super().__init__()
        self.manager = LyricsManager()
        self.poll_raw = self.manager.position_ms or 0
        self.poll_at = time.monotonic()
        self.last_poll = self.poll_at
        self.last_volume = None
        self.state = self.manager.poll_status()
        self._last_advance = time.monotonic()

    def compose(self) -> ComposeResult:
        yield NowPlaying(id="nowplaying")
        with Horizontal(id="progress-row"):
            yield Label("0:00", id="time-cur")
            yield ProgressBarView(id="progress")
            yield Label("0:00", id="time-dur")
        yield LyricsView(id="lyrics")

    def on_mount(self) -> None:
        self._load_config()
        self.query_one("#progress", ProgressBarView).progress = 0
        self._apply_state()
        self.set_interval(POLL_INTERVAL, self.poll)
        self.set_interval(RENDER_INTERVAL, self.update_position)

    def _load_config(self) -> None:
        try:
            if CONFIG_FILE.exists():
                data = json.loads(CONFIG_FILE.read_text())
                self.accent_index = data.get("accent_index", 0) % len(ACCENT_PALETTE)
                self.border_index = data.get("border_index", 0) % len(BORDER_PALETTE)
        except Exception:
            pass

    def _save_config(self) -> None:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        CONFIG_FILE.write_text(
            json.dumps(
                {
                    "accent_index": self.accent_index,
                    "border_index": self.border_index,
                }
            )
        )

    def watch_accent_index(self, idx: int) -> None:
        try:
            color = ACCENT_PALETTE[idx]
            self.query_one("#nowplaying", NowPlaying).accent_color = color
            self.query_one("#lyrics", LyricsView).accent_color = color
            self.query_one("#progress", ProgressBarView).fill_color = color
            self._save_config()
        except Exception:
            pass

    def watch_border_index(self, idx: int) -> None:
        try:
            color = BORDER_PALETTE[idx]
            self.query_one("#nowplaying").styles.border = ("round", color)
            self.query_one("#lyrics").styles.border = ("round", color)
            self._save_config()
        except Exception:
            pass

    def _apply_state(self) -> None:
        track = self.state.get("track") or {}
        now_playing = self.query_one("#nowplaying", NowPlaying)
        now_playing.status = self.state.get("playback_status", "stopped")
        now_playing.title = track.get("title") or ""
        now_playing.artist = track.get("artist") or ""
        now_playing.album = track.get("album") or ""
        now_playing.badge = badge_of(self.manager)
        now_playing.volume = (
            self.manager.playerobj.volume if self.manager.playerobj else None
        )

        duration = track.get("duration") or 0
        self.query_one("#progress", ProgressBarView).progress = 0
        self.query_one("#time-dur", Label).update(fmt_time(duration))
        self.query_one("#lyrics", LyricsView).lyrics = self.manager.lyrics

    def poll(self) -> None:
        """Poll MPRIS state. Resiliente: las excepciones nunca matan el timer."""
        try:
            state = self.manager.poll_status()
            new_raw = self.manager.position_ms or 0
            now = time.monotonic()
            # Heartbeat: si está 'playing' pero la posición no avanza >1s, re-consultar.
            if state.get("playback_status") == "playing":
                if new_raw != self.poll_raw:
                    self._last_advance = now
                elif now - self._last_advance > 1.0:
                    try:
                        state = self.manager.poll_status()
                        new_raw = self.manager.position_ms or 0
                    except Exception:
                        pass
                    self._last_advance = now
            self.state = state
            self.poll_raw = new_raw
            self.poll_at = now
            self.last_poll = now
            self._apply_state()
        except Exception:
            pass  # reintentar en el próximo tick

    def update_position(self) -> None:
        try:
            status = self.state.get("playback_status", "stopped")
            if status == "playing":
                pos = self.poll_raw + int((time.monotonic() - self.poll_at) * 1_000_000)
            else:
                pos = self.poll_raw

            progress_widget = self.query_one("#progress", ProgressBarView)
            duration = self.state.get("track", {}).get("duration") or 0
            if duration > 0:
                progress_widget.progress = pos / duration
            else:
                progress_widget.progress = 0
            self.query_one("#time-cur", Label).update(fmt_time(pos))

            lyrics_view = self.query_one("#lyrics", LyricsView)
            lyrics_view.active_idx = active_index(lyrics_view.lyrics, pos)
        except Exception:
            pass

    def action_play_pause(self) -> None:
        if self.manager.playerobj:
            self.manager.playerobj.play_pause()

    def action_next(self) -> None:
        if self.manager.playerobj:
            self.manager.playerobj.next()

    def action_prev(self) -> None:
        if self.manager.playerobj:
            self.manager.playerobj.previous()

    def action_vol_up(self) -> None:
        if self.manager.playerobj:
            self.manager.playerobj.volume = clamp(
                self.manager.playerobj.volume + 0.05, 0.0, 1.0
            )

    def action_vol_down(self) -> None:
        if self.manager.playerobj:
            self.manager.playerobj.volume = clamp(
                self.manager.playerobj.volume - 0.05, 0.0, 1.0
            )

    def action_mute(self) -> None:
        player = self.manager.playerobj
        if not player:
            return
        if player.volume > 0:
            self.last_volume = player.volume
            player.volume = 0.0
        else:
            player.volume = self.last_volume if self.last_volume is not None else 1.0

    def action_cycle_accent(self) -> None:
        self.accent_index = (self.accent_index + 1) % len(ACCENT_PALETTE)

    def action_cycle_border(self) -> None:
        self.border_index = (self.border_index + 1) % len(BORDER_PALETTE)


def main() -> None:
    PlayerApp().run()


if __name__ == "__main__":
    main()
