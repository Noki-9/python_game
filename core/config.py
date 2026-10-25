import pygame as pg

screen = pg.display.set_mode((1280, 720))
clock = pg.time.Clock()

WORLD_W = 150
WORLD_H = 120

LOCAL_W = 250
LOCAL_H = 250
TILE_SIZE = 32

CHUNK_SIZE = 8

# --- Туман войны ---
VISION_NEAR = 16  # радиус полной видимости (сегменты)
VISION_FAR = 30  # радиус полного затухания
VISION_NEAR_SQ = VISION_NEAR * VISION_NEAR
VISION_FAR_SQ = VISION_FAR * VISION_FAR

MEMORY_VISIBILITY = 0.55  # яркость «памяти» разведанного (0..1)
