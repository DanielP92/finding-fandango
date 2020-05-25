import os
import sys
import pygame as pg
import pytmx
from base_classes import SpriteWithCoords, BaseHitbox
import items

# constants
SCREEN_H = 500
SCREEN_W = 850
TERMINAL_VEL = 10
LAYERS = ["Background", "Foreground", "Water", "Decorations", "TreeTrunk", "TreeTop"]

# directories
current_dir = os.path.dirname('main.py')
map_dir = os.path.join(current_dir, 'maps/')
asset_dir = os.path.join(current_dir, 'assets/')
font_dir = os.path.join(asset_dir, 'fonts/')
background_dir = os.path.join(map_dir, 'background/')


class ParallaxBackground:

    class BackgroundSprite(SpriteWithCoords):
        def __init__(self, x, y):
            super().__init__(x, y)
            self.image = pg.Surface((0, 0))
            self.rect = self.image.get_rect()
            self.speed = 0  # larger speed = slower movement, negative speed will move sprites backwards

    def __init__(self, img_name):
        self.img_name = img_name
        self.images = []
        self.get_image_files()

    def get_image_files(self):
        x = 7
        for i in range(6):
            x -= 1
            sprite = self.BackgroundSprite(0, 0)
            filename = self.img_name + str(i) + '.png'
            sprite.image = pg.image.load(os.path.join(background_dir, filename))
            w, h = sprite.image.get_width(), sprite.image.get_height()
            sprite.image = pg.transform.scale(sprite.image, (w, h))
            sprite.rect = sprite.image.get_rect()
            sprite.speed = x
            self.images.append(sprite)


class LayerError(Exception):
    """Raised when incorrect layer name is used in tmx file"""
    pass


class Images:
    counter = 0
    step = 0

    class Spritesheet:
        def __init__(self, filename):
            self.sheet = pg.image.load(os.path.join(current_dir + 'assets/', filename)).convert_alpha()
            self.dimensions = (self.sheet.get_width(), self.sheet.get_height())
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
    background = ParallaxBackground('vrstva-')

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
                self.size = (width, height)
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
                self.image = self.frames[self.step].convert_alpha()
                self.counter += 1
                if self.counter % 25 == 0:
                    self.step += 1
                if self.step > len(self.frames) - 1:
                    self.step = 0

        def __init__(self):
            self.tiles = list()
            self.objects = list()
            self.groups = {'background': pg.sprite.Group(),
                           'foreground': pg.sprite.Group(),
                           'water': pg.sprite.Group(),
                           'decorations': pg.sprite.Group(),
                           'items': pg.sprite.Group()
                           }
            self.collisions = {'background': pg.sprite.Group(),
                               'foreground': pg.sprite.Group(),
                               }

        def add_to_tiles(self, tile, group):
            self.tiles.append(tile)
            group.add(tile)

        def add_to_objects(self, item, group):
            self.objects.append(item)
            group.add(item)

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
            elif isinstance(entity, ParallaxBackground.BackgroundSprite):
                return entity.rect.move((self.camera.bottomleft[0] / entity.speed, self.camera.bottomleft[1] / entity.speed))
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
        self.file = pytmx.load_pygame(os.path.join(map_dir, filename))
        self.settings = self.Settings(self.file)
        self.tiles = self.Tiles()
        self.width, self.height = self.settings.get_map_size()
        self.camera = self.Camera(self.width, self.height)
        self.set_map()

    def set_map(self):

        def set_layers():
            tw = self.settings.tw
            th = self.settings.th
            if isinstance(layer, pytmx.TiledTileLayer):
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
                        elif layer.name in ['Decorations', "TreeTrunk", "TreeTop"]:
                            tile_sprite = self.tiles.TileSprite(tile, x * tw, y * th, tw, th)
                            group = self.tiles.groups['decorations']

                        if tile and tile_sprite:
                            self.tiles.add_to_tiles(tile_sprite, group)

            elif isinstance(layer, pytmx.TiledObjectGroup):
                for item in layer:
                    sprite = None

                    if item.image and item.name == 'all-potion':
                        sprite = items.Restore(item.x, item.y, health=2, mana=10)
                        sprite.frames = [self.file.get_tile_image_by_gid(x.gid) for x in item.properties['frames']]
                    elif item.image and item.name == 'mana-potion':
                        sprite = items.Restore(item.x, item.y, mana=20)
                        sprite.frames = [self.file.get_tile_image_by_gid(x.gid) for x in item.properties['frames']]
                    elif item.image and item.name == 'health-potion':
                        sprite = items.Restore(item.x, item.y, health=1)
                        sprite.frames = [self.file.get_tile_image_by_gid(x.gid) for x in item.properties['frames']]

                    if sprite:
                        self.tiles.add_to_objects(sprite, self.tiles.groups['items'])

        for layer in self.file.visible_layers:
            set_layers()

        for sprite in self.tiles.groups['background']:
            self.tiles.collisions['background'].add(sprite)

        for sprite in self.tiles.groups['foreground']:
            self.tiles.collisions['foreground'].add(sprite)

    def draw(self, screen, player):
        for sprite in self.background.images:
            screen.blit(sprite.image.convert_alpha(), self.camera.apply(sprite))

        for tile in self.tiles.tiles:
            screen.blit(tile.image, self.camera.apply(tile))

        for item in self.tiles.objects:
            screen.blit(item.image, self.camera.apply(item))

        if player.movement.flip:
            screen.blit(pg.transform.flip(player.image, True, False), self.camera.apply(player))
        else:
            screen.blit(player.image, self.camera.apply(player))

        self.camera.update(player)


class Player(SpriteWithCoords):

    class Stats:
        def __init__(self, player):
            self.player = player
            self.alive = True
            self.lives = 5
            self.mana = 20
            self.collectables = 0

    class Movement:
        def __init__(self, player):
            self.player = player
            self.flip = False
            self.change_x = 0
            self.change_y = 0

        def animation_reset(func):
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

        @animation_reset
        def move_right(self):
            self.flip = False
            self.change_x = 2

        @animation_reset
        def move_left(self):
            self.flip = True
            self.change_x = -2

        @animation_reset
        def stop(self):
            self.change_x = 0

        @animation_reset
        def jump(self):
            self.change_y = -7

    class Hitbox(BaseHitbox):
        def __init__(self, player, *args):
            super().__init__(*args)
            self.player = player
            self.active = True
            self.health = 5

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
        self.stats = self.Stats(self)

    def get_position(self):
        return self.hitbox.x, self.hitbox.y

    def update(self):
        self.hitbox.update()
        self.movement.update()
        self.sprites.update()
        if self.stats.lives < 0:
            self.stats.alive = False


class Menu:
    def __init__(self):
        self.title_font = pg.font.Font(os.path.join(font_dir, 'SquadaOne-Regular.ttf'), 42)
        self.subtitle_font = pg.font.Font(os.path.join(font_dir, 'Raleway-Medium.ttf'), 24)
        self.body_font = pg.font.Font(os.path.join(font_dir, 'Raleway-Light.ttf'), 18)
        self.show = True

    def title_screen(self, screen):
        while self.show:
            for event in pg.event.get():
                if event.type == pg.QUIT:
                    self.show = False
                    sys.exit()

                if event.type == pg.KEYUP:
                    if event.key == pg.K_RETURN:
                        self.show = False
            self.draw(screen)
            pg.display.update()

    def draw(self, screen):
        title = self.title_font.render("Finding Fandango", True, (150, 0, 100))
        subt = self.subtitle_font.render("A short platforming adventure...", True, (100, 0, 150))
        desc = self.body_font.render("Press Enter to start", True, (100, 0, 150))

        screen.blit(title, (SCREEN_W / 2 - (title.get_width() / 2), SCREEN_H / 3 - (title.get_height() / 2)))
        screen.blit(subt, (SCREEN_W / 2 - (subt.get_width() / 2), SCREEN_H / 2 - (subt.get_height() / 2)))
        screen.blit(desc, (SCREEN_W / 2 - (desc.get_width() / 2), SCREEN_H / 2 + (subt.get_height() / 2)))


class Game:
    pg.init()
    screen = pg.display.set_mode((SCREEN_W, SCREEN_H), pg.SCALED, 32)
    all_maps = [Map('level-1.tmx')]
    current_map_no = 0
    done = False

    def __init__(self):
        self.current_map = self.all_maps[self.current_map_no]
        self.player = Player(50, 500, self.current_map, self.screen)
        self.clock = pg.time.Clock()
        self.menu = Menu()

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
        sky = pg.image.load(os.path.join(background_dir, '1.png'))
        sky = pg.transform.scale(sky, (SCREEN_W, SCREEN_H))
        self.menu.title_screen(self.screen)
        while not self.done:
            self.check_all_events()
            self.screen.blit(sky.convert_alpha(), (0, 0))
            self.current_map.draw(self.screen, self.player)
            self.current_map.tiles.groups['water'].update()
            self.current_map.tiles.groups['items'].update()
            self.player.update()
            self.clock.tick(60)
            pg.display.flip()


g = Game()

if __name__ == '__main__':
    g.main_loop()
