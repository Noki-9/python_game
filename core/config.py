import pygame as pg

screen = pg.display.set_mode((1280, 720))
clock = pg.time.Clock()

# --- Размеры мира ---
WORLD_W = 150
WORLD_H = 120

LOCAL_W = 250
LOCAL_H = 250
TILE_SIZE = 32

# --- Spatial hash ---
CHUNK_SIZE = 8

# --- Глобальная карта ---
VISION_RADIUS = 10  # радиус обзора в сегментах
