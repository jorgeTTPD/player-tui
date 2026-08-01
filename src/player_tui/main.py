"""Helper functions for player-tui.

Extraídas de la v1 del reproductor original (~/Escritorio/reproductorMusica/player/main.py).
"""


def clamp(value, lo, hi):
    return max(lo, min(hi, value))


def fmt_time(us):
    us = max(0, us)
    secs = int(us // 1_000_000)
    h, rem = divmod(secs, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


def active_index(lyrics, pos_us):
    if not lyrics:
        return None
    lo, hi = 0, len(lyrics) - 1
    idx = -1
    while lo <= hi:
        mid = (lo + hi) // 2
        if lyrics[mid]["time_ms"] <= pos_us:
            idx = mid
            lo = mid + 1
        else:
            hi = mid - 1
    return idx if idx >= 0 else None


def badge_of(manager):
    player = manager.playerobj
    if not player:
        return ""
    entry = (player.desktop_entry or "").lower()
    if "spotify" in entry:
        return "Spotify"
    if "firefox" in entry:
        return "Firefox"
    if "chromium" in entry or "chrome" in entry:
        return "Chromium"
    if "vlc" in entry:
        return "VLC"
    if "mpv" in entry:
        return "mpv"
    return manager.identity or player.dbus_identifier
