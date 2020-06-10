import os
import sys
import pygame as pg
import pytmx
from base_classes import SpriteWithCoords, BaseHitbox
import items

# constants
SCREEN_H = 768
SCREEN_W = 1366
TERMINAL_VEL = 10
LAYERS = ["Background", "Foreground", "Water", "Decorations", "TreeTrunk", "TreeTop"]
ITEM_NAMES = ['all-potion', 'mana-potion', 'health-potion', '1-up', 'coin-silver', 'coin-gold']
BG_IMG_NAME = 'vrstva-'

# directories
current_dir = os.path.dirname('main.py')
map_dir = os.path.join(current_dir, 'maps/')
asset_dir = os.path.join(current_dir, 'assets/')
font_dir = os.path.join(asset_dir, 'fonts/')
background_dir = os.path.join(map_dir, 'background/')

pg.init()

LABEL_FONT = pg.font.Font(os.path.join(font_dir, 'SquadaOne-Regular.ttf'), 18)


class BackgroundSprite(SpriteWithCoords):
    def __init__(self, x, y, spd, filename):
        super().__init__(x, y)
        self.speed = spd         # larger speed = slower movement, negative speed will move sprites backwards
        self.filename = filename
        self.image = pg.image.load(os.path.join(background_dir, self.filename))
        self.image = pg.transform.scale(self.image, (int(self.get_size()[0] * 0.65), int(self.get_size()[1] * 0.65)))
        self.width, self.height = self.get_size()
        self.rect = pg.Rect(self.x, self.y, self.width, self.height)

    def get_size(self):
        return self.image.get_width(), self.image.get_height()


class ParallaxBackground:
    def __init__(self, img_name, game_map):
        self.img_name = img_name
        self.game_map = game_map
        self.images = []
        self.get_image_files()

    def get_image_files(self):
        spd = 4

        for i in range(6):
            spd -= 0.5
            filename = BG_IMG_NAME + str(i) + '.png'
            sprite = BackgroundSprite(0, 0, spd, filename)
            repeater = int((self.game_map.width / (sprite.width * sprite.speed)) + 1)

            for i in range(repeater):
                x = sprite.width * i
                extra_sprite = BackgroundSprite(x, 0, spd, filename)
                self.images.append(extra_sprite)


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
                return entity.hitbox.move((self.camera.topleft[0] + entity.sprites.get_offset()[0], self.camera.topleft[1] + entity.sprites.get_offset()[1]))
            elif isinstance(entity, BackgroundSprite):
                return entity.rect.move((self.camera.topleft[0] / (entity.speed + 1), (self.camera.bottomleft[1] - entity.image.get_height())))
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
        self.settings = {'background': None,
                         'tw': self.file.tilewidth,
                         'th': self.file.tileheight,
                         'tw_count': self.file.width,
                         'th_count': self.file.height}

        self.tiles = self.Tiles()
        self.width, self.height = self.get_map_size()
        self.settings.update({'background': ParallaxBackground('vrstva-', self)})
        self.camera = self.Camera(self.width, self.height)
        self.set_map()

    def get_map_size(self):
        return self.settings['tw'] * self.settings['tw_count'], self.settings['th'] * self.settings['th_count']

    def set_map(self):
        tw = self.settings['tw']
        th = self.settings['th']
        restore = items.Restore
        one_up = items.OneUp
        coin = items.Collectable

        def set_layers():

            if isinstance(layer, pytmx.TiledTileLayer):
                for x, y, gid, in layer:
                    tile = self.file.get_tile_image_by_gid(gid)
                    sprite = None
                    data = self.file.get_tile_properties_by_gid(gid)
                    position = x * tw, y * th, tw, th
                    group = None

                    if layer.name not in LAYERS:
                        raise LayerError(f'"{layer.name}" is an invalid layer name. Must be one of the following: {LAYERS}.')
                    else:
                        if layer.name == "Background":
                            if data and data['type'] == "walkable":
                                sprite = self.tiles.BackgroundTile(tile, *position)
                                group = self.tiles.groups['background']
                            elif data and data['type'] == "fallable":
                                sprite = self.tiles.TileSprite(tile, *position)
                                group = self.tiles.groups['background']
                        elif layer.name == "Foreground":
                            sprite = self.tiles.ForegroundTile(tile, *position)
                            group = self.tiles.groups['foreground']
                        elif layer.name == 'Water':
                            sprite = self.tiles.WaterTile(data, tile, *position)
                            group = self.tiles.groups['water']
                            if data:
                                sprite.frames = [self.file.get_tile_image_by_gid(x.gid) for x in data['frames']]
                        elif layer.name in ['Decorations', "TreeTrunk", "TreeTop"]:
                            sprite = self.tiles.TileSprite(tile, *position)
                            group = self.tiles.groups['decorations']

                        if tile and sprite:
                            self.tiles.add_to_tiles(sprite, group)

            elif isinstance(layer, pytmx.TiledObjectGroup):
                for item in layer:
                    position = item.x, item.y
                    sprite = None

                    item_sprites = [restore(*position, health=35, mana=35), restore(*position, mana=20),
                                    restore(*position, health=20), one_up(*position), coin(*position), coin(*position, z=2)]

                    for key, value in zip(ITEM_NAMES, item_sprites):
                        if item.name == key:
                            sprite = value
                            sprite.frames = [self.file.get_tile_image_by_gid(x.gid) for x in item.properties['frames']]
                            self.tiles.add_to_objects(sprite, self.tiles.groups['items'])

        for layer in self.file.visible_layers:
            set_layers()

        for sprite in self.tiles.groups['background']:
            self.tiles.collisions['background'].add(sprite)

        for sprite in self.tiles.groups['foreground']:
            self.tiles.collisions['foreground'].add(sprite)

    def draw_background(self, screen):
        cam = self.camera.camera

        for sprite in self.settings['background'].images:
            camera_left = max(self.camera.camera.topleft[0], 1)
            move_ratio = 1 / (camera_left / (camera_left / (sprite.speed + 1)))
            if not move_ratio:
                move_ratio = 1

            def on_screen(x):
                left_on_screen = 0 <= x.left + (cam.left * (move_ratio)) <= SCREEN_W
                right_on_screen = 0 <= x.right + (cam.left * (move_ratio)) <= SCREEN_W
                return bool((left_on_screen or right_on_screen))

            if on_screen(sprite.rect):
                screen.blit(sprite.image.convert_alpha(), self.camera.apply(sprite))

    def draw(self, screen, player):
        self.draw_background(screen)

        for tile in self.tiles.tiles:
            screen.blit(tile.image.convert_alpha(), self.camera.apply(tile))

        for item in self.tiles.objects:
            screen.blit(item.image.convert_alpha(), self.camera.apply(item))

        if player.movement.flip:
            screen.blit(pg.transform.flip(player.image.convert_alpha(), True, False), self.camera.apply(player))
        else:
            screen.blit(player.image.convert_alpha(), self.camera.apply(player))

        self.camera.update(player)


class Player(SpriteWithCoords):

    class Stats:
        max_mana = 100

        def __init__(self, player):
            self.player = player
            self.alive = True
            self.lives = 5
            self.mana = 20
            self.collectables = 0

    class Movement:
        max_jumps = 1

        def __init__(self, player):
            self.player = player
            self.flip = False
            self.change_x = 0
            self.change_y = 0
            self.jump_count = self.max_jumps

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
            if self.jump_count:
                self.jump_count -= 1
                self.change_y = -7

    class Hitbox(BaseHitbox):
        max_health = 100

        def __init__(self, player, *args):
            super().__init__(*args)
            self.player = player
            self.active = True
            self.health = 68

        def update(self):
            self.platform_collisions()
            self.item_collisions()
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
                    self.player.movement.jump_count = self.player.movement.max_jumps

            background_tile_list = self.player.game_map.tiles.collisions['background']

            for sprite in background_tile_list:
                if self.clip(self.x, (self.y + self.height - TERMINAL_VEL), self.width, TERMINAL_VEL).colliderect(sprite.collision_area):
                    if self.player.movement.change_y > 0:
                        self.bottom = sprite.rect.top
                    elif self.player.movement.change_y < 0:
                        pass

                    self.player.movement.change_y = 0
                    self.player.movement.jump_count = self.player.movement.max_jumps

        def item_collisions(self):
            item_list = self.player.game_map.tiles.groups['items']

            for sprite in item_list:
                if self.colliderect(sprite.rect):
                    sprite.effect(self.player)
                    sprite.kill()
                    self.player.game_map.tiles.objects.remove(sprite)
                    print(self.player.stats.collectables, self.player.stats.lives, self.player.hitbox.health, self.player.stats.mana)

        def enemy_collisions(self):
            if self.is_iframe():
                print('invincible!')
            else:
                pass

    def __init__(self, x, y, game_map, screen):
        super().__init__(x, y)
        self.game_map = game_map
        self.movement = self.Movement(self)
        self.hitbox = self.Hitbox(self, x, y, 15, 32)
        self.image = pg.Surface([self.hitbox.width, self.hitbox.height])
        self.sprites = Images(self, screen, 'player-spritesheet.png')
        self.stats = self.Stats(self)

    def get_position(self):
        return self.hitbox.x, self.hitbox.y

    def update(self):
        self.hitbox.update()
        self.movement.update()
        self.sprites.update()
        if self.stats.lives < 0:
            self.stats.alive = False


class Label(pg.sprite.Sprite):

    def __init__(self, display_value):
        super().__init__()
        self.image = LABEL_FONT.render(str(display_value), True, (0, 0, 0))


class StatDisplay:
    dict_keys = ['lives', 'collectables', 'health', 'mana']
    font = pg.font.Font(os.path.join(font_dir, 'SquadaOne-Regular.ttf'), 15)

    def __init__(self, player, screen):
        self.player = player
        self.screen = screen
        self.image = pg.Surface([SCREEN_W, SCREEN_H], pg.SRCALPHA, 32)
        self.properties = {'stats': {},
                           'images': {},
                           'labels': {}}

        self.set_images()

    def get_health_increment(self):
        return (SCREEN_W / 3) / self.player.hitbox.max_health

    def get_mana_increment(self):
        return (SCREEN_W / 3) / self.player.stats.max_mana

    def set_images(self):
        dict_values = [pg.image.load(os.path.join(asset_dir, 'ui-lives.png')),
                       pg.image.load(os.path.join(asset_dir, 'ui-coins.png')),
                       pg.image.load(os.path.join(asset_dir, 'ui-health.png')),
                       pg.image.load(os.path.join(asset_dir, 'ui-mana.png'))]

        for key, value in zip(self.dict_keys, dict_values):
            self.properties['images'].update({key: value})

    def set_labels(self):
        dict_values = [Label(self.player.stats.lives), Label(self.player.stats.collectables),
                       Label(self.player.hitbox.health), Label(self.player.stats.mana)]

        for key, value in zip(self.dict_keys, dict_values):
            self.properties['labels'].update({key: value})

    def update(self):
        dict_values = [self.player.stats.lives, self.player.stats.collectables,
                       self.player.hitbox.health, self.player.stats.mana]

        for key, value in zip(self.dict_keys, dict_values):
            self.properties['stats'].update({key: value})

        self.set_labels()
        self.draw()

    def draw(self):
        bar_length = SCREEN_W / 3

        # set health bar
        base_health_bar = pg.Rect(38, 13, bar_length + 4, 19)
        health_bar = pg.Rect(40, 15, bar_length, 15)
        health_bar.width = self.get_health_increment() * self.player.hitbox.health

        # set mana bar
        base_mana_bar = pg.Rect(SCREEN_W - 40 - bar_length, 13, bar_length + 4, 19)
        mana_bar = pg.Rect(SCREEN_W - 38 - bar_length, 15, bar_length, 15)
        mana_bar.width = self.get_mana_increment() * self.player.stats.mana

        # draw health and mana bars
        pg.draw.rect(self.image, (0, 0, 0), base_health_bar)
        pg.draw.rect(self.image, (235, 100, 100), health_bar)
        pg.draw.rect(self.image, (0, 0, 0), base_mana_bar)
        pg.draw.rect(self.image, (100, 100, 235), mana_bar)

        # set labels
        health_label = self.properties['labels']['health'].image
        mana_label = self.properties['labels']['mana'].image
        oneup_label = self.properties['labels']['lives'].image
        coin_label = self.properties['labels']['collectables'].image

        # blit stat images to self.image
        self.image.blit(pg.transform.scale(self.properties['images']['health'], (31, 37)), (0, 0))
        self.image.blit(pg.transform.scale(self.properties['images']['mana'], (31, 37)), ((SCREEN_W - 37), 0))
        self.image.blit(pg.transform.scale(self.properties['images']['lives'], (31, 37)), (0, (SCREEN_H - 40)))
        self.image.blit(pg.transform.scale(self.properties['images']['collectables'], (30, 30)), ((SCREEN_W - 36), (SCREEN_H - 30)))

        # blit labels to screen
        self.screen.blit(health_label, (SCREEN_W / 2 - (health_label.get_width() + 75), 14))
        self.screen.blit(mana_label, (SCREEN_W / 2 + 75, 14))
        self.screen.blit(oneup_label, (38, SCREEN_H - 23))
        self.screen.blit(coin_label, (SCREEN_W - (38 + coin_label.get_width()), SCREEN_H - 23))


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
    screen = pg.display.set_mode((SCREEN_W, SCREEN_H), pg.SCALED, 32)
    all_maps = [Map('level-1.tmx')]
    current_map_no = 0
    sky = pg.transform.scale(pg.image.load(os.path.join(background_dir, '1.png')).convert_alpha(), (SCREEN_W, SCREEN_H))
    done = False

    def __init__(self):
        self.current_map = self.all_maps[self.current_map_no]
        self.player = Player(50, 500, self.current_map, self.screen)
        self.ui_display = StatDisplay(self.player, self.screen)
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

    def update(self):
        self.current_map.tiles.groups['water'].update()
        self.current_map.tiles.groups['items'].update()
        self.player.update()
        self.ui_display.update()
        self.clock.tick(60)
        pg.display.flip()

    def draw(self):
        self.screen.blit(self.sky, (0, 0))
        self.current_map.draw(self.screen, self.player)
        self.screen.blit(self.ui_display.image, (0, 0))

    def main_loop(self):
        self.menu.title_screen(self.screen)
        while not self.done:
            self.check_all_events()
            self.draw()
            self.update()


g = Game()

if __name__ == '__main__':
    g.main_loop()
