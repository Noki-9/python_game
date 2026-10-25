import math
import random

import pygame as pg

from core.abilities import get_abilities_for_class, get_ability_for_key
from core.camera import Camera
from core.config import TILE_SIZE, screen
from core.scene_manager import Scene
from models.player import Player
from models.projectile import Projectile
from ui.character_ui import CharacterUI
from ui.dialogue_ui import DialogueUI
from ui.inventory_ui import InventoryUI
from ui.quest_log_ui import QuestLogUI
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
MINIMAP_SIZE = 180


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
        self.projectiles = []
        self.visual_effects = []  # [x, y, radius, color, t_left, t_max]
        self.return_pos = None
        self.notifications = []
        self._minimap_cache = None

        self._font_hint = pg.font.SysFont(None, 22)
        self._font_label = pg.font.SysFont(None, 24)
        self._font_hud = pg.font.SysFont(None, 18)
        self._font_npc = pg.font.SysFont(None, 16)
        self._font_key = pg.font.SysFont(None, 20)

    # ================= Жизненный цикл =================
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
        self.projectiles = []
        self.visual_effects = []
        self._minimap_cache = None

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

        self._sync_fetch_quests()
        self._build_minimap()

        if self.segment.cleared:
            self.notifications.append(("Локация уже зачищена", 3.0))

    def on_exit(self):
        self.segment.reset_if_unfinished()

    # ================= Мини-карта: построение =================
    def _build_minimap(self):
        """1 раз при входе: 250×250 тайлов → 180×180. Дальше только blit."""
        base = pg.Surface((self.map.width, self.map.height))
        base.fill((10, 10, 15))
        tiles = self.map.tiles
        for ty in range(self.map.height):
            row = tiles[ty]
            for tx in range(self.map.width):
                base.set_at((tx, ty), COLORS.get(row[tx], (255, 0, 255)))
        self._minimap_cache = pg.transform.scale(base, (MINIMAP_SIZE, MINIMAP_SIZE))

    # ================= Ввод =================
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
            if event.key == pg.K_j:
                self.manager.push_ui(
                    QuestLogUI(screen.get_size(), self.manager.player_state)
                )
                return
            if event.key == pg.K_q:
                self._cast_ability("Q")
                return
            if event.key == pg.K_f:
                self._cast_ability("F")
                return
            if event.key == pg.K_r:
                self._cast_ability("R")
                return
            if event.key == pg.K_e:
                npc = self._find_npc_near()
                if npc is not None:
                    self.manager.push_ui(
                        DialogueUI(
                            screen.get_size(),
                            self.manager.player_state,
                            npc,
                            world=self.manager.world,
                        )
                    )
                else:
                    self._try_interact()
            elif event.key == pg.K_SPACE:
                self._player_attack()

        elif event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
            self._player_attack()

    # ================= Умения =================
    def _cast_ability(self, key):
        s = self.manager.player_state
        ability = get_ability_for_key(s.class_id, key)
        if ability is None:
            return
        if s.ability_cooldowns.get(ability.ability_id, 0) > 0:
            return
        if s.mana < ability.mana_cost:
            self.notifications.append(("Не хватает маны", 1.0))
            return
        if not s.try_spend_ability(ability):
            return

        if ability.is_projectile:
            self._cast_projectile(ability)
        elif ability.is_aoe_at_cursor:
            self._cast_aoe_at_cursor(ability)
        elif ability.is_aoe_self:
            self._cast_aoe_self(ability)
        elif ability.is_single_target:
            self._cast_single_target(ability)

    def _cast_projectile(self, ability):
        mx, my = pg.mouse.get_pos()
        wx = mx + self.camera.x
        wy = my + self.camera.y
        pcx = self.player.x + self.player.rect_x / 2
        pcy = self.player.y + self.player.rect_y / 2
        base_angle = math.atan2(wy - pcy, wx - pcx)

        count = ability.projectile_count
        spread_rad = math.radians(ability.projectile_spread)
        damage = int(self.manager.player_state.attack_damage * ability.damage_mult)
        lifetime = ability.range / ability.projectile_speed

        for i in range(count):
            if count > 1:
                offset = -spread_rad / 2 + (spread_rad / (count - 1)) * i
            else:
                offset = 0.0
            angle = base_angle + offset
            vx = math.cos(angle) * ability.projectile_speed
            vy = math.sin(angle) * ability.projectile_speed
            self.projectiles.append(
                Projectile(
                    x=pcx,
                    y=pcy,
                    vx=vx,
                    vy=vy,
                    damage=damage,
                    radius=6,
                    color=ability.color,
                    lifetime=lifetime,
                    aoe_radius=ability.aoe_radius,
                )
            )

    def _cast_aoe_at_cursor(self, ability):
        mx, my = pg.mouse.get_pos()
        wx = mx + self.camera.x
        wy = my + self.camera.y
        pcx = self.player.x + self.player.rect_x / 2
        pcy = self.player.y + self.player.rect_y / 2

        dist = math.hypot(wx - pcx, wy - pcy)
        if dist > ability.range:
            wx = pcx + (wx - pcx) / dist * ability.range
            wy = pcy + (wy - pcy) / dist * ability.range

        radius = ability.aoe_radius
        damage = int(self.manager.player_state.attack_damage * ability.damage_mult)

        for target_list in (self.enemies, self.animals):
            for t in target_list:
                if not t.is_alive():
                    continue
                ex = t.x + t.rect_x / 2
                ey = t.y + t.rect_y / 2
                if math.hypot(ex - wx, ey - wy) <= radius:
                    if t.take_damage(damage):
                        self._on_enemy_killed(t)

        self.visual_effects.append([wx, wy, radius, ability.color, 0.5, 0.5])

    def _cast_aoe_self(self, ability):
        pcx = self.player.x + self.player.rect_x / 2
        pcy = self.player.y + self.player.rect_y / 2
        radius = ability.aoe_radius
        damage = int(self.manager.player_state.attack_damage * ability.damage_mult)

        for target_list in (self.enemies, self.animals):
            for t in target_list:
                if not t.is_alive():
                    continue
                ex = t.x + t.rect_x / 2
                ey = t.y + t.rect_y / 2
                if math.hypot(ex - pcx, ey - pcy) <= radius:
                    if t.take_damage(damage):
                        self._on_enemy_killed(t)

        if ability.heal > 0:
            self.manager.player_state.heal(ability.heal)
            self.notifications.append((f"+{ability.heal} HP", 1.0))

        self.visual_effects.append([pcx, pcy, radius, ability.color, 0.35, 0.35])

    def _cast_single_target(self, ability):
        pcx = self.player.x + self.player.rect_x / 2
        pcy = self.player.y + self.player.rect_y / 2
        best = None
        best_d = float(ability.range)
        for e in self.enemies:
            if not e.is_alive():
                continue
            ex = e.x + e.rect_x / 2
            ey = e.y + e.rect_y / 2
            d = math.hypot(ex - pcx, ey - pcy)
            if d <= best_d:
                best = e
                best_d = d
        if best is None:
            self.notifications.append(("Нет цели", 1.0))
            return

        damage = int(self.manager.player_state.attack_damage * ability.damage_mult)
        if best.take_damage(damage):
            self._on_enemy_killed(best)

        self.visual_effects.append(
            [
                best.x + best.rect_x / 2,
                best.y + best.rect_y / 2,
                30,
                ability.color,
                0.25,
                0.25,
            ]
        )

    # ================= Атака =================
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

        finished = state.quest_log.notify_kill(enemy.enemy_id)
        self._on_quests_completed(finished)
        self._check_quest_completion()

    def _on_quests_completed(self, finished):
        state = self.manager.player_state
        for q in finished:
            state.grant_quest_reward(q)
            self.notifications.append(
                (
                    f"Квест выполнен: {q.title} "
                    f"(+{q.reward_gold} зол., +{q.reward_xp} XP)",
                    4.0,
                )
            )

    def _sync_fetch_quests(self):
        state = self.manager.player_state
        finished = state.quest_log.notify_inventory(state.inventory)
        self._on_quests_completed(finished)

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
        if self.segment.poi:
            finished = state.quest_log.notify_location_cleared(self.segment.poi.name)
            self._on_quests_completed(finished)

    def _try_interact(self):
        if not self.segment.location_type.is_quest:
            return
        if self.segment.cleared:
            return
        cx = (self.map.width // 2) * TILE_SIZE
        cy = (self.map.height // 2) * TILE_SIZE
        px = self.player.x + self.player.rect_x / 2
        py = self.player.y + self.player.rect_y / 2
        if (px - cx) ** 2 + (py - cy) ** 2 < (TILE_SIZE * 3) ** 2:
            self._complete_quest()

    def _find_npc_near(self):
        px = self.player.x + self.player.rect_x / 2
        py = self.player.y + self.player.rect_y / 2
        best = None
        best_d = NPC_INTERACT_RADIUS
        for npc in self.npcs:
            d = math.hypot(npc.x + npc.rect_x / 2 - px, npc.y + npc.rect_y / 2 - py)
            if d < best_d:
                best = npc
                best_d = d
        return best

    # ================= Update =================
    def update(self, dt):
        if not self.player.is_alive():
            self._on_player_death()
            return

        state = self.manager.player_state
        state.tick_ability_cooldowns(dt)
        state.regen_mana(dt)

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

        for p in self.projectiles:
            killed_list = p.update(dt, self.enemies, self.animals, self.map, TILE_SIZE)
            for target in killed_list:
                self._on_enemy_killed(target)
        self.projectiles = [p for p in self.projectiles if p.alive]

        for eff in self.visual_effects:
            eff[4] -= dt
        self.visual_effects = [e for e in self.visual_effects if e[4] > 0]

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
        had_fetch = False
        for item, x, y in self.dropped_items:
            dx = self.player.x - x
            dy = self.player.y - y
            if math.hypot(dx, dy) < PICKUP_RADIUS:
                if item.item_id == GOLD:
                    state.add_gold(item.count)
                else:
                    state.add_item(item)
                    had_fetch = True
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
        if had_fetch:
            self._sync_fetch_quests()

    def _on_player_death(self):
        state = self.manager.player_state
        lost = state.gold // 5
        state.gold -= lost
        state.hp = state.max_hp
        state.stamina = state.max_stamina
        state.mana = float(state.max_mana)
        from scenes.world_scene import WorldScene

        self.manager.switch(
            WorldScene(self.manager, self.manager.world),
            world_pos=(self.manager.world.start_gx, self.manager.world.start_gy),
            mode="play",
        )

    # ================= Draw =================
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

        for p in self.projectiles:
            p.draw(screen, self.camera)

        self._draw_visual_effects(screen)

        px, py = self.camera.apply(self.player.x, self.player.y)
        pg.draw.rect(
            screen,
            self.player.texture,
            (px, py, self.player.rect_x, self.player.rect_y),
        )

        self._draw_label(screen)
        self._draw_hud(screen)
        self._draw_active_quests(screen)
        self._draw_ability_bar(screen)
        self._draw_minimap(screen)
        self._draw_notifications(screen)
        self._draw_hint(screen)

    # ---------- Отрисовка эффектов ----------
    def _draw_visual_effects(self, screen):
        for x, y, radius, color, t_left, t_max in self.visual_effects:
            sx, sy = self.camera.apply(x, y)
            alpha = int(255 * (t_left / t_max))
            surf = pg.Surface((radius * 2 + 4, radius * 2 + 4), pg.SRCALPHA)
            c = (color[0], color[1], color[2], max(0, alpha // 2))
            pg.draw.circle(surf, c, (radius + 2, radius + 2), radius)
            c2 = (color[0], color[1], color[2], max(0, alpha))
            pg.draw.circle(surf, c2, (radius + 2, radius + 2), radius, 2)
            screen.blit(surf, (sx - radius - 2, sy - radius - 2))

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
        self._bar(screen, 10, y, 200, 12, s.mana_ratio, (80, 160, 240))
        surf = self._font_hud.render(
            f"MP: {int(s.mana)}/{s.max_mana}", True, (255, 255, 255)
        )
        screen.blit(surf, (216, y - 1))

        y += 18
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

    def _draw_active_quests(self, screen):
        quests = self.manager.player_state.quest_log.active()
        if not quests:
            return
        x = 10
        y = 200
        title = self._font_hud.render(
            f"Активные квесты ({len(quests)})  [J]", True, (240, 220, 100)
        )
        screen.blit(title, (x, y))
        y += 20
        for q in quests[:3]:
            text = f"• {q.title}: {q.objective.progress_str}"
            surf = self._font_hud.render(text, True, (220, 220, 200))
            screen.blit(surf, (x + 4, y))
            y += 18

    def _bar(self, screen, x, y, w, h, ratio, color):
        pg.draw.rect(screen, (30, 30, 30), (x, y, w, h))
        fill = int((w - 4) * max(0.0, min(1.0, ratio)))
        if fill > 0:
            pg.draw.rect(screen, color, (x + 2, y + 2, fill, h - 4))
        pg.draw.rect(screen, (200, 200, 200), (x, y, w, h), 1)

    def _draw_ability_bar(self, screen):
        s = self.manager.player_state
        abilities = get_abilities_for_class(s.class_id)
        if not abilities:
            return

        slot = 56
        gap = 8
        total = len(abilities) * slot + (len(abilities) - 1) * gap
        x_start = (screen.get_width() - total) // 2
        y = screen.get_height() - slot - 70

        mb_h = 8
        mb_y = y - 16
        pg.draw.rect(screen, (30, 30, 40), (x_start, mb_y, total, mb_h))
        fw = int((total - 2) * s.mana_ratio)
        if fw > 0:
            pg.draw.rect(screen, (80, 160, 240), (x_start + 1, mb_y + 1, fw, mb_h - 2))
        pg.draw.rect(screen, (100, 100, 120), (x_start, mb_y, total, mb_h), 1)

        for i, ab in enumerate(abilities):
            sx = x_start + i * (slot + gap)
            rect = pg.Rect(sx, y, slot, slot)
            cd = s.get_cooldown_ratio(ab)
            ready = cd >= 1.0 and s.mana >= ab.mana_cost

            bg = (50, 60, 70) if ready else (30, 30, 40)
            border = ab.color if ready else (80, 80, 90)
            pg.draw.rect(screen, bg, rect)
            pg.draw.rect(screen, border, rect, 2)

            pg.draw.circle(screen, ab.color, (rect.centerx, rect.centery), 18)
            pg.draw.circle(screen, (30, 30, 30), (rect.centerx, rect.centery), 18, 1)

            k = self._font_key.render(ab.key, True, (255, 255, 255))
            screen.blit(k, (rect.x + 4, rect.y + 1))

            m = self._font_hud.render(str(ab.mana_cost), True, (120, 200, 250))
            screen.blit(m, (rect.right - m.get_width() - 4, rect.y + 2))

            if cd < 1.0:
                cd_h = int(slot * (1 - cd))
                ov = pg.Surface((slot, cd_h))
                ov.set_alpha(180)
                ov.fill((0, 0, 0))
                screen.blit(ov, (sx, y + slot - cd_h))

            if s.mana < ab.mana_cost:
                tint = pg.Surface((slot, slot))
                tint.set_alpha(70)
                tint.fill((200, 40, 40))
                screen.blit(tint, (sx, y))

    # ---------- Мини-карта ----------
    def _draw_minimap(self, screen):
        if self._minimap_cache is None:
            return

        sw, _ = screen.get_size()
        mm_x = sw - MINIMAP_SIZE - 10
        mm_y = 10

        screen.blit(self._minimap_cache, (mm_x, mm_y))
        pg.draw.rect(
            screen, (150, 150, 170), (mm_x, mm_y, MINIMAP_SIZE, MINIMAP_SIZE), 2
        )

        scale_x = MINIMAP_SIZE / self.map_w_px
        scale_y = MINIMAP_SIZE / self.map_h_px

        # Квест-алтарь
        if self.segment.location_type.is_quest:
            cx = (self.map.width // 2) * TILE_SIZE
            cy = (self.map.height // 2) * TILE_SIZE
            qx = mm_x + int(cx * scale_x)
            qy = mm_y + int(cy * scale_y)
            color = (100, 100, 100) if self.segment.cleared else (230, 200, 80)
            pg.draw.circle(screen, color, (qx, qy), 4)
            pg.draw.circle(screen, (20, 20, 20), (qx, qy), 4, 1)

        # Животные
        for a in self.animals:
            if not a.is_alive():
                continue
            ax = mm_x + int((a.x + a.rect_x / 2) * scale_x)
            ay = mm_y + int((a.y + a.rect_y / 2) * scale_y)
            pg.draw.circle(screen, (240, 200, 80), (ax, ay), 2)

        # Враги
        for e in self.enemies:
            if not e.is_alive():
                continue
            ex = mm_x + int((e.x + e.rect_x / 2) * scale_x)
            ey = mm_y + int((e.y + e.rect_y / 2) * scale_y)
            pg.draw.circle(screen, (220, 60, 60), (ex, ey), 2)

        # NPC
        for npc in self.npcs:
            nx = mm_x + int((npc.x + npc.rect_x / 2) * scale_x)
            ny = mm_y + int((npc.y + npc.rect_y / 2) * scale_y)
            pg.draw.circle(screen, npc.texture, (nx, ny), 3)
            pg.draw.circle(screen, (20, 20, 20), (nx, ny), 3, 1)

        # Вьюпорт камеры
        vp_x = mm_x + int(self.camera.x * scale_x)
        vp_y = mm_y + int(self.camera.y * scale_y)
        vp_w = max(2, int(self.camera.view_w * scale_x))
        vp_h = max(2, int(self.camera.view_h * scale_y))
        pg.draw.rect(screen, (255, 255, 255), (vp_x, vp_y, vp_w, vp_h), 1)

        # Игрок
        px = mm_x + int((self.player.x + self.player.rect_x / 2) * scale_x)
        py = mm_y + int((self.player.y + self.player.rect_y / 2) * scale_y)
        pg.draw.circle(screen, (100, 180, 255), (px, py), 3)
        pg.draw.circle(screen, (255, 255, 255), (px, py), 3, 1)

    def _draw_notifications(self, screen):
        y = screen.get_height() - 220
        for txt, t in self.notifications:
            alpha = 255 if t >= 1.0 else int(255 * t)
            surf = self._font_hint.render(txt, True, (255, 240, 100))
            surf.set_alpha(alpha)
            screen.blit(surf, (20, y))
            y += 24

    def _draw_hint(self, screen):
        npc = self._find_npc_near() if self.npcs else None
        if npc:
            text = f"E — поговорить с {npc.name} | Q F R — умения | I C K J | Esc"
        elif self.segment.location_type.is_quest and not self.segment.cleared:
            text = "WASD | ЛКМ — атака | Q F R — умения | E — взаимодействие | Esc"
        else:
            text = "WASD | ЛКМ — атака | Q F R — умения | I C K J | Esc"
        surf = self._font_hint.render(text, True, (230, 230, 230))
        bg = pg.Surface((surf.get_width() + 16, surf.get_height() + 8))
        bg.set_alpha(160)
        bg.fill((0, 0, 0))
        x = 10
        y = screen.get_height() - surf.get_height() - 14
        screen.blit(bg, (x, y))
        screen.blit(surf, (x + 8, y + 4))
