import pygame
import os
import cv2
import mediapipe as mp
import pyautogui
import random
import json
import time
from operator import itemgetter

pygame.font.init()
pygame.mixer.init()


WIDTH, HEIGHT = 1500, 1000  # 1028, 750
score = 0
WIN = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Space Shooter Tutorial")
break_sound = pygame.mixer.Sound("assets/break.ogg")
shoot_sound = pygame.mixer.Sound("assets/blaster.ogg")
# Load images
RED_SPACE_SHIP = pygame.image.load(os.path.join("assets", "pixel_ship_red_small.png"))
GREEN_SPACE_SHIP = pygame.image.load(os.path.join("assets", "pixel_ship_green_small.png"))
BLUE_SPACE_SHIP = pygame.image.load(os.path.join("assets", "pixel_ship_blue_small.png"))

# Player player
YELLOW_SPACE_SHIP = pygame.image.load(os.path.join("assets", "pixel_ship_yellow.png"))

# Lasers
RED_LASER = pygame.image.load(os.path.join("assets", "pixel_laser_red.png"))
GREEN_LASER = pygame.image.load(os.path.join("assets", "pixel_laser_green.png"))
BLUE_LASER = pygame.image.load(os.path.join("assets", "pixel_laser_blue.png"))
YELLOW_LASER = pygame.image.load(os.path.join("assets", "pixel_laser_yellow.png"))

# Background
BG = pygame.transform.scale(pygame.image.load(os.path.join("assets", "background-black.png")), (WIDTH, HEIGHT))
screen_w, screen_h = pyautogui.size()
cam = cv2.VideoCapture(0)
pyautogui.FAILSAFE = False
pose = mp.solutions.pose.Pose()
class Laser:
    def __init__(self, x, y, img):
        self.x = x
        self.y = y
        self.img = img
        self.mask = pygame.mask.from_surface(self.img)

    def draw(self, window):
        window.blit(self.img, (self.x, self.y))

    def move(self, vel):
        self.y += vel

    def off_screen(self, height):
        return not(self.y <= height and self.y >= 0)

    def collision(self, obj):
        return collide(self, obj)


class Ship:
    COOLDOWN = 20

    def __init__(self, x, y, health=10):
        self.x = x
        self.y = y
        self.health = health
        self.ship_img = None
        self.laser_img = None
        self.lasers = []
        self.cool_down_counter = 0

    def draw(self, window):
        window.blit(self.ship_img, (self.x, self.y))
        for laser in self.lasers:
            laser.draw(window)

    def move_lasers(self, vel, obj, dmg):
        self.cooldown()
        for laser in self.lasers:
            laser.move(vel)
            if laser.off_screen(HEIGHT):
                self.lasers.remove(laser)
            elif laser.collision(obj):
                break_sound.play()
                obj.health -= dmg
                self.lasers.remove(laser)

    def cooldown(self):
        if self.cool_down_counter >= self.COOLDOWN:
            self.cool_down_counter = 0
        elif self.cool_down_counter > 0:
            self.cool_down_counter += 1

    def shoot(self):
        if self.cool_down_counter == 0:
            laser = Laser(self.x, self.y, self.laser_img)
            shoot_sound.play()
            self.lasers.append(laser)
            self.cool_down_counter = 1

    def get_width(self):
        return self.ship_img.get_width()

    def get_height(self):
        return self.ship_img.get_height()


class Player(Ship):
    score = 0
    def __init__(self, x, y, health=10):
        super().__init__(x, y, health)
        self.ship_img = YELLOW_SPACE_SHIP
        self.laser_img = YELLOW_LASER
        self.mask = pygame.mask.from_surface(self.ship_img)
        self.max_health = health
    def move_lasers(self, vel, objs, dmg):
        self.cooldown()
        for laser in self.lasers:
            laser.move(vel)
            if laser.off_screen(HEIGHT):
                self.lasers.remove(laser)
            else:
                for obj in objs:
                    if laser.collision(obj):
                        objs.remove(obj)
                        break_sound.play()
                        self.score += obj.points
                        if laser in self.lasers:
                            self.lasers.remove(laser)

    def draw(self, window):
        super().draw(window)
        self.healthbar(window)

    def healthbar(self, window):
        pygame.draw.rect(window, (255,0,0), (self.x, self.y + self.ship_img.get_height() + 10, self.ship_img.get_width(), 10))
        pygame.draw.rect(window, (0,255,0), (self.x, self.y + self.ship_img.get_height() + 10, self.ship_img.get_width() * (self.health/self.max_health), 10))


class Enemy(Ship):
    COLOR_MAP = {
                "red": (RED_SPACE_SHIP, RED_LASER, 50, 20, 3),
                "green": (GREEN_SPACE_SHIP, GREEN_LASER, 75, 10, 2),
                "blue": (BLUE_SPACE_SHIP, BLUE_LASER, 100, 5, 1)
                }

    def __init__(self, x, y, color, health=100):
        super().__init__(x, y, health)
        self.ship_img, self.laser_img, self.speed, self.dmg, self.points = self.COLOR_MAP[color]
        self.mask = pygame.mask.from_surface(self.ship_img)
    def move(self, vel):
        if self.y > -100:
            self.y += int(vel*self.speed/100)
        else:
            self.y += int(vel*self.speed/100)*2

    def shoot(self):
        if self.cool_down_counter == 0:
            laser = Laser(self.x-20, self.y, self.laser_img)
            self.lasers.append(laser)
            self.cool_down_counter = 1


def collide(obj1, obj2):
    offset_x = obj2.x - obj1.x
    offset_y = obj2.y - obj1.y
    return obj1.mask.overlap(obj2.mask, (offset_x, offset_y)) != None

def main(name):
    run = True
    FPS = 2000
    level = 0

    main_font = pygame.font.SysFont("comicsans", 50)
    lost_font = pygame.font.SysFont("comicsans", 60)

    enemies = []
    wave_length = 5
    enemy_vel = 5  # 1
    laser_vel = 25  # 5

    player = Player(300, HEIGHT - 150)

    clock = pygame.time.Clock()

    lost = False
    lost_count = 0

    def redraw_window():
        WIN.blit(BG, (0,0))
        # draw text
        lives_label = main_font.render(f"Score: {player.score}", 1, (255,255,255))
        level_label = main_font.render(f"Level: {level}", 1, (255,255,255))

        WIN.blit(lives_label, (10, 10))
        WIN.blit(level_label, (WIDTH - level_label.get_width() - 10, 10))

        for enemy in enemies:
            enemy.draw(WIN)

        player.draw(WIN)

        if lost:
            lost_label = lost_font.render("You Lost!!", 1, (255,255,255))
            WIN.blit(lost_label, (WIDTH/2 - lost_label.get_width()/2, 350))

        pygame.display.update()

    while run:
        clock.tick(FPS)
        redraw_window()
        _, frame = cam.read()
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        rgb_frame = cv2.flip(rgb_frame, 1)
        output = pose.process(rgb_frame)
        landmarks = output.pose_landmarks
        frame_h, frame_w, _ = frame.shape
        oldx = 0
        if landmarks:
            landmark = landmarks.landmark
            mark = landmark[0]
            movex = int(mark.x * WIDTH * 2)
            if abs(movex-oldx) > 5:
                player.x = movex - WIDTH/2
                oldx = movex
        player.shoot()

        if player.health <= 0:
            lost = True
            lost_count += 1

        if lost:
            c = 1
            tc = 0
            with open('db.json', 'r') as db:
                names = json.load(db)
                for name, score in names.items():
                    tc += 1
                    if score is not None and score > player.score:
                        c += 1
            with open('db.json', 'w') as db:
                names[name] = player.score
                json.dump(names, db)
            run = False
            title_font = pygame.font.SysFont("comicsans", 40)
            title_label = title_font.render("YOU DIED! Your Score: "+str(player.score), 1, (255, 255, 255))
            score_label = title_font.render("Your rank: " + str(c) + " out of " + str(tc), 1, (255, 255, 255))
            print(WIDTH / 2 - title_label.get_width() / 2, HEIGHT // 2)
            WIN.blit(title_label, (WIDTH // 2 - title_label.get_width() / 2, HEIGHT//2))
            WIN.blit(score_label, (WIDTH // 2 - score_label.get_width() / 2, HEIGHT//2 + title_label.get_width()))
            pygame.display.update()
            time.sleep(7)
            continue

        if len(enemies) == 0:
            level += 1
            for i in range(wave_length):
                enemy = Enemy(random.randrange(50, WIDTH-100), random.randrange(-1500, -100), random.choice(["red", "blue", "green"]))
                enemies.append(enemy)
            wave_length += 3

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                quit()

        for enemy in enemies[:]:
            enemy.move(enemy_vel)
            enemy.move_lasers(laser_vel, player, enemy.dmg)

            if random.randrange(0, 2*60) == 1:
                enemy.shoot()

            if collide(enemy, player):
                player.health -= enemy.dmg
                break_sound.play()
                enemies.remove(enemy)
            elif enemy.y + enemy.get_height() > HEIGHT:
                player.health -= enemy.dmg
                enemies.remove(enemy)

        player.move_lasers(-laser_vel, enemies, 0)

def main_menu():
    title_font = pygame.font.SysFont("comicsans", 40)
    name_font = pygame.font.SysFont("comicsans", 70)
    run = True
    width = WIDTH//2
    height = HEIGHT//2
    c = 0
    name = ""


    while run:
        WIN.blit(BG, (0,0))
        pos = 1
        with open('db.json', 'r') as db:
            names = json.load(db)
        if names:
            db = dict(sorted(names.items(), key=itemgetter(1), reverse=True))
            top = list(db.keys())[:3]
            title_label = title_font.render("LEADERBOARD", 1, (255, 215, 0))
            WIN.blit(title_label, (WIDTH / 2 - title_label.get_width() / 2, HEIGHT * 3 / 5))
            gap = 0
            for i in top:
                key_label = title_font.render(str(pos)+'. '+i, 1, (255, 255, 255))
                val_label = title_font.render(str(db[i]) + " Points", 1, (255, 255, 255))
                gap += key_label.get_height()
                WIN.blit(key_label, (WIDTH / 2 - title_label.get_width()*3 / 4, HEIGHT * 3 / 5 + gap + 10))
                WIN.blit(val_label, (WIDTH / 2 + title_label.get_width() / 4, HEIGHT * 3 / 5 + gap + 10))
                pos += 1
        title_label = title_font.render("ENTER NAME", 1, (255,255,255))

        text_box_rect = pygame.Rect(width//2, height//2, width, height//4)
        submit_button_rect = pygame.Rect(width-50, height, 100, 40)
        name_label = name_font.render(name, 1, (0, 0, 0))
        #WIN.blit(title_label, (WIDTH/2 - title_label.get_width()/2, 350))
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                run = False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if submit_button_rect.collidepoint(event.pos):
                    with open('db.json', 'r') as db:
                        names = json.load(db)
                        for uname in names.keys():
                            if uname == name:
                                print('EXISS!')
                                c = 1
                                break
                            else:
                                c = 0
                    if c == 1:
                        continue
                    with open('db.json', 'w') as db:
                        names[name] = 0
                        json.dump(names, db)
                    main(name)

            elif event.type == pygame.KEYDOWN:
                if event.unicode.isalnum() or event.unicode in " _-.":
                    name += event.unicode
                elif event.key == pygame.K_BACKSPACE:
                    name = name[:-1]
        if c == 1:
            err_label = title_font.render("USERNAME EXISTS!", 1, (255, 255, 255))
            WIN.blit(err_label, (width - err_label.get_width() / 2, (HEIGHT // 4) * 3))
        pygame.draw.rect(WIN, (255, 255, 255), text_box_rect)
        pygame.draw.rect(WIN, (255, 255, 255), submit_button_rect)
        WIN.blit(name_label, (width - name_label.get_width() / 2, height // 2 + 10))
        WIN.blit(title_label, (width - title_label.get_width() / 2, height // 4))
        # Draw the user's input in the text input box
        font = pygame.font.SysFont("Arial", 18)
        text = font.render("PLAY!", True, (0, 0, 0))
        WIN.blit(text, (submit_button_rect.x + 25, submit_button_rect.y + 10))
        pygame.display.update()
    pygame.quit()


main_menu()