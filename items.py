import pygame as pg
from base_classes import SpriteWithCoords, BaseHitBox


class Item(SpriteWithCoords):
    def __init__(self, x, y):
        super().__init__(x, y)
        self.width, self.height = 10, 16
        self.hitbox = BaseHitbox(self.x, self.y, self.width, self.height)
        self.image = pg.Surface(self.width, self.height)
