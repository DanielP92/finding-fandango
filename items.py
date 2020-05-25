import pygame as pg
from base_classes import SpriteWithCoords, BaseHitbox


class Item(SpriteWithCoords):
    def __init__(self, x, y):
        super().__init__(x, y)
        self.width, self.height = 16, 16
        self.hitbox = BaseHitbox(self.x, self.y, 10, self.height)
        self.image = pg.Surface(self.width, self.height)
