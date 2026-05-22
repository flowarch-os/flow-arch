#!/usr/bin/env python3
"""Clipboard manager: PySide6 host driving a QML UI on top of cliphist + pin store.

Replaces the old wofi-based clipboard launcher. Pins live in their own JSON file
(survive cliphist wipe). History reads live from cliphist.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

from PySide6.QtCore import (
    QAbstractListModel, QByteArray, QModelIndex, QObject, Qt, QSize,
    Signal, Slot, Property,
)
from PySide6.QtGui import QGuiApplication, QImage
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickImageProvider

HOME = Path.home()
PINS_PATH = HOME / ".local/state/hyprland/clipboard_pins.json"
THEME_LINK = HOME / ".config/waybar/style.css"
SCRIPT_DIR = Path(__file__).resolve().parent
QML_PATH = SCRIPT_DIR / "ClipboardManager.qml"

HISTORY_LIMIT = 250
IMAGE_RE = re.compile(
    r"\[\[\s*binary data\s+([\d.]+\s*\w+)\s+(\w+)\s+(\d+)x(\d+)"
)


# ---------------- cliphist + wl-copy helpers ----------------

def cliphist_list() -> list[tuple[str, str]]:
    try:
        out = subprocess.run(
            ["cliphist", "list"], capture_output=True, text=True, check=True,
        ).stdout
    except (subprocess.CalledProcessError, FileNotFoundError):
        return []
    items: list[tuple[str, str]] = []
    for line in out.splitlines():
        if "\t" not in line:
            continue
        _id, preview = line.split("\t", 1)
        items.append((_id, preview))
        if len(items) >= HISTORY_LIMIT:
            break
    return items


def cliphist_decode(_id: str) -> bytes:
    try:
        return subprocess.run(
            ["cliphist", "decode"], input=_id.encode(),
            capture_output=True, check=True,
        ).stdout
    except subprocess.CalledProcessError:
        return b""


def cliphist_delete(_id: str) -> None:
    # cliphist delete reads stdin lines and matches each by leading ID.
    subprocess.run(["cliphist", "delete"], input=f"{_id}\n".encode())


def wl_copy(data: bytes, mime: str) -> None:
    subprocess.run(["wl-copy", "--type", mime], input=data, check=False)


# ---------------- Preview / kind helpers ----------------

def detect_kind(preview: str) -> tuple[str, dict]:
    m = IMAGE_RE.search(preview)
    if m:
        return "image", {
            "size": m.group(1).strip(),
            "format": m.group(2).upper(),
            "width": int(m.group(3)),
            "height": int(m.group(4)),
        }
    return "text", {}


def first_line(s: str, maxlen: int = 240) -> str:
    s = s.split("\n", 1)[0].rstrip()
    return s if len(s) <= maxlen else s[: maxlen - 1] + "…"


def text_detail(full: str) -> str:
    lines = full.count("\n") + 1
    if lines > 1:
        return f"text · {lines} lines · {len(full)} chars"
    return f"text · {len(full)} chars"


def image_detail_from_meta(meta: dict) -> str:
    return f"{meta['format']} · {meta['width']}×{meta['height']} · {meta['size']}"


def detect_image_format(data: bytes) -> str:
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "PNG"
    if data[:3] == b"\xff\xd8\xff":
        return "JPEG"
    if data[:6] in (b"GIF87a", b"GIF89a"):
        return "GIF"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "WEBP"
    return "IMG"


# ---------------- Pin store ----------------

class PinStore:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._data = self._load()

    def _load(self) -> dict:
        if not self.path.exists():
            return {"version": 1, "pins": []}
        try:
            d = json.loads(self.path.read_text())
            d.setdefault("pins", [])
            d.setdefault("version", 1)
            return d
        except Exception:
            return {"version": 1, "pins": []}

    def _save(self) -> None:
        tmp = self.path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(self._data, indent=2))
        tmp.replace(self.path)

    @property
    def pins(self) -> list[dict]:
        return self._data["pins"]

    def add(self, content: bytes, mime: str, preview: str) -> dict:
        h = hashlib.sha256(content).hexdigest()[:12]
        for p in self._data["pins"]:
            if p["id"].endswith(h):
                # Already pinned — move to top
                self._data["pins"].remove(p)
                self._data["pins"].insert(0, p)
                self._save()
                return p
        entry = {
            "id": f"pin-{int(time.time())}-{h}",
            "mime": mime,
            "content_b64": base64.b64encode(content).decode(),
            "preview": preview,
            "pinned_at": int(time.time()),
        }
        self._data["pins"].insert(0, entry)
        self._save()
        return entry

    def remove(self, pin_id: str) -> bool:
        before = len(self._data["pins"])
        self._data["pins"] = [p for p in self._data["pins"] if p["id"] != pin_id]
        if len(self._data["pins"]) < before:
            self._save()
            return True
        return False

    def get(self, pin_id: str) -> dict | None:
        for p in self._data["pins"]:
            if p["id"] == pin_id:
                return p
        return None


# ---------------- Theme ----------------

DEFAULT_THEME = {
    "bg_color": "0a1a2e",
    "fg_color": "5fbaff",
    "active_border": "5fbaff",
    "inactive_border": "1a3a5e",
}


def load_theme_colors() -> dict[str, str]:
    try:
        target = THEME_LINK.resolve()
        colors_path = target.parent / "colors"
        if not colors_path.exists():
            return dict(DEFAULT_THEME)
        out: dict[str, str] = {}
        for line in colors_path.read_text().splitlines():
            line = line.strip()
            if "=" not in line or line.startswith("#"):
                continue
            k, v = line.split("=", 1)
            out[k.strip()] = v.strip().strip("'\"")
        for k, v in DEFAULT_THEME.items():
            out.setdefault(k, v)
        return out
    except Exception:
        return dict(DEFAULT_THEME)


def to_qml_color(hex_str: str) -> str:
    h = hex_str.strip().lstrip("#")
    if len(h) in (6, 8):
        return f"#{h}"
    return "#5fbaff"


# ---------------- Image provider ----------------

class ClipboardImageProvider(QQuickImageProvider):
    """Resolves image://clipboard/<kind>/<id> URLs to decoded image bytes."""

    def __init__(self, controller: "Controller"):
        super().__init__(QQuickImageProvider.Image)
        self._ctrl = controller

    def requestImage(self, id_str, size, requested_size):
        try:
            kind, key = id_str.split("/", 1)
        except ValueError:
            return QImage()
        if kind == "history":
            data = cliphist_decode(key)
        elif kind == "pin":
            p = self._ctrl.pin_store.get(key)
            data = base64.b64decode(p["content_b64"]) if p else b""
        else:
            data = b""
        if not data:
            return QImage()
        img = QImage()
        img.loadFromData(QByteArray(data))
        if img.isNull():
            return QImage()
        if requested_size.isValid() and requested_size.width() > 0:
            img = img.scaled(
                requested_size, Qt.KeepAspectRatio, Qt.SmoothTransformation,
            )
        if size is not None:
            size.setWidth(img.width())
            size.setHeight(img.height())
        return img


# ---------------- Models ----------------

ID_ROLE = Qt.UserRole + 1
KIND_ROLE = Qt.UserRole + 2
PREVIEW_ROLE = Qt.UserRole + 3
DETAIL_ROLE = Qt.UserRole + 4
IMAGE_SRC_ROLE = Qt.UserRole + 5
IS_PINNED_ROLE = Qt.UserRole + 6


class ClipboardModel(QAbstractListModel):
    def __init__(self, is_pinned: bool):
        super().__init__()
        self._items: list[dict] = []
        self._is_pinned = is_pinned

    def roleNames(self):
        return {
            ID_ROLE: b"itemId",
            KIND_ROLE: b"kind",
            PREVIEW_ROLE: b"preview",
            DETAIL_ROLE: b"detail",
            IMAGE_SRC_ROLE: b"imageSrc",
            IS_PINNED_ROLE: b"isPinned",
        }

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self._items)

    def data(self, index, role):
        if not index.isValid() or index.row() >= len(self._items):
            return None
        it = self._items[index.row()]
        if role == ID_ROLE:
            return it["id"]
        if role == KIND_ROLE:
            return it["kind"]
        if role == PREVIEW_ROLE:
            return it["preview"]
        if role == DETAIL_ROLE:
            return it["detail"]
        if role == IMAGE_SRC_ROLE:
            return it.get("image_src", "")
        if role == IS_PINNED_ROLE:
            return self._is_pinned
        return None

    def set_items(self, items: list[dict]) -> None:
        self.beginResetModel()
        self._items = items
        self.endResetModel()

    def find(self, item_id: str) -> dict | None:
        for it in self._items:
            if it["id"] == item_id:
                return it
        return None


# ---------------- Controller ----------------

class Controller(QObject):
    closeRequested = Signal()
    filterChanged = Signal()

    def __init__(self):
        super().__init__()
        self.pin_store = PinStore(PINS_PATH)
        self.history_model = ClipboardModel(is_pinned=False)
        self.pins_model = ClipboardModel(is_pinned=True)
        self._theme = load_theme_colors()
        self._filter = ""
        self._raw_history: list[tuple[str, str]] = []
        self.refresh()

    @Property("QVariant", constant=True)
    def theme(self):
        return {
            "bg": to_qml_color(self._theme["bg_color"]),
            "fg": to_qml_color(self._theme["fg_color"]),
            "accent": to_qml_color(self._theme["active_border"]),
            "muted": to_qml_color(self._theme["inactive_border"]),
        }

    @Property(QObject, constant=True)
    def historyModel(self):
        return self.history_model

    @Property(QObject, constant=True)
    def pinsModel(self):
        return self.pins_model

    # ---- Item builders ----

    def _build_pin_item(self, p: dict) -> dict:
        is_image = p["mime"].startswith("image/")
        if is_image:
            return {
                "id": p["id"], "kind": "image",
                "preview": "",
                "detail": p.get("preview", "image"),
                "image_src": f"image://clipboard/pin/{p['id']}",
            }
        return {
            "id": p["id"], "kind": "text",
            "preview": first_line(p.get("preview", "")),
            "detail": text_detail(p.get("preview", "")),
            "image_src": "",
        }

    def _build_history_item(self, _id: str, preview_raw: str) -> dict:
        kind, meta = detect_kind(preview_raw)
        if kind == "image":
            return {
                "id": _id, "kind": "image", "preview": "",
                "detail": image_detail_from_meta(meta),
                "image_src": f"image://clipboard/history/{_id}",
                "_raw": preview_raw,
            }
        return {
            "id": _id, "kind": "text",
            "preview": first_line(preview_raw),
            "detail": text_detail(preview_raw),
            "image_src": "",
            "_raw": preview_raw,
        }

    def _apply_filter(self, items: list[dict]) -> list[dict]:
        if not self._filter:
            return items
        f = self._filter.lower()
        return [it for it in items
                if f in it.get("preview", "").lower()
                or f in it.get("detail", "").lower()]

    def refresh(self) -> None:
        pin_items = [self._build_pin_item(p) for p in self.pin_store.pins]
        self._raw_history = cliphist_list()
        hist_items = [self._build_history_item(i, p) for i, p in self._raw_history]
        self.pins_model.set_items(self._apply_filter(pin_items))
        self.history_model.set_items(self._apply_filter(hist_items))

    # ---- Slots ----

    @Slot(str)
    def setFilter(self, text: str) -> None:
        self._filter = (text or "").strip()
        self.refresh()
        self.filterChanged.emit()

    @Slot(str, bool)
    def paste(self, item_id: str, is_pinned: bool) -> None:
        if is_pinned:
            p = self.pin_store.get(item_id)
            if not p:
                return
            data = base64.b64decode(p["content_b64"])
            wl_copy(data, p["mime"])
        else:
            data = cliphist_decode(item_id)
            if not data:
                return
            it = self.history_model.find(item_id)
            mime = "text/plain"
            if it and it["kind"] == "image":
                mime = f"image/{detect_image_format(data).lower()}"
            wl_copy(data, mime)
        self.closeRequested.emit()

    @Slot(str, bool)
    def togglePin(self, item_id: str, is_pinned: bool) -> None:
        if is_pinned:
            self.pin_store.remove(item_id)
        else:
            data = cliphist_decode(item_id)
            if not data:
                return
            it = self.history_model.find(item_id)
            if it and it["kind"] == "image":
                fmt = detect_image_format(data)
                img = QImage()
                img.loadFromData(QByteArray(data))
                kib = max(1, len(data) // 1024)
                preview = f"{fmt} · {img.width()}×{img.height()} · {kib} KiB"
                mime = f"image/{fmt.lower()}"
            else:
                text = data.decode("utf-8", errors="replace")
                preview = text[:500]
                mime = "text/plain"
            self.pin_store.add(data, mime, preview)
        self.refresh()

    @Slot(str, bool)
    def deleteItem(self, item_id: str, is_pinned: bool) -> None:
        if is_pinned:
            self.pin_store.remove(item_id)
        else:
            cliphist_delete(item_id)
        self.refresh()

    @Slot()
    def wipe(self) -> None:
        subprocess.run(["cliphist", "wipe"])
        self.refresh()

    @Slot()
    def close(self) -> None:
        self.closeRequested.emit()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pos", default=None,
                    help="X,Y position for the window (logical pixels)")
    args = ap.parse_args()

    # App identity — picked up by Hyprland as the window class.
    QGuiApplication.setApplicationName("clipboard-manager")
    QGuiApplication.setDesktopFileName("clipboard-manager")
    os.environ.setdefault("QT_QPA_PLATFORM", "wayland;xcb")

    app = QGuiApplication(sys.argv)
    app.setQuitOnLastWindowClosed(True)

    controller = Controller()

    init_x, init_y = -1, -1
    if args.pos:
        try:
            init_x, init_y = (int(v) for v in args.pos.split(","))
        except ValueError:
            pass

    engine = QQmlApplicationEngine()
    engine.addImageProvider("clipboard", ClipboardImageProvider(controller))
    ctx = engine.rootContext()
    ctx.setContextProperty("controller", controller)
    ctx.setContextProperty("initialX", init_x)
    ctx.setContextProperty("initialY", init_y)

    engine.load(str(QML_PATH))
    if not engine.rootObjects():
        sys.exit(1)

    controller.closeRequested.connect(app.quit)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
