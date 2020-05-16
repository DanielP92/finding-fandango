import os
import pygame as pg
import pytmx

SCREEN_H = 400
SCREEN_W = 600
TERMINAL_VEL = 10
LAYERS = ["Background", "Foreground", "Water", "Decorations"]

current_dir = os.path.dirname('main.py')
bg_file = os.path.join(current_dir + 'assets/', '119991.png')


class SpriteWithCoords(pg.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.x = x
        self.y = y


class LayerError(Exception):
    """Raised when incorrect layer name is used in tmx file"""
    pass


class Images:
    counter = 0
    step = 0

    class Spritesheet:
        def __init__(self, filename):
            self.sheet = pg.image.load(os.path.join(current_dir + 'assets/', filename))
            self.dimensions = [self.sheet.get_width(), self.sheet.get_height()]
            self.all_sprites = []
            self.sprite_dict = {}

        def get_subsurfaces(self, width, height):
            for i in range(0, self.dimensions[1], height):
                for j in range(0, self.dimensions[0], width):
                    self.all_sprites.append(self.sheet.subsurface(j, i, width, height))

    def __init__(self, entity, screen, filename):
        self.entity = entity
        self.screen = screen
        self.image = self.Spritesheet(filename)
        self.current_sprites = []
        self.set_sprites()

    def reset_counter(self):
        self.counter, self.step = 0, 0

    def get_offset(self):
        return [(self.entity.hitbox.x + (self.entity.hitbox.width / 2) - (self.entity.image.get_width() / 2)) - self.entity.hitbox.x,
                (self.entity.hitbox.y + (self.entity.hitbox.height / 2) - (self.entity.image.get_height() / 2)) - self.entity.hitbox.y]

    def set_sprites(self):
        imgs = self.image.all_sprites

        if isinstance(self.entity, Player):
            width, height = 50, 37
            self.image.get_subsurfaces(width, height)

            self.image.sprite_dict = {'idle': [imgs[0], imgs[0], imgs[1], imgs[2],
                                               imgs[2], imgs[2], imgs[3], imgs[0]],
                                      'run': imgs[8:14],
                                      'jump': imgs[15:22],
                                      'fall': imgs[23:24]}

        else:
            pass

    def get_current_sprites(self):
        if isinstance(self.entity, Player):
            if self.entity.movement.is_moving() and self.entity.movement.change_y == 1:
                self.current_sprites = self.image.sprite_dict['run']
            elif self.entity.movement.is_jumping():
                self.current_sprites = self.image.sprite_dict['jump']
            elif self.entity.movement.is_falling():
                self.reset_counter()
                self.current_sprites = self.image.sprite_dict['fall']
            else:
                self.current_sprites = self.image.sprite_dict['idle']

    def update(self):
        self.get_current_sprites()
        no_of_sprites = len(self.current_sprites) - 1
        self.entity.image = self.current_sprites[self.counter]
        self.step += 1

        if self.counter < no_of_sprites and self.step >= 6:
            self.counter += 1
            self.step = 0
        elif self.counter >= no_of_sprites and self.step >= 6:
            self.counter = 0
            self.step = 0


class Map:

    class Settings:
        def __init__(self, file):
            self.tw = file.tilewidth
            self.th = file.tileheight
            self.tw_count = file.width
            self.th_count = file.height

        def get_map_size(self):
            return self.tw * self.tw_count, self.th * self.th_count

    class Tiles:

        class TileSprite(SpriteWithCoords):
            def __init__(self, tile, x, y, width, height):
                super().__init__(x, y)
                self.image = tile
                self.rect = pg.Rect(self.x, self.y, width, height)
                self.collision_area = pg.sprite.Sprite()
                self.collision_area.rect = (0, 0, 0, 0)

        class ForegroundTile(TileSprite):
            def __init__(self, *args):
                super().__init__(*args)
                self.collision_area = pg.sprite.Sprite()
                self.collision_area.rect = self.rect

        class BackgroundTile(TileSprite):
            def __init__(self, *args):
                super().__init__(*args)
                self.collision_area = pg.sprite.Sprite()
                self.collision_area.rect = self.rect.clip(self.x, self.y, self.rect.width, 2)

        class WaterTile(TileSprite):
            step = 0
            counter = 0

            def __init__(self, data, *args):
                super().__init__(*args)
                self.collision_area = pg.sprite.Sprite()
                self.collision_area.rect = (0, 0, 0, 0)
                self.frames = []

            def update(self):
                self.image = self.frames[self.step]
                self.counter += 1
                if self.counter % 25 == 0:
                    self.step += 1
                if self.step > len(self.frames) - 1:
                    self.step = 0

        def __init__(self):
            self.tiles = list()
            self.groups = {'background': pg.sprite.Group(),
                           'foreground': pg.sprite.Group(),
                           'water': pg.sprite.Group(),
                           'decorations': pg.sprite.Group()
                           }
            self.collisions = {'background': pg.sprite.Group(),
                               'foreground': pg.sprite.Group(),
                               }

        def add_to(self, tile, group):
            self.tiles.append(tile)
            group.add(tile)

    class Camera:
        def __init__(self, width, height):
            self.camera = pg.Rect(0, 0, width, height)
            self.width = width
            self.height = height

        def apply(self, entity):
            if isinstance(entity, Player):
                x = (entity.hitbox.x + (entity.hitbox.width / 2)) - (entity.image.get_width() / 2)
                y = entity.hitbox.y - 40
                return entity.hitbox.move((self.camera.topleft[0] + entity.sprites.get_offset()[0], self.camera.topleft[1] + entity.sprites.get_offset()[1]))
            else:
                return entity.rect.move(self.camera.topleft)

        def update(self, target):
            x = -target.hitbox.x + int(SCREEN_W / 2)
            y = -target.hitbox.y + int(SCREEN_H / 2)
            x = min(0, x)
            y = min(0, y)
            x = max(-(self.width - SCREEN_W), x)
            y = max(-(self.height - SCREEN_H), y)
            self.camera = pg.Rect(x, y, self.width, self.height)

    def __init__(self, filename):
        self.file = pytmx.load_pygame(os.path.join(current_dir, filename))
        self.settings = self.Settings(self.file)
        self.tiles = self.Tiles()
        self.width, self.height = self.settings.get_map_size()
        self.camera = self.Camera(self.width, self.height)
        self.set_map()

    def set_map(self):

        def set_layers():
            tw = self.settings.tw
            th = self.settings.th

            for x, y, gid, in layer:
                tile = self.file.get_tile_image_by_gid(gid)
                tile_sprite = None
                data = self.file.get_tile_properties_by_gid(gid)
                group = None

                if layer.name not in LAYERS:
                    raise LayerError(f'"{layer.name}" is an invalid layer name. Must be one of the following: {LAYERS}.')
                else:
                    if layer.name == "Background":
                        if data and data['type'] == "walkable":
                            tile_sprite = self.tiles.BackgroundTile(tile, x * tw, y * th, tw, th)
                            group = self.tiles.groups['background']
                        elif data and data['type'] == "fallable":
                            tile_sprite = self.tiles.TileSprite(tile, x * tw, y * th, tw, th)
                            group = self.tiles.groups['background']
                    elif layer.name == "Foreground":
                        tile_sprite = self.tiles.ForegroundTile(tile, x * tw, y * th, tw, th)
                        group = self.tiles.groups['foreground']
                    elif layer.name == 'Water':
                        tile_sprite = self.tiles.WaterTile(data, tile, x * tw, y * th, tw, th)
                        group = self.tiles.groups['water']
                        if data:
                            tile_sprite.frames = [self.file.get_tile_image_by_gid(x.gid) for x in data['frames']]
                    elif layer.name == 'Decorations':
                        tile_sprite = self.tiles.TileSprite(tile, x * tw, y * th, tw, th)
                        group = self.tiles.groups['decorations']

                    if tile and tile_sprite:
                        self.tiles.add_to(tile_sprite, group)

        for layer in self.file.visible_layers:
            set_layers()

        for sprite in self.tiles.groups['background']:
            self.tiles.collisions['background'].add(sprite)

        for sprite in self.tiles.groups['foreground']:
            self.tiles.collisions['foreground'].add(sprite)

    def draw(self, screen, player):
        for tile in self.tiles.tiles:
            screen.blit(tile.image, self.camera.apply(tile))

        if player.movement.flip:
            screen.blit(pg.transform.flip(player.image, True, False), self.camera.apply(player))
        else:
            screen.blit(player.image, self.camera.apply(player))

        self.camera.update(player)


class BaseHitbox(pg.Rect):
    def __init__(self, *args):
        super().__init__(*args)
        self.active = None

    def is_iframe(self):
        return self.active is False

    def update(self):
        pass


class Player(SpriteWithCoords):
    alive = True

    class Movement:
        def __init__(self, player):
            self.player = player
            self.flip = False
            self.change_x = 0
            self.change_y = 0

        def reset_animation_counter(func):
            def wrapper(self):
                self.player.sprites.reset_counter()
                func(self)
            return wrapper

        def is_moving(self):
            return self.change_x != 0

        def is_jumping(self):
            return self.change_y < 0

        def is_falling(self):
            return self.change_y > 1

        def update(self):
            self.calc_grav()
            self.player.hitbox.x += self.change_x

        def calc_grav(self):
            if self.change_y == 0:
                self.change_y = 1
            elif self.change_y >= TERMINAL_VEL:
                self.change_y = TERMINAL_VEL
            else:
                self.change_y += .3

        @reset_animation_counter
        def move_right(self):
            self.flip = False
            self.change_x = 2

        @reset_animation_counter
        def move_left(self):
            self.flip = True
            self.change_x = -2

        @reset_animation_counter
        def stop(self):
            self.change_x = 0

        @reset_animation_counter
        def jump(self):
            self.change_y = -7

    class Hitbox(BaseHitbox):
        def __init__(self, player, *args):
            super().__init__(*args)
            self.player = player
            self.active = True

        def update(self):
            self.platform_collisions()
            self.enemy_collisions()

        def platform_collisions(self):
            foreground_tile_list = self.player.game_map.tiles.collisions['foreground']

            for sprite in foreground_tile_list:
                if self.colliderect(sprite.collision_area):
                    if self.player.movement.change_x > 0:
                        self.right = sprite.rect.left
                        self.player.movement.stop()
                    elif self.player.movement.change_x < 0:
                        self.left = sprite.rect.right
                        self.player.movement.stop()

            self.y += self.player.movement.change_y

            foreground_tile_list = self.player.game_map.tiles.collisions['foreground']

            for sprite in foreground_tile_list:
                if self.colliderect(sprite.collision_area):
                    if self.player.movement.change_y > 0:
                        self.bottom = sprite.rect.top
                    elif self.player.movement.change_y < 0:
                        self.top = sprite.rect.bottom

                    self.player.movement.change_y = 0

            background_tile_list = self.player.game_map.tiles.collisions['background']

            for sprite in background_tile_list:
                if self.clip(self.x, (self.y + self.height - TERMINAL_VEL), self.width, TERMINAL_VEL).colliderect(sprite.collision_area):
                    if self.player.movement.change_y > 0:
                        self.bottom = sprite.rect.top
                    elif self.player.movement.change_y < 0:
                        pass

                    self.player.movement.change_y = 0

        def enemy_collisions(self):
            if self.is_iframe():
                print('invincible!')
            else:
                pass

    def __init__(self, x, y, game_map, screen):
        super().__init__(x, y)
        self.game_map = game_map
        self.screen = screen
        self.movement = self.Movement(self)
        self.hitbox = self.Hitbox(self, x, y, 15, 32)
        self.image = pg.Surface([self.hitbox.width, self.hitbox.height])
        self.sprites = Images(self, self.screen, 'player-spritesheet.png')

    def get_position(self):
        return self.hitbox.x, self.hitbox.y

    def update(self):
        self.hitbox.update()
        self.movement.update()
        self.sprites.update()


class Game:
    pg.init()
    screen = pg.display.set_mode(size=(SCREEN_W, SCREEN_H))
    all_maps = [Map('maps/level-1.tmx')]
    current_map_no = 0
    background = pg.transform.scale(pg.image.load(bg_file).convert(), (SCREEN_W, SCREEN_H))
    done = False

    def __init__(self):
        self.current_map = self.all_maps[self.current_map_no]
        self.player = Player(50, 500, self.current_map, self.screen)
        self.clock = pg.time.Clock()

    def check_all_events(self):
        for event in pg.event.get():
            self.check_key_press(event)
            self.check_key_release(event)

    def check_key_press(self, event):
        if event.type == pg.QUIT:
            self.done = True

        if event.type == pg.KEYDOWN:
            if event.key == pg.K_LEFT:
                self.player.movement.move_left()
            if event.key == pg.K_RIGHT:
                self.player.movement.move_right()
            if event.key == pg.K_UP:
                self.player.movement.jump()

    def check_key_release(self, event):
        if event.type == pg.KEYUP:
            if event.key == pg.K_LEFT and self.player.movement.change_x < 0:
                self.player.movement.stop()
            if event.key == pg.K_RIGHT and self.player.movement.change_x > 0:
                self.player.movement.stop()

    def main_loop(self):
        while not self.done:
            self.screen.blit(self.background, (0, 0))
            self.check_all_events()
            self.current_map.draw(self.screen, self.player)
            self.current_map.tiles.groups['water'].update()
            self.player.update()
            self.clock.tick(60)
            pg.display.flip()


g = Game()

if __name__ == '__main__':
    g.main_loop()
