import pygame as pg

screen = pg.display.set_mode((1280, 720))
clock = pg.time.Clock()

# --- Размеры мира ---
WORLD_W = 150  # сегментов по X (как RimWorld "medium planet")
WORLD_H = 120  # сегментов по Y

LOCAL_W = 250  # тайлов по X (RimWorld default map)
LOCAL_H = 250  # тайлов по Y
TILE_SIZE = 32  # 250 * 32 = 8000 px — карта в 6 раз больше экрана

# --- Spatial hash ---
CHUNK_SIZE = 8  # 8×8 тайлов в чанке
