import math
import random

import pygame as pg

from core.abilities import get_abilities_for_class, get_ability_for_key
from core.assets import assets
from core.status_effects import EFFECT_DEFS
from core.camera import Camera
from core.config import TILE_SIZE, screen
from core.scene_manager import Scene
from core.utils import direction_name
from models.player import Player
from models.projectile import Projectile, visual_for_ability
from models.resource_node import ResourceNode
from models.npc import NPC
from ui.character_ui import CharacterUI
from ui.dialogue_ui import DialogueUI
from ui.inventory_ui import InventoryUI
from ui.quest_log_ui import QuestLogUI
from ui.skills_ui import SkillsUI
from world.item_generator import roll_random_equipment
from world.location_type import LocationType
from world.loot import GOLD, ITEMS_REGISTRY
from world.npc_gen import spawn_npcs
from world.quest import QuestType
from world.quest_gen import generate_quest
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
        self.visual_effects = []  # [x, y, radius, color, t_left, t_max, kind]
        self.particles = []
        self.return_pos = None
        self.notifications = []
        self.opened_props = set()
        self.objective_pending = False
        self.objective_kind = None
        self.objective_quest = None
        self.escort_npc = None
        self._minimap_cache = None
        self.time = 0.0

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
        self.particles = []
        self.opened_props = set(self.segment.opened_props)
        self._minimap_cache = None
        self.time = 0.0

        state = self.manager.player_state
        state.restore()
        if self.segment.location_type.is_settlement:
            state.remember_village(self.segment.gx, self.segment.gy)

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

        self._setup_location_objectives(state)
        self._sync_fetch_quests()
        self._build_minimap()

        if self.segment.cleared:
            self.notifications.append(("Локация уже зачищена", 3.0))

    # ================= Цели квестов в локации =================
    def _find_free_prop_tile(self):
        rng = random.Random(self.segment.seed + 991)
        sx, sy = self.map.spawn_tile
        occupied = {(tx, ty) for _k, tx, ty in getattr(self.map, "props", [])}
        for obj in self.map.objects:
            occupied.add((obj.tx, obj.ty))
        for _ in range(300):
            tx = rng.randint(max(6, sx - 22), min(self.map.width - 7, sx + 22))
            ty = rng.randint(max(6, sy - 22), min(self.map.height - 7, sy + 22))
            if (tx, ty) in occupied:
                continue
            if not self.map.is_walkable(tx, ty):
                continue
            return tx, ty
        return None

    def _spawn_escort_npc(self, quest):
        npc = NPC(
            npc_id=f"escortee_{quest.quest_id}",
            name="Путник",
            role="guard",
            x=self.player.x - TILE_SIZE,
            y=self.player.y,
            rect_x=TILE_SIZE - 8,
            rect_y=TILE_SIZE - 8,
            color=(210, 185, 140),
        )
        npc.role_title = "Спутник"
        npc.home_x = npc.x
        npc.home_y = npc.y
        self.escort_npc = npc

    def _setup_location_objectives(self, state):
        self.objective_pending = False
        self.objective_kind = None
        self.objective_quest = None
        self.escort_npc = None
        active = state.quest_log.active()

        if self.segment.location_type.is_quest and not self.segment.cleared:
            for q in active:
                if q.quest_type not in (QuestType.FREE, QuestType.EXPLORE):
                    continue
                if (q.target_gx, q.target_gy) != (
                    self.segment.gx,
                    self.segment.gy,
                ):
                    continue
                kind = (
                    "prisoner" if q.quest_type == QuestType.FREE else "artifact"
                )
                pos = self._find_free_prop_tile()
                if pos is not None:
                    self.map.props.append((kind, pos[0], pos[1]))
                    self.objective_pending = True
                    self.objective_kind = kind
                    self.objective_quest = q
                break

        # «Найденные» квесты в диких локациях — записки.
        if (
            self.segment.location_type == LocationType.WILD
            and not self.segment.cleared
        ):
            rng = random.Random(self.segment.seed + 5150)
            if rng.random() < 0.22:
                pos = self._find_free_prop_tile()
                if pos is not None:
                    self.map.props.append(("note", pos[0], pos[1]))

        for q in active:
            if q.quest_type != QuestType.ESCORT:
                continue
            if (q.target_gx, q.target_gy) == (
                self.segment.gx,
                self.segment.gy,
            ):
                finished = state.quest_log.notify_escort_arrived(
                    self.segment.gx, self.segment.gy
                )
                self._on_quests_completed(finished)
                if finished:
                    self.notifications.append(
                        (f"Путник доставлен: {q.objective.target_id}", 3.5)
                    )
            else:
                self._spawn_escort_npc(q)
            break

    def _update_escort(self, dt):
        npc = self.escort_npc
        if npc is None:
            return
        px, py = self._player_center()
        nx = npc.x + npc.rect_x / 2
        ny = npc.y + npc.rect_y / 2
        dx, dy = px - nx, py - ny
        dist = math.hypot(dx, dy)
        if dist > 52:
            step = min(dist - 44, 220 * dt)
            tx = npc.x + dx / dist * step
            ty = npc.y + dy / dist * step
            ttx = int((tx + npc.rect_x / 2) // TILE_SIZE)
            tty = int((ty + npc.rect_y / 2) // TILE_SIZE)
            if self.map.is_walkable(ttx, tty):
                npc.x, npc.y = tx, ty
                npc.moving = True
                npc.face_delta(dx, dy)
        npc.update_animation(dt)

    def _draw_quest_prop(self, screen, kind, tx, ty):
        sx, sy = self.camera.apply(tx * TILE_SIZE, ty * TILE_SIZE)
        if not (
            -64 < sx < self.camera.view_w + 64
            and -64 < sy < self.camera.view_h + 64
        ):
            return
        cx, cy = sx + TILE_SIZE // 2, sy + TILE_SIZE // 2
        bob = int(math.sin(self.time * 2.5 + tx + ty) * 2)
        if kind == "artifact":
            pg.draw.circle(screen, (230, 200, 90), (cx, cy + bob), 11, 2)
            pg.draw.polygon(
                screen,
                (255, 240, 160),
                [
                    (cx, cy - 8 + bob),
                    (cx + 7, cy + bob),
                    (cx, cy + 8 + bob),
                    (cx - 7, cy + bob),
                ],
            )
            pg.draw.circle(screen, (255, 255, 220), (cx - 2, cy - 3 + bob), 2)
        elif kind == "prisoner":
            pg.draw.rect(screen, (70, 60, 50), (sx + 6, sy + 6, 20, 24), border_radius=3)
            pg.draw.rect(screen, (190, 170, 140), (sx + 11, sy + 9, 10, 10), border_radius=5)
            for i in range(3):
                pg.draw.line(
                    screen,
                    (150, 140, 120),
                    (sx + 9 + i * 7, sy + 6),
                    (sx + 9 + i * 7, sy + 30),
                    2,
                )
            pg.draw.rect(screen, (220, 200, 150), (sx + 14, sy + 20, 4, 8))
        else:  # note
            pg.draw.rect(screen, (230, 220, 180), (sx + 9, sy + 10 + bob, 14, 18))
            for i in range(4):
                pg.draw.line(
                    screen,
                    (120, 110, 90),
                    (sx + 11, sy + 14 + i * 3 + bob),
                    (sx + 21, sy + 14 + i * 3 + bob),
                    1,
                )

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
                base.set_at(
                    (tx, ty),
                    assets.tile_color(row[tx], COLORS.get(row[tx], (255, 0, 255))),
                )
        for obj in self.map.objects:
            base.set_at(
                (obj.tx, obj.ty),
                assets.object_color(obj.kind, COLORS.get(obj.kind, (255, 0, 255))),
            )
        self._minimap_cache = pg.transform.scale(base, (MINIMAP_SIZE, MINIMAP_SIZE))

    # ================= Ввод =================
    def handle_event(self, event):
        if event.type == pg.KEYDOWN:
            if event.key == pg.K_ESCAPE:
                from core.save_load import save_game
                from scenes.world_scene import WorldScene

                save_game(self.manager.world, self.manager.player_state, slot="auto")
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
            if event.key == pg.K_t:
                self._try_rest()
                return
            if event.key == pg.K_b:
                self._open_camp_craft()
                return
            if event.key == pg.K_x:
                self._toggle_stealth()
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
                    return
                node = self._find_resource_near()
                if node is not None:
                    self._gather_resource(node)
                    return
                if self.objective_pending:
                    objective = self._find_prop_near({self.objective_kind})
                    if objective is not None:
                        self._complete_objective()
                        return
                note = self._find_prop_near({"note"})
                if note is not None:
                    self._open_note(note)
                    return
                prop = self._find_chest_near()
                if prop is not None:
                    self._open_chest(prop)
                    return
                self._try_interact()
            elif event.key == pg.K_SPACE:
                self._player_attack()

        elif event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
            self._player_attack()

    # ================= Умения =================
    @staticmethod
    def _ability_fx(ability_id):
        if ability_id == "m_f":
            return "ice"
        if ability_id == "m_r":
            return "explosion"
        if ability_id == "w_f":
            return "heal"
        if ability_id.startswith(("w_", "r_")):
            return "slash"
        if ability_id in ("a_q", "a_f"):
            return "hit"
        return "explosion"

    def _add_fx(self, kind, x, y, color=(255, 255, 255), radius=32, duration=0.35):
        self.visual_effects.append([x, y, radius, color, duration, duration, kind])

    def _spawn_particles(self, x, y, color, count=8, speed=90):
        for _ in range(count):
            angle = random.uniform(0, math.tau)
            spd = random.uniform(speed * 0.35, speed)
            life = random.uniform(0.25, 0.55)
            self.particles.append(
                [
                    x,
                    y,
                    math.cos(angle) * spd,
                    math.sin(angle) * spd,
                    life,
                    life,
                    color,
                    random.choice((1, 1, 2)),
                ]
            )

    def _toggle_stealth(self):
        s = self.manager.player_state
        if s.class_id not in ("rogue", "archer"):
            self.notifications.append(("Скрытность доступна плуту и лучнику", 1.6))
            return
        s.stealth = not s.stealth
        if s.stealth:
            self.notifications.append(("Скрытность включена", 1.2))
        else:
            self.notifications.append(("Скрытность выключена", 1.2))

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

        s.stealth = False
        self.player.trigger_attack(0.3)
        if ability.is_projectile:
            self._cast_projectile(ability)
        elif ability.is_aoe_at_cursor:
            self._cast_aoe_at_cursor(ability)
        elif ability.is_aoe_self:
            self._cast_aoe_self(ability)
        elif ability.is_single_target:
            self._cast_single_target(ability)

    @staticmethod
    def _apply_ability_effect(ability, target):
        if not ability.effect:
            return
        if random.random() > ability.effect_chance:
            return
        target.apply_status(
            ability.effect,
            ability.effect_duration or None,
            ability.effect_power or None,
        )

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
                    visual=visual_for_ability(ability.ability_id),
                    effect=ability.effect,
                    effect_chance=ability.effect_chance,
                    effect_duration=ability.effect_duration,
                    effect_power=ability.effect_power,
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
                    killed = t.take_damage(damage)
                    self._apply_ability_effect(ability, t)
                    if killed:
                        self._on_enemy_killed(t)

        self.visual_effects.append(
            [wx, wy, radius, ability.color, 0.5, 0.5, self._ability_fx(ability.ability_id)]
        )
        self._spawn_particles(wx, wy, ability.color, count=14, speed=130)

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
                    killed = t.take_damage(damage)
                    self._apply_ability_effect(ability, t)
                    if killed:
                        self._on_enemy_killed(t)

        if ability.heal > 0:
            self.manager.player_state.heal(ability.heal)
            self.notifications.append((f"+{ability.heal} HP", 1.0))
            self._add_fx("heal", pcx, pcy, (120, 255, 160), 40, 0.5)

        self.visual_effects.append(
            [pcx, pcy, radius, ability.color, 0.35, 0.35, self._ability_fx(ability.ability_id)]
        )
        self._spawn_particles(pcx, pcy, ability.color, count=10, speed=120)

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
        killed = best.take_damage(damage)
        self._apply_ability_effect(ability, best)
        if killed:
            self._on_enemy_killed(best)

        self.visual_effects.append(
            [
                best.x + best.rect_x / 2,
                best.y + best.rect_y / 2,
                30,
                ability.color,
                0.25,
                0.25,
                self._ability_fx(ability.ability_id),
            ]
        )
        self._spawn_particles(
            best.x + best.rect_x / 2,
            best.y + best.rect_y / 2,
            ability.color,
            count=10,
            speed=100,
        )

    def _has_target_in_range(self):
        cx, cy = self._player_center()
        attack_range = self.manager.player_state.attack_range
        for target in list(self.enemies) + list(self.animals):
            if not target.is_alive():
                continue
            if math.hypot(
                target.x + target.rect_x / 2 - cx,
                target.y + target.rect_y / 2 - cy,
            ) <= attack_range:
                return True
        return False

    # ================= Атака =================
    def _player_attack(self):
        self.player.trigger_attack(0.25)
        targets = [e for e in self.enemies if e.is_alive()] + [
            a for a in self.animals if a.is_alive()
        ]
        result = self.player.try_attack(targets)
        if result is None:
            # Взмах в пустоту — эффект и анимация всё равно видны.
            dirs = {"left": (-1, 0), "right": (1, 0), "up": (0, -1), "down": (0, 1)}
            ox, oy = dirs.get(self.player.facing, (0, 1))
            px = self.player.x + self.player.rect_x / 2 + ox * 26
            py = self.player.y + self.player.rect_y / 2 + oy * 26
            self._add_fx("slash", px, py, (255, 245, 210), 24, 0.22)
            return
        killed, target, is_crit = result
        tx = target.x + target.rect_x / 2
        ty = target.y + target.rect_y / 2
        if is_crit:
            self.notifications.append(("КРИТ!", 1.0))
            self._add_fx("slash", tx, ty, (255, 230, 120), 34, 0.3)
            self._spawn_particles(tx, ty, (255, 210, 90), count=14, speed=140)
        else:
            self._add_fx("hit", tx, ty, (255, 240, 210), 22, 0.22)
            self._spawn_particles(tx, ty, target.texture, count=7, speed=95)
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

        cx, cy = enemy.x + enemy.rect_x / 2, enemy.y + enemy.rect_y / 2
        self._add_fx("hit", cx, cy, enemy.texture, 28, 0.3)
        self._spawn_particles(cx, cy, enemy.texture, count=16, speed=135)
        self._add_fx("pickup", cx, cy, (255, 220, 120), 20, 0.45)

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
        if finished:
            from core.save_load import save_game

            save_game(self.manager.world, state, slot="auto")

    def _sync_fetch_quests(self):
        state = self.manager.player_state
        finished = state.quest_log.notify_inventory(state.inventory)
        self._on_quests_completed(finished)

    def _check_quest_completion(self):
        if not self.segment.location_type.is_quest:
            return
        if self.segment.cleared:
            return
        if self.objective_pending:
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
        state.reputation += 5
        rng = random.Random(self.segment.seed + 7331)
        reward_item = roll_random_equipment(rng)
        if reward_item is not None:
            state.add_item(reward_item)
            self.notifications.append((f"Награда: {reward_item.name}", 4.5))
        self.notifications.append(
            ("Локация зачищена! +100 золота, +250 XP, +5 репутации", 4.0)
        )
        from core.save_load import save_game

        save_game(self.manager.world, state, slot="auto")
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

    def _player_center(self):
        return (
            self.player.x + self.player.rect_x / 2,
            self.player.y + self.player.rect_y / 2,
        )

    def _find_resource_near(self):
        px, py = self._player_center()
        best = None
        best_d = NPC_INTERACT_RADIUS
        for obj in self.map.objects:
            if not isinstance(obj, ResourceNode) or obj.depleted:
                continue
            d = math.hypot(obj.x + obj.rect_x / 2 - px, obj.y + obj.rect_y / 2 - py)
            if d < best_d:
                best = obj
                best_d = d
        return best

    def _find_prop_near(self, kinds):
        px, py = self._player_center()
        best = None
        best_d = NPC_INTERACT_RADIUS
        for kind, tx, ty in getattr(self.map, "props", []):
            if kinds is not None and kind not in kinds:
                continue
            if (kind, tx, ty) in self.opened_props:
                continue
            cx = tx * TILE_SIZE + TILE_SIZE / 2
            cy = ty * TILE_SIZE + TILE_SIZE / 2
            d = math.hypot(cx - px, cy - py)
            if d < best_d:
                best = (kind, tx, ty)
                best_d = d
        return best

    def _find_chest_near(self):
        return self._find_prop_near({"chest"})

    def _gather_resource(self, node):
        state = self.manager.player_state
        template = ITEMS_REGISTRY.get(node.resource_id)
        if template is None:
            return
        item = template.copy()
        item.count = node.amount
        state.add_item(item)
        node.depleted = True
        state.add_xp(3)
        self.notifications.append((f"+{item.count} {item.name}", 1.8))
        cx = node.x + node.rect_x / 2
        cy = node.y + node.rect_y / 2
        self._spawn_particles(cx, cy, item.icon_color, count=8, speed=80)
        self._sync_fetch_quests()

    def _open_chest(self, prop):
        _kind, tx, ty = prop
        self.opened_props.add(prop)
        self.segment.opened_props.add(prop)
        state = self.manager.player_state
        rng = random.Random(
            (self.segment.seed * 73856093) ^ (tx * 19349663) ^ (ty * 83492791)
        )
        gold = rng.randint(15, 50)
        state.add_gold(gold)
        self.notifications.append((f"Сундук: +{gold} золота", 2.0))
        if rng.random() < 0.55:
            equip = roll_random_equipment(rng)
            if equip:
                state.add_item(equip)
                self.notifications.append((f"Найдено: {equip.name}", 2.5))
        cx = tx * TILE_SIZE + TILE_SIZE / 2
        cy = ty * TILE_SIZE + TILE_SIZE / 2
        self._add_fx("pickup", cx, cy, (255, 220, 120), 24, 0.5)
        self._spawn_particles(cx, cy, (255, 220, 120), count=12, speed=110)

    def _complete_objective(self):
        if not self.objective_pending:
            return
        prop = self._find_prop_near({self.objective_kind})
        if prop is None:
            return
        if prop in self.map.props:
            self.map.props.remove(prop)
        self.objective_pending = False
        state = self.manager.player_state
        label = (
            "Пленник освобождён"
            if self.objective_kind == "prisoner"
            else "Артефакт найден"
        )
        self.notifications.append((label, 3.0))
        cx = prop[1] * TILE_SIZE + TILE_SIZE / 2
        cy = prop[2] * TILE_SIZE + TILE_SIZE / 2
        self._add_fx("pickup", cx, cy, (255, 230, 120), 32, 0.6)
        self._spawn_particles(cx, cy, (255, 230, 120), count=16, speed=120)
        quest = self.objective_quest
        self.objective_quest = None
        if quest is not None:
            finished = state.quest_log.notify_objective(quest.objective.target_id)
            self._on_quests_completed(finished)
        self._complete_quest()

    def _open_note(self, prop):
        if prop in self.map.props:
            self.map.props.remove(prop)
        world = getattr(self.manager, "world", None)
        state = self.manager.player_state
        if world is None:
            self.notifications.append(("Записка истлела", 1.6))
            return
        from types import SimpleNamespace

        seed = (
            self.segment.seed * 7331 + prop[1] * 131 + prop[2] * 17
        ) & 0xFFFFFFFF
        giver = SimpleNamespace(
            npc_id=f"note_{self.segment.seed}_{prop[1]}_{prop[2]}",
            name="Найденная записка",
        )
        quest = generate_quest(
            world, giver, seed, state.level, state.gx, state.gy
        )
        if state.quest_log.add(quest):
            self.notifications.append((f"Найден квест: {quest.title}", 3.5))
        else:
            self.notifications.append(
                ("Записка не содержит нового задания", 2.0)
            )

    def _try_rest(self):
        state = self.manager.player_state
        in_settlement = self.segment.location_type.is_settlement
        campfire = self._find_prop_near({"campfire"})
        if not in_settlement and campfire is None:
            self.notifications.append(("Отдых возможен в деревне или у костра", 1.8))
            return
        state.rest(full=in_settlement)
        label = "Полный отдых" if in_settlement else "Отдых у костра"
        self.notifications.append((f"{label}: силы восстановлены", 2.0))
        self._add_fx("heal", *self._player_center(), (120, 255, 160), 42, 0.6)

    def _open_camp_craft(self):
        if self._find_prop_near({"campfire"}) is None:
            self.notifications.append(("Нужен костёр для крафта", 1.6))
            return
        from ui.craft_ui import CraftUI
        from world.crafting import CAMP_RECIPES

        self.manager.push_ui(
            CraftUI(
                screen.get_size(),
                self.manager.player_state,
                recipes=CAMP_RECIPES,
                title="Костёр — простой крафт",
            )
        )

    # ================= Update =================
    def update(self, dt):
        if not self.player.is_alive():
            self._on_player_death()
            return

        self.time += dt

        state = self.manager.player_state
        state.tick_ability_cooldowns(dt)
        state.regen_mana(dt)
        if state.tick_status(dt):
            self._on_player_death()
            return

        self._tick_enemy_statuses(dt)
        self._group_alert()

        # Автоатака при зажатой ЛКМ (ТЗ 9).
        if pg.mouse.get_pressed()[0] and self.player.attack_timer <= 0:
            if self._has_target_in_range():
                self._player_attack()

        nearby = self.map.walls_near(
            self.player.x + self.player.rect_x / 2,
            self.player.y + self.player.rect_y / 2,
            radius_px=96,
        )
        self.player.update(
            dt, walls=nearby, map_w_px=self.map_w_px, map_h_px=self.map_h_px
        )
        self.camera.follow(self.player, self.map_w_px, self.map_h_px)
        self._update_escort(dt)

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

        for npc in self.npcs:
            npc.update(dt, self.player)

        for p in self.projectiles:
            was_alive = p.alive
            killed_list = p.update(dt, self.enemies, self.animals, self.map, TILE_SIZE)
            for target in killed_list:
                self._on_enemy_killed(target)
            if was_alive and not p.alive:
                if p.visual in ("fireball", "meteor"):
                    kind = "explosion"
                elif p.visual == "ice":
                    kind = "ice"
                else:
                    kind = "hit"
                radius = max(24, p.aoe_radius) if p.aoe_radius else 24
                self._add_fx(kind, p.x, p.y, p.color, radius, 0.38)
                self._spawn_particles(p.x, p.y, p.color, count=10, speed=110)
        self.projectiles = [p for p in self.projectiles if p.alive]

        for eff in self.visual_effects:
            eff[4] -= dt
        self.visual_effects = [e for e in self.visual_effects if e[4] > 0]

        for part in self.particles:
            part[0] += part[2] * dt
            part[1] += part[3] * dt
            part[2] *= max(0.0, 1.0 - 4.0 * dt)
            part[3] *= max(0.0, 1.0 - 4.0 * dt)
            part[4] -= dt
        self.particles = [p for p in self.particles if p[4] > 0]

        self._collect_drops()

        if not self.player.is_alive():
            self._on_player_death()
            return

        self.notifications = [
            (txt, t - dt) for txt, t in self.notifications if t - dt > 0
        ]

    def _tick_enemy_statuses(self, dt):
        for unit in list(self.enemies) + list(self.animals):
            if not unit.is_alive():
                continue
            damage = unit.status.tick(dt)
            if damage <= 0:
                continue
            unit.health -= damage
            unit.trigger_hurt()
            if unit.health <= 0:
                self._on_enemy_killed(unit)

    def _group_alert(self):
        """Раненый/заметивший игрока враг поднимает тревогу у соседей."""
        alerted = [
            e
            for e in self.enemies
            if e.is_alive() and e.alert_timer > 0
        ]
        if not alerted:
            return
        for e in self.enemies:
            if not e.is_alive() or e.alert_timer > 0:
                continue
            ex = e.x + e.rect_x / 2
            ey = e.y + e.rect_y / 2
            for other in alerted:
                ox = other.x + other.rect_x / 2
                oy = other.y + other.rect_y / 2
                if math.hypot(ox - ex, oy - ey) < 200:
                    e.alert_timer = 4.0
                    break

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
        # Потеря одного случайного предмета из инвентаря.
        if state.inventory:
            drop_idx = random.randrange(len(state.inventory))
            state.inventory.pop(drop_idx)
        state.hp = state.max_hp
        state.stamina = state.max_stamina
        state.mana = float(state.max_mana)
        state.status.clear()
        world = self.manager.world
        respawn = state.last_village or (world.start_gx, world.start_gy)
        from scenes.world_scene import WorldScene

        self.manager.switch(
            WorldScene(self.manager, world),
            world_pos=respawn,
            mode="play",
        )

    # ================= Draw =================
    def draw(self, screen):
        screen.fill((20, 20, 20))

        tx0, ty0, tx1, ty1 = self.camera.visible_tile_range(TILE_SIZE)
        tx1 = min(tx1, self.map.width)
        ty1 = min(ty1, self.map.height)
        tiles = self.map.tiles
        tile_at = assets.tile
        for ty in range(ty0, ty1):
            row = tiles[ty]
            sy = ty * TILE_SIZE - int(self.camera.y)
            for tx in range(tx0, tx1):
                sx = tx * TILE_SIZE - int(self.camera.x)
                name = row[tx]
                variant = (tx * 73856093 ^ ty * 19349663) & 0x7FFFFFFF
                image = tile_at(name, variant, self.time)
                if image is not None:
                    screen.blit(image, (sx, sy))
                else:
                    pg.draw.rect(
                        screen, COLORS.get(name, (255, 0, 255)), (sx, sy, TILE_SIZE, TILE_SIZE)
                    )

        self._draw_props(screen)
        self._draw_entities(screen)
        self._draw_dropped_items(screen)
        for p in self.projectiles:
            p.draw(screen, self.camera)
        self._draw_visual_effects(screen)
        self._draw_particles(screen)
        self._draw_quest_marker(screen)

        self._draw_label(screen)
        self._draw_hud(screen)
        self._draw_active_quests(screen)
        self._draw_ability_bar(screen)
        self._draw_minimap(screen)
        self._draw_notifications(screen)
        self._draw_hint(screen)

    # ---------- Пропсы и сущности ----------
    def _draw_props(self, screen):
        for kind, tx, ty in getattr(self.map, "props", []):
            if kind in ("prisoner", "artifact", "note"):
                self._draw_quest_prop(screen, kind, tx, ty)
                continue
            image = assets.prop(kind, self.time)
            if image is None:
                continue
            sx, sy = self.camera.apply(tx * TILE_SIZE, ty * TILE_SIZE)
            if -64 < sx < self.camera.view_w + 64 and -64 < sy < self.camera.view_h + 64:
                screen.blit(image, (sx, sy))

    def _draw_entities(self, screen):
        drawables = []

        # Статичные объекты (деревья, кактусы) сортируются вместе с юнитами по Y.
        tx0, ty0, tx1, ty1 = self.camera.visible_tile_range(TILE_SIZE)
        tx1 = min(tx1, self.map.width)
        ty1 = min(ty1, self.map.height)
        for ty in range(ty0, ty1):
            row = self.map.object_grid[ty]
            for tx in range(tx0, tx1):
                obj = row[tx]
                if obj is not None:
                    drawables.append((obj.bottom, "object", obj))

        for a in self.animals:
            if a.is_alive():
                drawables.append((a.y + a.rect_y, "unit", a))
        for e in self.enemies:
            if e.is_alive():
                drawables.append((e.y + e.rect_y, "unit", e))
        for npc in self.npcs:
            drawables.append((npc.y + npc.rect_y, "npc", npc))
        if self.escort_npc is not None:
            drawables.append(
                (
                    self.escort_npc.y + self.escort_npc.rect_y,
                    "npc",
                    self.escort_npc,
                )
            )
        drawables.append((self.player.y + self.player.rect_y, "unit", self.player))
        drawables.sort(key=lambda item: item[0])
        for _y, kind, obj in drawables:
            if kind == "npc":
                obj.draw(screen, self.camera, self._font_npc)
            elif kind == "object":
                obj.draw(screen, self.camera, self.time)
            else:
                obj.draw(screen, self.camera)

    def _draw_dropped_items(self, screen):
        for item, x, y in self.dropped_items:
            sx, sy = self.camera.apply(x + 4, y + 4)
            bob = int(math.sin(self.time * 3.0 + (x + y) * 0.01) * 3)
            cx, cy = sx + 12, sy + 12 + bob
            color = item.rarity.color if item.is_equipment else item.icon_color
            pg.draw.circle(screen, (20, 20, 20), (cx, cy + 5), 9)
            pg.draw.circle(screen, color, (cx, cy), 11, 1)
            icon = assets.item_icon(item)
            if icon is not None:
                icon = assets.scaled(icon, 22, 22)
                screen.blit(icon, icon.get_rect(center=(cx, cy)))
            else:
                pg.draw.circle(screen, color, (cx, cy), 5)

    def _draw_particles(self, screen):
        for x, y, vx, vy, life, max_life, color, size in self.particles:
            t = max(0.0, min(1.0, life / max_life))
            c = (int(color[0] * t), int(color[1] * t), int(color[2] * t))
            sx, sy = self.camera.apply(x, y)
            pg.draw.rect(screen, c, (sx, sy, size, size))

    # ---------- Отрисовка эффектов ----------
    def _draw_visual_effects(self, screen):
        for effect in self.visual_effects:
            x, y, radius, color, t_left, t_max = effect[:6]
            kind = effect[6] if len(effect) > 6 else "ring"
            sx, sy = self.camera.apply(x, y)
            if kind != "ring":
                progress = 1.0 - max(0.0, t_left) / max(0.001, t_max)
                frame = assets.effect_frame(kind, progress)
                if frame is not None:
                    size = max(28, int(radius * 1.3))
                    frame = assets.scaled(frame, size, size).copy()
                    alpha = int(255 * min(1.0, max(0.0, t_left) / max(0.001, t_max * 0.6)))
                    frame.set_alpha(alpha)
                    screen.blit(frame, frame.get_rect(center=(sx, sy)))
                    continue
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
        cx = (self.map.width // 2) * TILE_SIZE + TILE_SIZE // 2
        cy = (self.map.height // 2) * TILE_SIZE + TILE_SIZE // 2
        sx, sy = self.camera.apply(cx, cy)
        color = (120, 120, 120) if self.segment.cleared else (240, 208, 90)
        pulse = 2.0 * math.sin(self.time * 3.0)
        pg.draw.circle(screen, color, (sx, sy), int(20 + pulse), 2)
        bob = int(math.sin(self.time * 2.5) * 3)
        icon = assets.world_icon("cleared" if self.segment.cleared else "quest")
        if icon is not None:
            icon = assets.scaled(icon, 22, 22)
            screen.blit(icon, icon.get_rect(center=(sx, sy - 30 + bob)))
        else:
            pg.draw.circle(screen, color, (sx, sy - 26 + bob), 8)

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
        assets.draw_bar(screen, (10, y, 200, 16), s.hp_ratio, "bar_hp")
        surf = self._font_hud.render(f"HP: {s.hp}/{s.max_hp}", True, (255, 255, 255))
        screen.blit(surf, (216, y - 1))

        y += 20
        assets.draw_bar(screen, (10, y, 200, 12), s.mana_ratio, "bar_mp")
        surf = self._font_hud.render(
            f"MP: {int(s.mana)}/{s.max_mana}", True, (255, 255, 255)
        )
        screen.blit(surf, (216, y - 1))

        y += 18
        xp_r = s.xp / s.xp_to_next if s.xp_to_next else 0
        assets.draw_bar(screen, (10, y, 200, 14), xp_r, "bar_xp")
        surf = self._font_hud.render(
            f"Ур. {s.level}  XP: {s.xp}/{s.xp_to_next}", True, (255, 255, 255)
        )
        screen.blit(surf, (216, y - 1))

        y += 18
        gold_icon = assets.named_icon("gold")
        if gold_icon is not None:
            gold_icon = assets.scaled(gold_icon, 16, 16)
            screen.blit(gold_icon, (10, y - 1))
            surf = self._font_hud.render(f"Золото: {s.gold}", True, (240, 220, 100))
            screen.blit(surf, (30, y))
        else:
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
            y += 18

        if s.status.effects:
            names = ", ".join(
                EFFECT_DEFS[k]["name"]
                for k in s.status.active_kinds()
                if k in EFFECT_DEFS
            )
            surf = self._font_hud.render(f"Эффекты: {names}", True, (255, 150, 120))
            screen.blit(surf, (10, y))
            y += 18

        if s.stealth:
            surf = self._font_hud.render("Скрытность: вкл [X]", True, (150, 220, 255))
            screen.blit(surf, (10, y))
            y += 18

        # === Навигация ===
        y += 20
        state = self.manager.player_state
        if state.waypoint is not None:
            wgx, wgy = state.waypoint
            dx, dy = wgx - self.segment.gx, wgy - self.segment.gy
            dist = math.hypot(dx, dy)
            if dist == 0:
                text = "★ Вы на метке"
            else:
                text = f"★ Метка: {direction_name(dx, dy)} ({int(dist)})"
            surf = self._font_hud.render(text, True, (255, 230, 80))
            screen.blit(surf, (10, y))
            y += 18

        # Мы на цели какого-то квеста?
        on_target = [
            q
            for q in state.quest_log.active()
            if q.target_gx == self.segment.gx and q.target_gy == self.segment.gy
        ]
        if on_target:
            q = on_target[0]
            text = f"⚑ Вы на месте квеста: {q.title}"
            surf = self._font_hud.render(text, True, (255, 200, 100))
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

            icon = assets.ability_icon(ab.ability_id)
            if icon is not None:
                icon = assets.scaled(icon, 40, 40)
                screen.blit(icon, icon.get_rect(center=(rect.centerx, rect.centery)))
            else:
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
            pg.draw.circle(screen, color, (qx, qy), 5, 1)
            icon = assets.world_icon("cleared" if self.segment.cleared else "quest")
            if icon is not None:
                icon = assets.scaled(icon, 12, 12)
                screen.blit(icon, icon.get_rect(center=(qx, qy)))
            else:
                pg.draw.circle(screen, color, (qx, qy), 4)

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

        # Объекты локации
        prop_colors = {
            "altar": (120, 230, 255),
            "campfire": (255, 150, 60),
            "brazier": (255, 180, 80),
            "chest": (240, 200, 90),
            "cave": (30, 30, 38),
            "well": (90, 150, 210),
            "ruins": (160, 160, 160),
            "grave": (180, 180, 190),
            "crate": (170, 120, 70),
        }
        for kind, ptx, pty in getattr(self.map, "props", []):
            px = mm_x + int(ptx * TILE_SIZE * scale_x)
            py = mm_y + int(pty * TILE_SIZE * scale_y)
            pg.draw.circle(screen, prop_colors.get(kind, (200, 200, 200)), (px, py), 2)

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
        icon = assets.world_icon("player")
        if icon is not None:
            pg.draw.circle(screen, (255, 255, 255), (px, py), 7, 1)
            icon = assets.scaled(icon, 12, 12)
            screen.blit(icon, icon.get_rect(center=(px, py)))
        else:
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
        node = self._find_resource_near()
        chest = self._find_chest_near()
        if npc:
            text = f"E — поговорить с {npc.name} | Q F R — умения | I C K J | Esc"
        elif node is not None:
            text = f"E — собрать: {node.display_name} | ЛКМ — атака | I C K J | Esc"
        elif chest is not None:
            text = "E — открыть сундук | ЛКМ — атака | I C K J | Esc"
        elif self.objective_pending:
            label = (
                "освободить пленника"
                if self.objective_kind == "prisoner"
                else "забрать артефакт"
            )
            text = f"E — {label} | ЛКМ — атака | I C K J | Esc"
        elif self._find_prop_near({"note"}) is not None:
            text = "E — прочитать записку | ЛКМ — атака | I C K J | Esc"
        elif self.segment.location_type.is_settlement:
            text = "T — отдохнуть | E — диалог | Q F R — умения | I C K J | Esc"
        elif self.segment.location_type.is_quest and not self.segment.cleared:
            text = "WASD | ЛКМ — атака | Q F R — умения | X — скрытность | Esc"
        else:
            text = "WASD | ЛКМ — атака | Q F R — умения | E — собрать | X — скрытность | Esc"
        surf = self._font_hint.render(text, True, (230, 230, 230))
        bg = pg.Surface((surf.get_width() + 16, surf.get_height() + 8))
        bg.set_alpha(160)
        bg.fill((0, 0, 0))
        x = 10
        y = screen.get_height() - surf.get_height() - 14
        screen.blit(bg, (x, y))
        screen.blit(surf, (x + 8, y + 4))
