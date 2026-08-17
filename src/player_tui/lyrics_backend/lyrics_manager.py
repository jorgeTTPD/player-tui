import json
import os
import re
import threading
from pathlib import Path
import urllib.request
from urllib.parse import quote, unquote, urlencode, urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from .mpris_prober import find_players, find_playing_players
from .mpris_player import MprisPlayer, PlaybackStatus


class LyricsManager:
    """
    Core Controller: Manages player selection, tracking, and lyrics fetching.

    Note: ms here == microseconds, not miliseconds.
    """

    def __init__(self):
        self.lyrics_cache = {}
        self.cache_dir = Path(
            os.environ.get(
                "LRC_CACHE_DIR", str(Path.home() / ".cache" / "lyrics-on-panel")
            )
        )
        self._fetch_id = 0
        self.setup()

    def setup(
        self,
        playername=None,
        playerobj=None,
        title=None,
        artist=None,
        album=None,
        duration=0,
        identity=None,
        lyrics=None,
        current_lyric=None,
        playback_status=PlaybackStatus.STOPPED,
        position_ms=0,
        available_players=None,
    ):
        self.playername = playername
        self.playerobj = playerobj
        self.title = title
        self.artist = artist
        self.album = album
        self.duration = duration
        self.identity = identity
        self.lyrics = lyrics
        self.current_lyric = current_lyric
        self.playback_status = playback_status
        self.position_ms = position_ms
        self.available_players = available_players or []

    def poll_status(self, requested_playername=None):
        """
        Polls for player changes and state updates.

        requested_playername == None => Global Mode
                        == 'org.mpris.MediaPlayer2.spotify' => Spotify Mode
                        == 'org.mpris.MediaPlayer2.yesplaymusic' => YesPlayMusic Mode

        Args:
            requested_playername (str, optional): The specific DBus name to track (e.g. 'org.mpris.MediaPlayer2.spotify').
                                             If None, defaults to the first available player.
        """
        playernames = find_players()










        def set_free():
            self.setup()
            return self._get_empty_state()

        if not playernames:
            return set_free()
        current_playername = self.playername
        current_playerobj = None
        if requested_playername:
            if requested_playername in playernames:
                current_playername = requested_playername
            else:
                return self._get_empty_state()
        else:


            if self.playername and self.playername in playernames:
                try:
                    player = MprisPlayer(self.playername)
                    if player.obj:
                        if player.playback_status == PlaybackStatus.PLAYING:

                            current_playername = self.playername
                            current_playerobj = player
                        else:

                            playing_playernames = find_playing_players(playernames)
                            if playing_playernames:
                                current_playername = playing_playernames[0]
                            else:

                                current_playername = self.playername
                                current_playerobj = player
                except Exception:
                    pass

            if not current_playerobj:
                playing_playernames = find_playing_players(playernames)
                if playing_playernames:
                    current_playername = playing_playernames[0]
                elif playernames:
                    current_playername = playernames[0]
                else:
                    return set_free()
                current_playerobj = MprisPlayer(current_playername)
        if not current_playerobj:
            current_playerobj = MprisPlayer(current_playername)
        if not current_playerobj.obj:
            return set_free()

        try:
            track_info = current_playerobj.track_info
            playback_status = current_playerobj.playback_status
            position = current_playerobj.position
            identity = current_playerobj.identity
        except Exception:
            return set_free()
        track_changed = (
            self.title != track_info["title"]
            or self.artist != track_info["artist"]
            or self.album != track_info["album"]
        )
        if track_changed:
            self.title = track_info["title"]
            self.artist = track_info["artist"]
            self.album = track_info["album"]

            cached = self.lyrics_cache.get(current_playername)
            if (
                cached
                and cached["title"] == track_info["title"]
                and cached["artist"] == track_info["artist"]
                and cached["album"] == track_info["album"]
            ):
                self.lyrics = cached["lyrics"]
            else:
                cached_disk = self._load_disk_cache(current_playername, track_info)
                if cached_disk is not None:
                    self.lyrics = cached_disk
                    self.lyrics_cache[current_playername] = {
                        "title": track_info["title"],
                        "artist": track_info["artist"],
                        "album": track_info["album"],
                        "lyrics": cached_disk,
                    }
                else:
                    self.lyrics = None
                    self._fetch_id += 1
                    threading.Thread(
                        target=self._fetch_lyrics,
                        args=(current_playername, track_info, self._fetch_id),
                        daemon=True,
                    ).start()
        self.position_ms = position
        current_lyric = self._get_current_lyric()
        self.setup(
            playername=current_playername,
            playerobj=current_playerobj,
            title=track_info["title"],
            artist=track_info["artist"],
            album=track_info["album"],
            duration=track_info["length"],
            identity=identity,
            lyrics=self.lyrics,
            current_lyric=current_lyric,
            playback_status=playback_status,
            position_ms=position,
            available_players=playernames,
        )
        return self.get_state()

    def _disk_cache_path(self, playername, track_info):
        key = f"{track_info['title']}|{','.join(track_info['artist'])}|{track_info['album']}"
        safe = re.sub(r"[^A-Za-z0-9._-]+", "_", key)
        return self.cache_dir / f"{safe}.json"

    def _load_disk_cache(self, playername, track_info):
        path = self._disk_cache_path(playername, track_info)
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, list) else None
        except (FileNotFoundError, OSError, ValueError):
            return None

    def _save_disk_cache(self, playername, track_info, lyrics):
        if not lyrics:
            return
        try:
            path = self._disk_cache_path(playername, track_info)
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(lyrics, f, ensure_ascii=False)
        except OSError:
            pass

    def _fetch_lyrics(self, playername, track_info, fetch_id):

        if self._fetch_id != fetch_id:
            return
        title = track_info["title"]
        artists = track_info["artist"]
        artist = artists[0] if artists else ""
        album = track_info["album"]
        length = track_info["length"]
        url = track_info["url"]
        if not title or not artists:
            return
        try:
            lyrics = None
            if playername == "org.mpris.MediaPlayer2.yesplaymusic":
                lyrics = self._fetch_lyrics_ypm(title)
            elif playername == "org.mpris.MediaPlayer2.lx-music-desktop":
                lyrics = self._fetch_lyrics_lxmusic()
            else:
                lyrics = self._fetch_lyrics_local(url)
                if lyrics is None:

                    if self._fetch_id != fetch_id:
                        return
                    lyrics = self._fetch_lyrics_lrclib(title, artist, album, length)

            if self._fetch_id == fetch_id:
                self.lyrics = lyrics
                if lyrics:
                    self.lyrics_cache[playername] = {
                        "title": title,
                        "artist": artists,
                        "album": album,
                        "lyrics": lyrics,
                    }
                    self._save_disk_cache(playername, track_info, lyrics)
        except Exception as e:
            if self._fetch_id == fetch_id:
                self.lyrics = None

    def _http_get(self, url, timeout=5):
        """Simple HTTP GET using urllib. Returns (status_code, data) tuple."""
        try:
            with urllib.request.urlopen(url, timeout=timeout) as resp:
                return resp.status, resp.read().decode("utf-8")
        except Exception:
            return None, None

    def _fetch_lyrics_ypm(self, title):
        """Fetch lyrics from YesPlayMusic localhost API. Returns parsed lyrics or None."""
        ypm_base_url = "http://localhost:27232"
        status, text = self._http_get(f"{ypm_base_url}/player")
        if status != 200:
            return None
        data = json.loads(text)
        if (
            not data
            or not data.get("currentTrack")
            or data["currentTrack"].get("name") != title
        ):
            return None
        track_id = data["currentTrack"]["id"]
        status, text = self._http_get(f"{ypm_base_url}/api/lyric?id={track_id}")
        if status != 200:
            return None
        data = json.loads(text)
        if data and data.get("lrc") and data["lrc"].get("lyric"):
            return self._parse_lrc(data["lrc"]["lyric"])
        return None

    def _fetch_lyrics_lxmusic(self, port=23330):
        """Fetch lyrics from LX Music localhost API. Returns parsed lyrics or None."""
        lxmusic_base_url = f"http://localhost:{port}"
        status, text = self._http_get(f"{lxmusic_base_url}/lyric")
        if status == 200 and text:
            return self._parse_lrc(text)
        return None

    def _fetch_lyrics_local(self, song_path):
        """Fetch lyrics from disk."""
        if not song_path.startswith("file://"):
            return None
        lrc_path = Path(unquote(urlparse(song_path).path)).with_suffix(".lrc")
        try:
            content = lrc_path.read_text(encoding="utf-8")
        except (FileNotFoundError, PermissionError, OSError):
            return None
        return self._parse_lrc(content)

    def _fetch_lyrics_lrclib(self, title, artist, album, length):
        """Fetch lyrics from lrclib.net (compatible mode). Returns parsed lyrics or None."""
        duration_sec = length // 1000000 if length else None
        params = urlencode(
            {"track_name": title, "artist_name": artist, "album_name": album}
        )

        def fetch_exact():
            if not duration_sec:
                return None
            url = f"https://lrclib.net/api/get?{params}&duration={duration_sec}"
            status, text = self._http_get(url)
            if status == 200 and text:
                data = json.loads(text)
                return data.get("syncedLyrics")
            return None

        def fetch_search():
            url = f"https://lrclib.net/api/search?{params}"
            status, text = self._http_get(url)
            if status == 200 and text:
                data = json.loads(text)
                for result in data:
                    if result.get("syncedLyrics"):
                        return result["syncedLyrics"]
            return None

        def fetch_fuzzy():
            url = f"https://lrclib.net/api/search?q={quote(title)}"
            status, text = self._http_get(url)
            if status == 200 and text:
                data = json.loads(text)
                for result in data:
                    if result.get("syncedLyrics"):
                        return result["syncedLyrics"]
            return None


        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = {
                executor.submit(fetch_exact): 0,
                executor.submit(fetch_search): 1,
                executor.submit(fetch_fuzzy): 2,
            }
            results = [None, None, None]
            for future in as_completed(futures):
                priority = futures[future]
                try:
                    results[priority] = future.result()
                except Exception:
                    pass

        for result in results:
            if result:
                return self._parse_lrc(result)
        return None

    def _parse_lrc(self, lrc_text):
        lines = []
        for line in lrc_text.splitlines():
            parts = line.split("]")
            if len(parts) > 1:
                time_str = parts[0].replace("[", "").strip()
                lyric = parts[1].strip()
                try:
                    m, s = time_str.split(":")
                    time_ms = int((float(m) * 60 + float(s)) * 1000000)
                    lines.append({"time_ms": time_ms, "lyric": lyric})
                except:
                    continue
        return lines

    def _get_current_lyric(self):
        if not self.lyrics:
            return None
        lyrics_line_num = len(self.lyrics)
        start = 0
        end = lyrics_line_num - 1
        while start <= end:
            mid = (start + end) >> 1
            if self.position_ms == self.lyrics[mid]["time_ms"]:
                end = mid
                break
            if self.position_ms > self.lyrics[mid]["time_ms"]:
                start = mid + 1
            else:
                end = mid - 1
        if end < 0:
            return None

        while end >= 0 and not self.lyrics[end]["lyric"]:
            end -= 1
        if end < 0:
            return None
        return self.lyrics[end]["lyric"]

    def get_state(self):
        if not self.playerobj:
            return self._get_empty_state()
        return {
            "playback_status": self.playback_status.value.lower(),
            "player": {"identity": self.identity, "bus_name": self.playername},
            "track": {
                "title": self.title,
                "artist": ", ".join(self.artist) if self.artist else "",
                "album": self.album,
                "duration": self.duration,
            },
            "position_ms": self.position_ms,
            "lyrics": {
                "current_lyric": self.current_lyric,
            },
            "available_players": self.available_players,
        }

    def _get_empty_state(self):
        return {
            "playback_status": PlaybackStatus.STOPPED.value.lower(),
            "player": None,
            "track": None,
            "position_ms": 0,
            "lyrics": None,
            "avaiable_players": None,
        }
