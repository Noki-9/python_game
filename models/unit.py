import pygame as pg

from core.assets import assets, facing_from_delta


class Unit:
    def __init__(
        self,
        type: str,
        x: int,
        y: int,
        rect_x: int,
        rect_y: int,
        health: int,
        speed: int,
        texture: str,
        sprite_group: str | None = None,
        sprite_key: str | None = None,
        visual_scale: float = 1.0,
    ):
        self.type = type
        self.health = health
        self.x = x
        self.y = y
        self.rect_x = rect_x
        self.rect_y = rect_y
        # Rect создаётся сразу — это "хитбокс" юнита
        self.Rect = pg.Rect(x, y, rect_x, rect_y)
        self.speed = speed
        self.texture = texture

        # --- Анимация ---
        self.sprite_group = sprite_group
        self.sprite_key = sprite_key
        self.visual_scale = visual_scale
        self.facing = "down"
        self.moving = False
        self.anim_time = 0.0
        self.anim_clip = "idle"
        self.attack_anim = 0.0
        self.hurt_anim = 0.0

    def sync_rect(self):
        """Переносит x, y в Rect. Вызывать после любого изменения позиции."""
        self.Rect.topleft = (int(self.x), int(self.y))

    def check_collision(self, other) -> bool:
        """other — Unit или pygame.Rect."""
        other_rect = other.Rect if isinstance(other, Unit) else other
        return self.Rect.colliderect(other_rect)

    def check_collision_many(self, others: list) -> list:
        """Возвращает список объектов, с которыми есть пересечение."""
        return [o for o in others if self.check_collision(o)]

    # ------------------------------------------------------------------
    # Анимация
    # ------------------------------------------------------------------
    def set_sprite(self, group, key, scale=1.0):
        if self.sprite_group != group or self.sprite_key != key:
            self.anim_time = 0.0
            self.anim_clip = "idle"
        self.sprite_group = group
        self.sprite_key = key
        self.visual_scale = scale

    def face_delta(self, dx, dy):
        self.facing = facing_from_delta(dx, dy, self.facing)

    def face_towards(self, tx, ty):
        self.face_delta(tx - (self.x + self.rect_x / 2), ty - (self.y + self.rect_y / 2))

    def trigger_attack(self, duration=0.24):
        self.attack_anim = duration
        self.anim_time = 0.0
        self.anim_clip = "attack"

    def trigger_hurt(self, duration=0.14):
        self.hurt_anim = max(self.hurt_anim, duration)

    def update_animation(self, dt):
        self.attack_anim = max(0.0, self.attack_anim - dt)
        self.hurt_anim = max(0.0, self.hurt_anim - dt)
        clip = "attack" if self.attack_anim > 0 else ("walk" if self.moving else "idle")
        if clip != self.anim_clip:
            self.anim_clip = clip
            self.anim_time = 0.0
        self.anim_time += dt

    def current_sprite(self):
        if not self.sprite_group or not self.sprite_key:
            return None
        return assets.unit_frame(
            self.sprite_group, self.sprite_key, self.facing, self.anim_clip, self.anim_time
        )

    def draw_sprite(self, screen, camera, scale=None):
        """Рисует анимированный спрайт. Возвращает False, если ассетов нет."""
        sprite = self.current_sprite()
        if sprite is None:
            return False
        scale = self.visual_scale if scale is None else scale
        width = max(1, int(sprite.get_width() * scale))
        height = max(1, int(sprite.get_height() * scale))
        sprite = assets.scaled(sprite, width, height)
        if self.hurt_anim > 0:
            sprite = sprite.copy()
            sprite.fill((90, 40, 40, 0), special_flags=pg.BLEND_RGBA_ADD)
        sx = int(self.x + self.rect_x / 2 - width / 2 - camera.x)
        sy = int(self.y + self.rect_y - height + 2 - camera.y)
        screen.blit(sprite, (sx, sy))
        return True

    # ------------------------------------------------------------------
    def draw(self, screen):
        pg.draw.rect(screen, self.texture, self.Rect)

    def update(self, dt):
        pass
