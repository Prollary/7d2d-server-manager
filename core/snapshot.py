"""滚动快照与回档管理"""
import os
import zipfile
import shutil
import threading
import time
from datetime import datetime

SNAP_DIR = "_snapshots"
TAGS = ["5min", "30min", "3h", "daily"]
INTERVALS = {"5min": 300, "30min": 1800, "3h": 10800}


class SnapshotManager:
    def __init__(self, saves_dir: str):
        self.saves_dir = saves_dir
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._last: dict[str, float] = {t: 0.0 for t in TAGS}
        self._lock = threading.Lock()

    # ── 公开 API ──

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()

    def list_snapshots(self) -> dict:
        sd = self._snap_dir()
        result = {}
        for tag in TAGS:
            snaps = self._snaps_for(sd, tag)
            result[tag] = snaps[0] if snaps else None
        return result

    def create_now(self, tag: str) -> str | None:
        return self._create(tag)

    def rollback(self, tag: str) -> tuple[bool, str]:
        sd = self._snap_dir()
        snaps = self._snaps_for(sd, tag)
        if not snaps:
            return False, f"没有找到 {tag} 的快照，请确认服务器已运行过一段时间"
        snap_path = os.path.join(sd, snaps[0])
        try:
            self._create("pre_rollback")
            for item in os.listdir(self.saves_dir):
                if item == SNAP_DIR:
                    continue
                p = os.path.join(self.saves_dir, item)
                shutil.rmtree(p) if os.path.isdir(p) else os.remove(p)
            with zipfile.ZipFile(snap_path, "r") as zf:
                zf.extractall(self.saves_dir)
            ts = snaps[0].replace(f"snap_{tag}_", "").replace(".zip", "")
            return True, f"回档成功（快照时间：{ts}）"
        except Exception as e:
            return False, f"回档失败：{e}"

    # ── 内部 ──

    def _snap_dir(self) -> str:
        d = os.path.join(self.saves_dir, SNAP_DIR)
        os.makedirs(d, exist_ok=True)
        return d

    def _snaps_for(self, sd: str, tag: str) -> list[str]:
        try:
            return sorted(
                [f for f in os.listdir(sd) if f.startswith(f"snap_{tag}_") and f.endswith(".zip")],
                reverse=True,
            )
        except Exception:
            return []

    def _create(self, tag: str) -> str | None:
        sd = self._snap_dir()
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = os.path.join(sd, f"snap_{tag}_{ts}.zip")
        try:
            with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
                for root, dirs, files in os.walk(self.saves_dir):
                    dirs[:] = [d for d in dirs if d != SNAP_DIR]
                    for f in files:
                        fp = os.path.join(root, f)
                        zf.write(fp, os.path.relpath(fp, self.saves_dir))
            self._trim(sd, tag)
            return path
        except Exception as e:
            print(f"[Snapshot] {tag} failed: {e}")
            return None

    def _trim(self, sd: str, tag: str, keep: int = 3):
        for old in self._snaps_for(sd, tag)[keep:]:
            try:
                os.remove(os.path.join(sd, old))
            except Exception:
                pass

    def _loop(self):
        midnight_done_today = False
        while not self._stop.wait(60):
            now = time.time()
            for tag, interval in INTERVALS.items():
                if now - self._last[tag] >= interval:
                    self._create(tag)
                    self._last[tag] = now

            today = datetime.now()
            if today.hour == 0 and today.minute < 5 and not midnight_done_today:
                self._create("daily")
                midnight_done_today = True
            elif today.hour != 0:
                midnight_done_today = False
