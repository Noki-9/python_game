import math
import random

import pygame as pg

from core.camera import Camera
from core.config import TILE_SIZE, screen
from core.scene_manager import Scene
from models.player import Player
from ui.character_ui import CharacterUI
from ui.dialogue_ui import DialogueUI
from ui.inventory_ui import InventoryUI
from ui.skills_ui import SkillsUI
from world.item_generator import roll_random_equipment
from world.loot import GOLD, ITEMS_REGISTRY
from world.npc_gen import spawn_npcs
from world.spawn import spawn_animals, spawn_enemies

COLORS = {
    "grass": (100, 180, 90),
    "sand": (230, 210, 140),
    "snow": (230, 240, 250),
    "water": (60, 100, 200),
    "rock": (110, 100, 90),
    "tree": (50, 120, 60),
    "cactus": (70, 140, 80),
    "road": (170, 150, 110),
    "door": (130, 90, 60),
    "house_wall": (120, 100, 80),
    "house_floor": (160, 130, 100),
    "stone": (150, 150, 160),
}

PICKUP_RADIUS = 44
NPC_INTERACT_RADIUS = 64


class LocalScene(Scene):
    def __init__(self, manager, segment):
        self.manager = manager
        self.segment = segment
        self.map = None
        self.player = None
        self.enemies = []
        self.animals = []
        self.npcs = []
        self.dropped_items = []
        self.return_pos = None
        self.notifications = []

        self._font_hint = pg.font.SysFont(None, 22)
        self._font_label = pg.font.SysFont(None, 24)
        self._font_hud = pg.font.SysFont(None, 18)
        self._font_npc = pg.font.SysFont(None, 16)

    def _get_neighbors(self):
        world = getattr(self.manager, "world", None)
        if world is None:
            return None
        gx, gy = self.segment.gx, self.segment.gy
        result = {}
        for name, (dx, dy) in (
            ("n", (0, -1)),
            ("s", (0, 1)),
            ("w", (-1, 0)),
            ("e", (1, 0)),
        ):
            seg = world.get(gx + dx, gy + dy)
            result[name] = seg.biome if seg else None
        return result

    def on_enter(self, return_pos=None, entry_from=None):
        self.return_pos = return_pos
        self.notifications = []
        self.dropped_items = []

        state = self.manager.player_state
        state.restore()

        neighbors = self._get_neighbors()
        self.map = self.segment.get_local_map(
            neighbors=neighbors,
            player_state=state,
        )

        tx, ty = self.map.spawn_tile
        px = tx * TILE_SIZE
        py = ty * TILE_SIZE
        self.player = Player(
            px,
            py,
            TILE_SIZE - 8,
            TILE_SIZE - 8,
            100,
            300,
            state.class_def.color,
            state=state,
        )

        sw, sh = screen.get_size()
        self.camera = Camera(sw, sh)
        self.map_w_px = self.map.width * TILE_SIZE
        self.map_h_px = self.map.height * TILE_SIZE

        if not self.segment.cleared:
            self.enemies = spawn_enemies(
                self.map,
                self.segment.biome,
                self.segment.location_type,
                self.segment.seed,
                level=state.level,
            )
        else:
            self.enemies = []

        self.animals = spawn_animals(
            self.map,
            self.segment.biome,
            self.segment.location_type,
            self.segment.seed,
        )

        if self.segment.location_type.is_settlement:
            is_start = self.segment.location_type.value == "starting_village"
            self.npcs = spawn_npcs(self.map, self.segment.seed, is_starting=is_start)
        else:
            self.npcs = []

        if self.segment.cleared:
            self.notifications.append(("Локация уже зачищена", 3.0))

    def on_exit(self):
        self.segment.reset_if_unfinished()

    # -------- Ввод --------
    def handle_event(self, event):
        if event.type == pg.KEYDOWN:
            if event.key == pg.K_ESCAPE:
                from scenes.world_scene import WorldScene

                self.manager.switch(
                    WorldScene(self.manager, self.manager.world),
                    world_pos=self.return_pos,
                    mode="play",
                )
                return
            if event.key == pg.K_i:
                self.manager.push_ui(
                    InventoryUI(screen.get_size(), self.manager.player_state)
                )
                return
            if event.key == pg.K_c:
                self.manager.push_ui(
                    CharacterUI(screen.get_size(), self.manager.player_state)
                )
                return
            if event.key == pg.K_k:
                self.manager.push_ui(
                    SkillsUI(screen.get_size(), self.manager.player_state)
                )
                return
            if event.key == pg.K_e:
                npc = self._find_npc_near()
                if npc is not None:
                    self.manager.push_ui(
                        DialogueUI(screen.get_size(), self.manager.player_state, npc)
                    )
                else:
                    self._try_interact()
            elif event.key == pg.K_SPACE:
                self._player_attack()

        elif event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
            self._player_attack()

    def _find_npc_near(self):
        px = self.player.x + self.player.rect_x / 2
        py = self.player.y + self.player.rect_y / 2
        best = None
        best_d = NPC_INTERACT_RADIUS
        for npc in self.npcs:
            nx = npc.x + npc.rect_x / 2
            ny = npc.y + npc.rect_y / 2
            d = math.hypot(nx - px, ny - py)
            if d < best_d:
                best = npc
                best_d = d
        return best

    def _try_interact(self):
        if not self.segment.location_type.is_quest:
            return
        if self.segment.cleared:
            return
        cx = (self.map.width // 2) * TILE_SIZE
        cy = (self.map.height // 2) * TILE_SIZE
        px = self.player.x + self.player.rect_x / 2
        py = self.player.y + self.player.rect_y / 2
        dist2 = (px - cx) ** 2 + (py - cy) ** 2
        if dist2 < (TILE_SIZE * 3) ** 2:
            self._complete_quest()

    def _player_attack(self):
        targets = [e for e in self.enemies if e.is_alive()] + [
            a for a in self.animals if a.is_alive()
        ]
        result = self.player.try_attack(targets)
        if result is None:
            return
        killed, target, is_crit = result
        if is_crit:
            self.notifications.append(("КРИТ!", 1.0))
        if killed:
            self._on_enemy_killed(target)

    def _on_enemy_killed(self, enemy):
        state = self.manager.player_state
        rng = random.Random(enemy.loot_rng_seed)
        loot = enemy.drop_loot(rng)
        for item_id, count in loot.items():
            template = ITEMS_REGISTRY.get(item_id)
            if not template:
                continue
            item = template.copy()
            item.count = count
            self.dropped_items.append((item, enemy.x, enemy.y))
        if rng.random() < 0.20:
            equip = roll_random_equipment(rng)
            if equip:
                self.dropped_items.append((equip, enemy.x, enemy.y))
        state.add_xp(enemy.xp_reward)
        self.notifications.append((f"+{enemy.xp_reward} XP", 1.5))
        self._check_quest_completion()

    def _check_quest_completion(self):
        if not self.segment.location_type.is_quest:
            return
        if self.segment.cleared:
            return
        if not self.enemies:
            return
        if any(e.is_alive() for e in self.enemies):
            return
        self._complete_quest()

    def _complete_quest(self):
        if self.segment.cleared:
            return
        self.segment.cleared = True
        if self.segment.poi:
            self.segment.poi.cleared = True
        state = self.manager.player_state
        state.add_gold(100)
        state.add_xp(250)
        self.notifications.append(("Локация зачищена! +100 золота, +250 XP", 4.0))

    # -------- Update --------
    def update(self, dt):
        if not self.player.is_alive():
            self._on_player_death()
            return

        nearby = self.map.walls_near(
            self.player.x + self.player.rect_x / 2,
            self.player.y + self.player.rect_y / 2,
            radius_px=96,
        )
        self.player.update(
            dt, walls=nearby, map_w_px=self.map_w_px, map_h_px=self.map_h_px
        )
        self.camera.follow(self.player, self.map_w_px, self.map_h_px)

        for e in self.enemies:
            if not e.is_alive():
                continue
            walls = self.map.walls_near(
                e.x + e.rect_x / 2, e.y + e.rect_y / 2, radius_px=64
            )
            e.update(dt, self.player, walls)

        for a in self.animals:
            if not a.is_alive():
                continue
            walls = self.map.walls_near(
                a.x + a.rect_x / 2, a.y + a.rect_y / 2, radius_px=64
            )
            a.update(dt, self.player, walls)

        self._collect_drops()

        if not self.player.is_alive():
            self._on_player_death()
            return

        self.notifications = [
            (txt, t - dt) for txt, t in self.notifications if t - dt > 0
        ]

    def _collect_drops(self):
        state = self.manager.player_state
        remaining = []
        for item, x, y in self.dropped_items:
            dx = self.player.x - x
            dy = self.player.y - y
            if math.hypot(dx, dy) < PICKUP_RADIUS:
                if item.item_id == GOLD:
                    state.add_gold(item.count)
                else:
                    state.add_item(item)
                self.notifications.append(
                    (
                        f"+{item.count} {item.name}"
                        if item.count > 1
                        else f"+{item.name}",
                        1.5,
                    )
                )
            else:
                remaining.append((item, x, y))
        self.dropped_items = remaining

    def _on_player_death(self):
        state = self.manager.player_state
        lost = state.gold // 5
        state.gold -= lost
        state.hp = state.max_hp
        state.restore()
        from scenes.world_scene import WorldScene

        self.manager.switch(
            WorldScene(self.manager, self.manager.world),
            world_pos=(self.manager.world.start_gx, self.manager.world.start_gy),
            mode="play",
        )

    # -------- Draw --------
    def draw(self, screen):
        screen.fill((20, 20, 20))

        tx0, ty0, tx1, ty1 = self.camera.visible_tile_range(TILE_SIZE)
        tx1 = min(tx1, self.map.width)
        ty1 = min(ty1, self.map.height)

        tiles = self.map.tiles
        for ty in range(ty0, ty1):
            row = tiles[ty]
            sy = ty * TILE_SIZE - int(self.camera.y)
            for tx in range(tx0, tx1):
                sx = tx * TILE_SIZE - int(self.camera.x)
                color = COLORS.get(row[tx], (255, 0, 255))
                pg.draw.rect(screen, color, (sx, sy, TILE_SIZE, TILE_SIZE))

        self._draw_quest_marker(screen)

        for a in self.animals:
            if a.is_alive():
                a.draw(screen, self.camera)
        for e in self.enemies:
            if e.is_alive():
                e.draw(screen, self.camera)

        for npc in self.npcs:
            npc.draw(screen, self.camera, self._font_npc)

        for item, x, y in self.dropped_items:
            sx, sy = self.camera.apply(x + 12, y + 12)
            color = item.rarity.color if item.is_equipment else item.icon_color
            pg.draw.circle(screen, color, (sx, sy), 5)
            pg.draw.circle(screen, (20, 20, 20), (sx, sy), 5, 1)

        px, py = self.camera.apply(self.player.x, self.player.y)
        pg.draw.rect(
            screen,
            self.player.texture,
            (px, py, self.player.rect_x, self.player.rect_y),
        )

        self._draw_label(screen)
        self._draw_hud(screen)
        self._draw_notifications(screen)
        self._draw_hint(screen)

    def _draw_quest_marker(self, screen):
        if not self.segment.location_type.is_quest:
            return
        cx = (self.map.width // 2) * TILE_SIZE
        cy = (self.map.height // 2) * TILE_SIZE
        sx, sy = self.camera.apply(cx, cy)
        color = (100, 100, 100) if self.segment.cleared else (230, 200, 80)
        center = (sx + TILE_SIZE // 2, sy + TILE_SIZE // 2)
        pg.draw.circle(screen, color, center, 22, 2)
        pg.draw.circle(screen, color, center, 8)

    def _draw_label(self, screen):
        text = self.segment.location_type.display_name
        if self.segment.poi:
            text = f"{self.segment.poi.name} — {text}"
        surf = self._font_label.render(text, True, (240, 240, 240))
        bg = pg.Surface((surf.get_width() + 16, surf.get_height() + 8))
        bg.set_alpha(160)
        bg.fill((0, 0, 0))
        screen.blit(bg, (10, 10))
        screen.blit(surf, (18, 14))

    def _draw_hud(self, screen):
        s = self.manager.player_state
        y = 50
        self._bar(screen, 10, y, 200, 16, s.hp_ratio, (220, 60, 60))
        surf = self._font_hud.render(f"HP: {s.hp}/{s.max_hp}", True, (255, 255, 255))
        screen.blit(surf, (216, y - 1))

        y += 20
        xp_r = s.xp / s.xp_to_next if s.xp_to_next else 0
        self._bar(screen, 10, y, 200, 14, xp_r, (90, 180, 230))
        surf = self._font_hud.render(
            f"Ур. {s.level}  XP: {s.xp}/{s.xp_to_next}", True, (255, 255, 255)
        )
        screen.blit(surf, (216, y - 1))

        y += 18
        surf = self._font_hud.render(f"Золото: {s.gold}", True, (240, 220, 100))
        screen.blit(surf, (10, y))

        y += 18
        if s.stat_points > 0 or s.skill_points > 0:
            surf = self._font_hud.render(
                f"Очки: статы {s.stat_points} / навыки {s.skill_points}  [C][K]",
                True,
                (200, 220, 250),
            )
            screen.blit(surf, (10, y))

    def _bar(self, screen, x, y, w, h, ratio, color):
        pg.draw.rect(screen, (30, 30, 30), (x, y, w, h))
        fill = int((w - 4) * max(0.0, min(1.0, ratio)))
        if fill > 0:
            pg.draw.rect(screen, color, (x + 2, y + 2, fill, h - 4))
        pg.draw.rect(screen, (200, 200, 200), (x, y, w, h), 1)

    def _draw_notifications(self, screen):
        y = 140
        for txt, t in self.notifications:
            alpha = 255 if t >= 1.0 else int(255 * t)
            surf = self._font_hint.render(txt, True, (255, 240, 100))
            surf.set_alpha(alpha)
            screen.blit(surf, (20, y))
            y += 24

    def _draw_hint(self, screen):
        npc = self._find_npc_near() if self.npcs else None
        if npc:
            text = f"E — поговорить с {npc.name} | ЛКМ — атака | I C K | Esc"
        elif self.segment.location_type.is_quest and not self.segment.cleared:
            text = "WASD | ЛКМ/Пробел — атака | E — взаимодействие | I C K | Esc"
        else:
            text = "WASD | ЛКМ/Пробел — атака | I C K | Esc"
        surf = self._font_hint.render(text, True, (230, 230, 230))
        bg = pg.Surface((surf.get_width() + 16, surf.get_height() + 8))
        bg.set_alpha(160)
        bg.fill((0, 0, 0))
        x = 10
        y = screen.get_height() - surf.get_height() - 14
        screen.blit(bg, (x, y))
        screen.blit(surf, (x + 8, y + 4))
