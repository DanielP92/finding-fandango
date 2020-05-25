import pygame as pg


class SpriteWithCoords(pg.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.x = x
        self.y = y


class BaseHitbox(pg.Rect):
    def __init__(self, *args):
        super().__init__(*args)
        self.active = None

    def is_iframe(self):
        return self.active is False

    def update(self):
        pass
