"""Загрузка ассетов и анимаций.

Ассеты генерируются tools/generate_assets.py в assets/. Если ассетов нет,
игра продолжает работать на примитивах: все методы возвращают None, а
модели используют старый прямоугольный рендер.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import pygame as pg

ASSET_ROOT = Path(__file__).resolve().parent.parent / "assets"

UNIT_GROUPS = ("players", "enemies", "npcs", "animals")

# Иконка по префиксу item_id (sword_iron..., bow_wood..., staff_oak...).
# Ключи могут быть полными id шаблона: побеждает самый длинный префикс.
ITEM_ID_ICONS = {
    "sword": "sword",
    "dagger": "dagger",
    "staff": "staff",
    "bow": "bow",
    "axe": "axe",
    "shield": "shield",
    "helmet": "helmet",
    "armor": "armor",
    "gloves": "gloves",
    "boots": "boots",
    "amulet": "amulet",
    "ring": "ring",
    "shield_wood": "shield_wood",
    "shield_iron": "shield_iron",
    "helmet_leather": "helmet_leather",
    "helmet_iron": "helmet_iron",
    "armor_leather": "armor_leather",
    "armor_chain": "armor_chain",
}

# Запасной вариант — по типу предмета.
ITEM_TYPE_ICONS = {
    "weapon": "sword",
    "shield": "shield",
    "helmet": "helmet",
    "armor": "armor",
    "gloves": "gloves",
    "boots": "boots",
    "amulet": "amulet",
    "ring": "ring",
    "consumable": "potion",
}


def facing_from_delta(dx: float, dy: float, default: str = "down") -> str:
    if abs(dx) < 0.01 and abs(dy) < 0.01:
        return default
    if abs(dx) >= abs(dy):
        return "right" if dx > 0 else "left"
    return "down" if dy > 0 else "up"


def _tint(surface: pg.Surface, color) -> pg.Surface:
    copy = surface.copy()
    r, g, b = tuple(color)[:3]
    copy.fill((r, g, b, 255), special_flags=pg.BLEND_RGBA_MULT)
    return copy


class AssetManager:
    def __init__(self, root: Path = ASSET_ROOT):
        self.root = Path(root)
        self.manifest = {}
        self.available = False
        self._images: dict[str, pg.Surface] = {}
        self._tile_cache: dict[tuple, list[pg.Surface]] = {}
        self._frames_cache: dict[tuple, list[pg.Surface]] = {}
        self._grid_cache: dict[tuple, pg.Surface | None] = {}
        self._tint_cache: dict[tuple, list[pg.Surface]] = {}
        self._scale_cache: dict[tuple, pg.Surface] = {}
        self._tile_colors: dict[str, tuple] = {}
        self._load_manifest()

    # ------------------------------------------------------------------
    # Загрузка
    # ------------------------------------------------------------------
    def _load_manifest(self):
        path = self.root / "manifest.json"
        try:
            self.manifest = json.loads(path.read_text(encoding="utf-8"))
            self.available = True
        except (OSError, ValueError):
            self.manifest = {}
            self.available = False

    def reload(self):
        self._images.clear()
        self._tile_cache.clear()
        self._frames_cache.clear()
        self._grid_cache.clear()
        self._tint_cache.clear()
        self._scale_cache.clear()
        self._tile_colors.clear()
        self._load_manifest()

    def image(self, relpath: str):
        if not self.available:
            return None
        cached = self._images.get(relpath)
        if cached is not None:
            return cached
        path = self.root / relpath
        try:
            surface = pg.image.load(str(path))
            if pg.display.get_init() and pg.display.get_surface() is not None:
                surface = surface.convert_alpha()
        except (pg.error, FileNotFoundError):
            return None
        self._images[relpath] = surface
        return surface

    def _sheet(self, group: str):
        meta = self.manifest.get(group)
        if meta is None:
            # Персонажи лежат во вложенном разделе "characters".
            meta = self.manifest.get("characters", {}).get(group)
        if not meta:
            return None, None
        return self.image(meta["sheet"]), meta

    @staticmethod
    def _sub(sheet, x, y, w, h):
        rect = pg.Rect(x, y, w, h)
        if rect.right > sheet.get_width() or rect.bottom > sheet.get_height():
            return None
        return sheet.subsurface(rect).copy()

    def _frames(self, group, key, direction, clip):
        """Список кадров клипа из листа группы."""
        cache_key = (group, key, direction, clip)
        cached = self._frames_cache.get(cache_key)
        if cached is not None:
            return cached
        sheet, meta = self._sheet(group)
        if sheet is None:
            return []
        index = meta.get("index", {})
        if key not in index:
            if not index:
                return []
            key = next(iter(index))
        clip_meta = meta.get("clips", {}).get(clip)
        if not clip_meta:
            return []
        dirs = meta.get("directions", {})
        row = int(index[key]) + int(dirs.get(direction, 0))
        fw, fh = meta.get("frame", [32, 32])
        frames = []
        for i in range(int(clip_meta.get("count", 1))):
            col = int(clip_meta.get("start", 0)) + i
            frame = self._sub(sheet, col * fw, row * fh, fw, fh)
            if frame is not None:
                frames.append(frame)
        self._frames_cache[cache_key] = frames
        return frames

    # ------------------------------------------------------------------
    # Юниты
    # ------------------------------------------------------------------
    def clip_info(self, group: str, clip: str):
        meta = self.manifest.get(group, {})
        return meta.get("clips", {}).get(clip, {"fps": 8.0, "loop": True, "count": 1})

    def unit_frame(self, group, key, direction, clip, elapsed):
        """Кадр анимации по прошедшему времени. None, если ассетов нет."""
        if not self.available or group not in UNIT_GROUPS:
            return None
        frames = self._frames(group, key, direction, clip)
        if not frames:
            return None
        info = self.clip_info(group, clip)
        fps = float(info.get("fps", 8.0))
        idx = int(max(0.0, elapsed) * fps)
        if info.get("loop", True):
            idx %= len(frames)
        else:
            idx = min(idx, len(frames) - 1)
        return frames[idx]

    def unit_portrait(self, group, key, direction="down", scale=4):
        frame = self.unit_frame(group, key, direction, "idle", 0.0)
        if frame is None:
            return None
        return self.scaled(frame, frame.get_width() * scale, frame.get_height() * scale)

    # ------------------------------------------------------------------
    # Тайлы и пропсы
    # ------------------------------------------------------------------
    def tile_frames(self, name):
        cache_key = ("tile", name)
        cached = self._tile_cache.get(cache_key)
        if cached is not None:
            return cached
        meta = self.manifest.get("tiles")
        if not meta:
            return []
        slots = meta.get("index", {}).get(name, [])
        sheet = self.image(meta["sheet"])
        if sheet is None:
            return []
        fw, fh = meta.get("frame", [32, 32])
        frames = []
        for c, r in slots:
            frame = self._sub(sheet, c * fw, r * fh, fw, fh)
            if frame is not None:
                frames.append(frame)
        self._tile_cache[cache_key] = frames
        return frames

    def tile(self, name, variant=0, time=0.0):
        frames = self.tile_frames(name)
        if not frames:
            return None
        if name in ("water",) and len(frames) > 1:
            return frames[int(time * 4) % len(frames)]
        return frames[variant % len(frames)]

    def tile_color(self, name, fallback=(80, 80, 80)):
        if name in self._tile_colors:
            return self._tile_colors[name]
        frames = self.tile_frames(name)
        if not frames:
            return fallback
        frame = frames[0]
        w, h = frame.get_size()
        r = g = b = n = 0
        for y in range(0, h, 3):
            for x in range(0, w, 3):
                c = frame.get_at((x, y))
                r += c.r
                g += c.g
                b += c.b
                n += 1
        color = (r // max(1, n), g // max(1, n), b // max(1, n))
        self._tile_colors[name] = color
        return color

    def prop_frames(self, name):
        cache_key = ("prop", name)
        cached = self._tile_cache.get(cache_key)
        if cached is not None:
            return cached
        meta = self.manifest.get("props")
        if not meta:
            return []
        slots = meta.get("index", {}).get(name, [])
        sheet = self.image(meta["sheet"])
        if sheet is None:
            return []
        fw, fh = meta.get("frame", [32, 32])
        frames = []
        for c, r in slots:
            frame = self._sub(sheet, c * fw, r * fh, fw, fh)
            if frame is not None:
                frames.append(frame)
        self._tile_cache[cache_key] = frames
        return frames

    def prop(self, name, time=0.0):
        frames = self.prop_frames(name)
        if not frames:
            return None
        if len(frames) == 1:
            return frames[0]
        return frames[int(time * 6) % len(frames)]

    # ------------------------------------------------------------------
    # Снаряды и эффекты
    # ------------------------------------------------------------------
    def projectile_frames(self, kind, color=None):
        cache_key = ("proj", kind, tuple(color) if color else None)
        cached = self._tint_cache.get(cache_key)
        if cached is not None:
            return cached
        meta = self.manifest.get("projectiles")
        if not meta:
            return []
        clip = meta.get("clips", {}).get(kind)
        if not clip:
            clip = meta.get("clips", {}).get("orb")
            kind = "orb"
        if not clip:
            return []
        sheet = self.image(meta["sheet"])
        if sheet is None:
            return []
        fw, fh = meta.get("frame", [24, 24])
        frames = []
        for i in range(int(clip.get("count", 1))):
            frame = self._sub(sheet, i * fw, int(clip["row"]) * fh, fw, fh)
            if frame is None:
                continue
            if color is not None and kind == "orb":
                frame = _tint(frame, color)
            frames.append(frame)
        self._tint_cache[cache_key] = frames
        return frames

    def projectile_frame(self, kind, elapsed, color=None):
        frames = self.projectile_frames(kind, color)
        if not frames:
            return None
        meta = self.manifest.get("projectiles", {})
        clip = meta.get("clips", {}).get(kind, {})
        fps = float(clip.get("fps", 12))
        return frames[int(max(0.0, elapsed) * fps) % len(frames)]

    def effect_frames(self, kind):
        cache_key = ("fx", kind)
        cached = self._frames_cache.get(cache_key)
        if cached is not None:
            return cached
        meta = self.manifest.get("effects")
        if not meta:
            return []
        clip = meta.get("clips", {}).get(kind)
        if not clip:
            return []
        sheet = self.image(meta["sheet"])
        if sheet is None:
            return []
        fw, fh = meta.get("frame", [64, 64])
        frames = []
        for i in range(int(clip.get("count", 1))):
            frame = self._sub(sheet, i * fw, int(clip["row"]) * fh, fw, fh)
            if frame is not None:
                frames.append(frame)
        self._frames_cache[cache_key] = frames
        return frames

    def effect_frame(self, kind, progress):
        frames = self.effect_frames(kind)
        if not frames:
            return None
        idx = int(max(0.0, min(0.999, progress)) * len(frames))
        return frames[min(idx, len(frames) - 1)]

    # ------------------------------------------------------------------
    # Иконки
    # ------------------------------------------------------------------
    def _grid_frame(self, group, index_name):
        cache_key = (group, index_name)
        if cache_key in self._grid_cache:
            return self._grid_cache[cache_key]
        meta = self.manifest.get(group)
        if not meta:
            self._grid_cache[cache_key] = None
            return None
        pos = meta.get("index", {}).get(index_name)
        if pos is None:
            self._grid_cache[cache_key] = None
            return None
        sheet = self.image(meta["sheet"])
        if sheet is None:
            self._grid_cache[cache_key] = None
            return None
        c, r = pos
        fw, fh = meta.get("frame", [32, 32])
        frame = self._sub(sheet, c * fw, r * fh, fw, fh)
        self._grid_cache[cache_key] = frame
        return frame

    def named_icon(self, name):
        """Иконка предмета по имени из листа icons (gold, potion, sword...)."""
        return self._grid_frame("icons", name)

    def item_icon(self, item):
        key = getattr(item, "item_id", "generic")
        index = self.manifest.get("icons", {}).get("index", {})

        if key == "gold":
            return self.named_icon("gold")

        # Ищем самый длинный ключ, совпадающий с началом item_id:
        # bow_wood -> bow, helmet_leather -> helmet_leather.
        best = None
        for prefix in ITEM_ID_ICONS:
            if key == prefix or key.startswith(prefix + "_"):
                if best is None or len(prefix) > len(best):
                    best = prefix
        if best is not None:
            icon_key = ITEM_ID_ICONS[best]
            if icon_key in index:
                return self.named_icon(icon_key)

        item_type = getattr(item, "item_type", None)
        if item_type is not None:
            type_value = item_type.value
            icon_key = ITEM_TYPE_ICONS.get(type_value)
            if type_value == "resource" and key in index:
                icon_key = key
            if icon_key not in index:
                icon_key = "generic"
            return self.named_icon(icon_key)

        return self.named_icon("generic")

    def ability_icon(self, ability_id):
        return self._grid_frame("abilities", ability_id)

    def world_icon(self, name):
        return self._grid_frame("world_icons", name)

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------
    def ui(self, name):
        meta = self.manifest.get("ui", {})
        relpath = meta.get(name)
        if not relpath:
            return None
        return self.image(relpath)

    def scaled(self, surface, width, height=None):
        if surface is None:
            return None
        height = width if height is None else height
        key = (id(surface), int(width), int(height))
        cached = self._scale_cache.get(key)
        if cached is not None:
            return cached
        result = pg.transform.scale(surface, (max(1, int(width)), max(1, int(height))))
        self._scale_cache[key] = result
        return result

    def draw_panel(self, target, rect: pg.Rect, alpha=255):
        panel = self.ui("panel")
        if panel is None:
            pg.draw.rect(target, (22, 24, 36), rect)
            pg.draw.rect(target, (150, 128, 80), rect, 2)
            return
        rect = pg.Rect(rect)
        corner = 12
        w, h = panel.get_size()
        if rect.w < corner * 2 + 2 or rect.h < corner * 2 + 2:
            target.blit(pg.transform.smoothscale(panel, rect.size), rect.topleft)
            return
        if alpha < 255:
            panel = panel.copy()
            panel.set_alpha(alpha)
        # 9-slice
        xs = [(0, corner, rect.x, corner), (corner, w - corner * 2, rect.x + corner, rect.w - corner * 2), (w - corner, corner, rect.right - corner, corner)]
        ys = [(0, corner, rect.y, corner), (corner, h - corner * 2, rect.y + corner, rect.h - corner * 2), (h - corner, corner, rect.bottom - corner, corner)]
        for sx, sw, dx, dw in xs:
            for sy, sh, dy, dh in ys:
                part = panel.subsurface(pg.Rect(sx, sy, sw, sh))
                if (dw, dh) != (sw, sh):
                    part = pg.transform.smoothscale(part, (max(1, dw), max(1, dh)))
                target.blit(part, (dx, dy))

    def draw_bar(self, target, rect, ratio, kind):
        rect = pg.Rect(rect)
        bg = self.ui("bar_bg")
        fill = self.ui(kind)
        if bg is None or fill is None:
            pg.draw.rect(target, (30, 30, 30), rect)
            inner = rect.inflate(-4, -4)
            inner.w = int(inner.w * max(0.0, min(1.0, ratio)))
            if inner.w > 0:
                pg.draw.rect(target, (200, 80, 80), inner)
            return
        target.blit(pg.transform.smoothscale(bg, rect.size), rect.topleft)
        ratio = max(0.0, min(1.0, ratio))
        if ratio > 0:
            inner = pg.Rect(rect.x + 2, rect.y + 2, max(1, int((rect.w - 4) * ratio)), rect.h - 4)
            fill_scaled = pg.transform.smoothscale(fill, (inner.w, inner.h))
            target.blit(fill_scaled, inner.topleft)


assets = AssetManager()
