import math

from models.enemy import Enemy


class Animal(Enemy):
    """Животное: пассивное (стоит/пасётся) или агрессивное."""

    def __init__(
        self,
        animal_id,
        x,
        y,
        rect_x,
        rect_y,
        health,
        speed,
        damage,
        aggro_radius,
        xp_reward,
        color,
        passive=True,
        loot_rng_seed=0,
    ):
        super().__init__(
            animal_id,
            x,
            y,
            rect_x,
            rect_y,
            health,
            speed,
            damage=damage,
            attack_range=36,
            attack_cooldown=1.2,
            aggro_radius=aggro_radius,
            xp_reward=xp_reward,
            color=color,
            loot_rng_seed=loot_rng_seed,
        )
        self.passive = passive

    def update(self, dt, player, walls):
        if not self.is_alive():
            return

        self.attack_timer = max(0.0, self.attack_timer - dt)
        self.alert_timer = max(0.0, self.alert_timer - dt)

        px = player.x + player.rect_x / 2
        py = player.y + player.rect_y / 2
        cx = self.x + self.rect_x / 2
        cy = self.y + self.rect_y / 2
        dx, dy = px - cx, py - cy
        dist = math.hypot(dx, dy)

        if self.passive:
            # Пассивные: убегают только когда их ударили
            if self.alert_timer > 0 and dist > 0:
                mvx = -dx / dist * self.speed * dt
                mvy = -dy / dist * self.speed * dt
                self._try_move(mvx, mvy, walls)
                self.ai_state = "flee"
            else:
                self.ai_state = "idle"
            return

        # Агрессивные животные — как обычный Enemy
        super().update(dt, player, walls)
