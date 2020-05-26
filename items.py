import pygame as pg
from base_classes import SpriteWithCoords, BaseHitbox


class Item(SpriteWithCoords):
    step = 0
    counter = 0

    def __init__(self, x, y):
        super().__init__(x, y)
        self.width, self.height = 16, 16
        self.rect = BaseHitbox(self.x, self.y, 10, self.height)
        self.image = pg.Surface((self.width, self.height))
        self.frames = []

    def effect(self):
        pass

    def update(self):
        self.image = self.frames[self.step].convert_alpha()
        self.counter += 1
        if self.counter % 12 == 0:
            self.step += 1
        if self.step > len(self.frames) - 1:
            self.step = 0


class Restore(Item):
    def __init__(self, x, y, health=0, mana=0):
        super().__init__(x, y)
        self.health = health
        self.mana = mana

    def effect(self, player):
        if player.hitbox.health + self.health > 5:
            player.hitbox.health = 5
        elif player.hitbox.health + self.health < 5:
            player.hitbox.health += self.health

        if player.stats.mana < 100:
            player.stats.mana += self.mana
        else:
            pass


class OneUp(Item):
    def __init__(self, x, y):
        super().__init__(x, y)

    def effect(self, player):
        player.stats.lives += 1
        player.hitbox.health = 5


class Collectable(Item):
    def __init__(self, x, y, z=1):
        super().__init__(x, y)
        self.z = z                  # z is the value the collectible is worth,, default value of 1

    def effect(self, player):
        if player.stats.collectables <= 99:
            player.stats.collectables += self.z
        elif player.stats.collectables >= 100:
            player.stats.lives += 1
            player.hitbox.health = 5
            player.stats.collectables = 0

    def update(self):
        self.image = self.frames[self.step].convert_alpha()
        self.counter += 1
        if self.counter % 8 == 0:
            self.step += 1
        if self.step > len(self.frames) - 1:
            self.step = 0
