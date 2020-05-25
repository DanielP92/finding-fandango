import pygame as pg
from base_classes import SpriteWithCoords, BaseHitbox


class Item(SpriteWithCoords):
    def __init__(self, x, y):
        super().__init__(x, y)
        self.width, self.height = 16, 16
        self.hitbox = BaseHitbox(self.x, self.y, 10, self.height)
        self.image = pg.Surface(self.width, self.height)

    def effect(self):
        pass


class Restore(Item):
    def __init__(self, x, y, z):
        super().__init__(x, y)
        self.z = z                   # z is the amount of health restored

    def effect(self, player):
        if player.hitbox.health + self.z > 5:
            player.hitbox.health = 5
        elif player.health.health + self.z < 5:
            player.hitbox.health += self.z


class OneUp(Item):
    def __init__(self, x, y):
        super().__init__(x, y)

    def effect(self, player):
        player.lives += 1
        player.hitbox.health = 5


class Collectable(Item):
    def __init__(self, x, y, z=1):
        super().__init__(x, y)
        self.z = z                  # z is the value the collectible is worth,, default value of 1

    def effect(self, player):
        if player.collectables <= 99:
            player.collectables += self.z
        elif player.collectables >= 100:
            player.lives += 1
            player.hitbox.health = 5
            player.collectables = 0
