import asyncio
import pygame
import sys
import time 

# Initialize pygame
pygame.init()

# Setup Screen (Pygbag needs this setup for dynamic fullscreen)
screen = pygame.display.set_mode((0,0)) 
WIDTH, HEIGHT = screen.get_size()
pygame.display.set_caption("Pygbag Menu Example - Fullscreen")

# Globale Spielzustände
verloren = False 
gewonnen = False 
win_display_time = 0 
### NEU ###
current_level = 1 # Startet bei Level 1
MAX_LEVEL = 20 # Definiert die maximale Anzahl an Leveln
### END NEU ###

# Colors
WHITE = (255, 255, 255)
RED = (255, 0, 0)
BLACK = (0, 0, 0)
BLUE = (0, 0, 255)
LIGHT_GREY = (200, 200, 200)

# Clock for controlling FPS
clock = pygame.time.Clock()

# Schriftart
font = pygame.font.SysFont('Arial', 74)
menu_font = pygame.font.SysFont('Arial', 50)

# --- SPIELZUSTÄNDE (vereinfacht) ---
MENU = 0
GAME = 1
QUIT_GAME = 2
game_state = MENU

FRAME_WIDTH = 64
FRAME_HEIGHT = 68
PLAYER_WIDTH = 96
PLAYER_HEIGHT = 128 
GEGNER_WIDTH = 96
GEGNER_HEIGHT = 128

# --- Hintergrundbilder laden (unverändert) ---
background_image = None
try:
    background_image_raw = pygame.image.load('assets/controller.jpg').convert()
    background_image = pygame.transform.scale(background_image_raw, (WIDTH, HEIGHT))
except pygame.error as e:
    print(f"Fehler beim Laden des Hintergrundbilds (controller.jpg): {e}. Es wird ein weißer Hintergrund verwendet.")
    
siegBild = None
verlorenBild = None
try:
    siegBild = pygame.image.load('assets/golden_trophy.png').convert_alpha()
    siegBild = pygame.transform.scale(siegBild, (int(WIDTH * 0.5), int(HEIGHT * 0.5))) 
    verlorenBild = pygame.image.load('assets/lose.png').convert_alpha()
    verlorenBild = pygame.transform.scale(verlorenBild, (int(WIDTH * 0.5), int(HEIGHT * 0.5))) 
except pygame.error as e:
    print(f"Fehler beim Laden der Trophäen-Bilder: {e}. Es wird keine Anzeige erfolgen.")


# >>> GLOBALE HERZ-ASSETS <<<
ganz_herz = None
halb_herz = None 
leer_herz = None 
HERZ_SIZE = 30 # Deutlich kleiner

try:
    ganz_herz_raw = pygame.image.load('assets/voll.png').convert_alpha()
    halb_herz_raw = pygame.image.load('assets/halb.png').convert_alpha()
    leer_herz_raw = pygame.image.load('assets/leer.png').convert_alpha()
    
    # Skalierung
    ganz_herz = pygame.transform.scale(ganz_herz_raw, (HERZ_SIZE, HERZ_SIZE))
    halb_herz = pygame.transform.scale(halb_herz_raw, (HERZ_SIZE, HERZ_SIZE))
    leer_herz = pygame.transform.scale(leer_herz_raw, (HERZ_SIZE, HERZ_SIZE))
    
except pygame.error as e:
    print(f"Warnung: Herz-Assets (voll/halb/leer.png) nicht gefunden. Lebensanzeigen über Figuren deaktiviert. {e}")
# >>> ENDE GLOBALE HERZ-ASSETS <<<

# --- SPIELER ASSETS (unverändert) ---
def get_sprite(sheet, column, row):
    x = column * FRAME_WIDTH
    y = row * FRAME_HEIGHT
    sprite_rect = pygame.Rect(x, y, FRAME_WIDTH, FRAME_HEIGHT)
    image = sheet.subsurface(sprite_rect)
    image = pygame.transform.scale(image, (PLAYER_WIDTH, PLAYER_HEIGHT))
    return image

try:
    spritesheet_image = pygame.image.load('assets/daxbotsheet.png').convert_alpha()
    rechtsGehen = [get_sprite(spritesheet_image, i, 0) for i in range(4)]
    linksGehen = [pygame.transform.flip(frame, True, False) for frame in rechtsGehen] 
    stehenRechts = get_sprite(spritesheet_image, 1, 3) 
    stehenLinks = pygame.transform.flip(stehenRechts, True, False)
    gegnerRechtsGehen = rechtsGehen
    gegnerLinksGehen = linksGehen
except pygame.error as e:
    print(f"FEHLER: Spritesheet 'daxbotsheet.png' nicht gefunden! Fallback aktiv. {e}")
    rechtsGehen = [pygame.Surface((PLAYER_WIDTH, PLAYER_HEIGHT), pygame.SRCALPHA)] * 4
    linksGehen = [pygame.Surface((PLAYER_WIDTH, PLAYER_HEIGHT), pygame.SRCALPHA)] * 4
    stehenRechts = pygame.Surface((PLAYER_WIDTH, PLAYER_HEIGHT), pygame.SRCALPHA)
    stehenLinks = pygame.Surface((PLAYER_WIDTH, PLAYER_HEIGHT), pygame.SRCALPHA)
    

# ZENTRALE FUNKTION ZUM ZEICHNEN DER LEBENSANZEIGE (unverändert)
def draw_health_bar_hearts(current_life, max_total_life, max_hearts, entity_x, entity_y, entity_width, entity_height, allow_half_hearts=False):
    """
    Zeichnet eine Herz-Lebensanzeige über einer Entität.
    """
    if not ganz_herz or max_hearts <= 0:
        return

    # Um Rundungsfehler zu vermeiden, hier immer float
    life_per_heart = max_total_life / max_hearts 
    
    SPACING = 5
    HEART_SIZE = ganz_herz.get_width()
    
    total_width = (max_hearts * HEART_SIZE) + ((max_hearts - 1) * SPACING)
    
    # Zentriere die Herzen über dem Kopf der Figur
    START_X = entity_x + (entity_width // 2) - (total_width // 2)
    START_Y = entity_y - HEART_SIZE - 5 
    
    for i in range(max_hearts):
        x = START_X + i * (HEART_SIZE + SPACING)
        
        # Berechne, wie viel Leben dieser Herz-Slot noch darstellt
        points_for_this_heart = current_life - (i * life_per_heart)
        
        if points_for_this_heart >= life_per_heart:
            # Volles Herz
            screen.blit(ganz_herz, (x, START_Y))
        elif allow_half_hearts and points_for_this_heart >= (life_per_heart / 2):
            # Halbes Herz (nur wenn erlaubt)
            screen.blit(halb_herz, (x, START_Y))
        else:
            # Leeres Herz
            screen.blit(leer_herz, (x, START_Y))
    
    
class Gegner:
    # NEU: max_hearts, allow_half_hearts, schuss_interval (ms) als Parameter
    def __init__(self, x, y, geschw, min_x, max_x, max_life, max_hearts, allow_half_hearts, schuss_interval):
        self.x = x
        self.y = y
        self.geschw = geschw
        self.min_x = min_x
        self.max_x = max_x
        self.breite = GEGNER_WIDTH
        self.hoehe = GEGNER_HEIGHT
        self.richtung = 1
        self.schritte = 0
        self.rect = pygame.Rect(self.x, self.y, self.breite, self.hoehe)

        # NEUE PARAMETER
        self.max_leben = max_life 
        self.leben = max_life
        self.max_hearts = max_hearts
        self.allow_half_hearts = allow_half_hearts
        self.schuss_interval = schuss_interval
        self.letzter_schuss = pygame.time.get_ticks()

        self.besiegt = False
        

    def bewegen(self):
        if self.besiegt:
            return
            
        if self.x + self.breite >= self.max_x:
            self.richtung = -1
        elif self.x <= self.min_x:
            self.richtung = 1
            
        self.x += self.geschw * self.richtung
        self.rect.x = self.x
        self.schritte += 1

    def schiessen(self, current_time):
        """Erzeugt eine Kugel, wenn das Intervall erreicht ist."""
        global gegnerKugeln

        if self.besiegt:
            return

        if current_time - self.letzter_schuss > self.schuss_interval:
            gegner_kugel_x = round(self.x + (self.breite // 2))
            gegner_kugel_y = round(self.y + self.hoehe)
            # Wichtig: Geschw muss positiv sein (nach unten)
            gegnerKugeln.append(kugel(gegner_kugel_x, gegner_kugel_y, 8, BLUE, 5)) # Geschw von 10 auf 5 reduziert, damit es fairer ist
            self.letzter_schuss = current_time

    def gegnerZeichnen(self):
        if self.besiegt:
            return
            
        ANIMATION_SPEED = 8
        index = (self.schritte // ANIMATION_SPEED) % len(gegnerRechtsGehen)
        
        if self.richtung == 1:
            screen.blit(gegnerRechtsGehen[index], (self.x, self.y))
        else:
            screen.blit(gegnerLinksGehen[index], (self.x, self.y))
            
        # Aufruf der zentralen Funktion mit den individuellen Werten des Gegners
        draw_health_bar_hearts(
            self.leben, 
            self.max_leben, 
            self.max_hearts, 
            self.x, self.y, self.breite, self.hoehe, 
            allow_half_hearts=self.allow_half_hearts
        )
        
        
class spieler:
    # ... (Spieler-Klasse unverändert, nutzt 3 Leben, 3 Herzen, keine halben)
    def __init__(self, x, y, geschw, breite, richtg, schritteRechts, schritteLinks):
        self.x = x
        self.y = y
        self.geschw = geschw
        self.breite = breite
        self.richtg = richtg
        self.hoehe = PLAYER_HEIGHT
        self.schritteRechts = schritteRechts
        self.schritteLinks = schritteLinks
        self.sprung = False
        self.last = [1, 0]
        self.ok = True
        self.rect = pygame.Rect(self.x, self.y, self.breite, self.hoehe)
        
        self.max_leben = 3 
        self.leben = self.max_leben
        self.ist_tot = False

    def laufen(self, liste):
        if liste[0]:
            self.x -= self.geschw
            self.richtg = [1, 0, 0, 0]
            self.schritteLinks += 1
        if liste[1]:
            self.x += self.geschw
            self.richtg = [0, 1, 0, 0]
            self.schritteRechts += 1
            
        self.rect.x = self.x 
        self.rect.y = self.y

    def resetSchritte(self):
        self.schritteRechts = 0
        self.schritteLinks = 0

    def stehen(self):
        self.richtg = [0, 0, 1, 0]
        self.resetSchritte()

    def spZeichnen(self):
        ANIMATION_SPEED = 6 
        
        if self.richtg[2]: 
            if self.last[0]:
                screen.blit(stehenLinks, (self.x, self.y))
            else:
                screen.blit(stehenRechts, (self.x, self.y))

        elif self.richtg[0]:
            index = (self.schritteLinks // ANIMATION_SPEED) % len(linksGehen)
            screen.blit(linksGehen[index], (self.x, self.y))
            self.last = [1, 0]

        elif self.richtg[1]:
            index = (self.schritteRechts // ANIMATION_SPEED) % len(rechtsGehen)
            screen.blit(rechtsGehen[index], (self.x, self.y))
            self.last = [0, 1] 
            
        if not self.ist_tot:
            draw_health_bar_hearts(
                self.leben, 
                self.max_leben, 
                3, # Max. 3 Herzen
                self.x, self.y, self.breite, self.hoehe, 
                allow_half_hearts=False # Keine halben Herzen
            )
            
class kugel:
    def __init__(self, spX, spY, radius, farbe, geschw):
        self.x = spX
        self.y = spY
        self.geschw = geschw
        self.radius = radius
        self.farbe = farbe

    def bewegen(self):
        self.y += self.geschw 

    def zeichnen(self):
        kugel_rect = pygame.Rect(self.x - self.radius, self.y - self.radius, self.radius * 2, self.radius * 2)
        pygame.draw.circle(screen, self.farbe, (self.x, self.y), self.radius, 0)
        
# NEU: Kollision mit allen Gegnern
def Kollision():
    global kugeln, gewonnen, verloren, win_display_time, gegner_liste
    
    # 1. Kollision Spielerkugel <-> Gegner
    for gegner in list(gegner_liste):
        if gegner.besiegt:
            continue
            
        # Kollisionsrechteck des Gegners (kleinere Hitbox)
        gegnerRechteck = pygame.Rect(gegner.x + 18, gegner.y + 35, gegner.breite - 36, gegner.hoehe - 35)

        for k in list(kugeln):
            kugelRechteck = pygame.Rect(k.x - k.radius, k.y - k.radius, k.radius * 2, k.radius * 2)
            
            if gegnerRechteck.colliderect(kugelRechteck):
                if k in kugeln:
                    kugeln.remove(k)
                
                gegner.leben -= 1 
                
                if gegner.leben <= 0:
                    gegner.besiegt = True
                    # Prüfe, ob alle Gegner besiegt sind
                    if all(g.besiegt for g in gegner_liste):
                        ### GEWINN-LOGIK HIER ENTSCHÄRFEN, damit nur Levelende erkannt wird!
                        #gewonnen = True
                        win_display_time = pygame.time.get_ticks()

    # 2. Kollision Gegnerkugel <-> Spieler
    if not spieler1.ist_tot:
        for k_gegner in list(gegnerKugeln):
            kugelRechteck = pygame.Rect(k_gegner.x - k_gegner.radius, k_gegner.y - k_gegner.radius, k_gegner.radius * 2, k_gegner.radius * 2)
            
            if spieler1.rect.colliderect(kugelRechteck):
                 if k_gegner in gegnerKugeln:
                    gegnerKugeln.remove(k_gegner)
                     
                    spieler1.leben -= 1
                     
                    if spieler1.leben <= 0:
                        spieler1.ist_tot = True
                        verloren = True
                        win_display_time = pygame.time.get_ticks()
            
def kugelHandler(kugeln_liste):
    global HEIGHT

    for k in list(kugeln_liste): 
        k.bewegen()
        
        if k.y < -100 or k.y > HEIGHT + 100:
            kugeln_liste.remove(k)
        
class Button:
    # ... (Button-Klasse unverändert)
    def __init__(self, text, x, y, width, height, color, hover_color, text_color, action=None):
        self.text = text
        self.rect = pygame.Rect(x, y, width, height)
        self.color = color
        self.hover_color = hover_color
        self.action = action
        self.text_color = text_color
        self.text_surface_normal = menu_font.render(text, True, self.text_color)
        
        hover_text_color = self.text_color
        if self.color is None:
            hover_text_color = WHITE 
        
        self.text_surface_hover = menu_font.render(text, True, hover_text_color)
        self.text_rect = self.text_surface_normal.get_rect(center=self.rect.center)
        

    def draw(self, surface, mouse_pos):
        current_color = self.color
        current_text_surface = self.text_surface_normal
        
        if self.rect.collidepoint(mouse_pos):
            current_color = self.hover_color
            current_text_surface = self.text_surface_hover 
        
        if current_color is not None:
            pygame.draw.rect(surface, current_color, self.rect)
        
        surface.blit(current_text_surface, self.text_rect)

    def is_clicked(self, mouse_pos):
        return self.rect.collidepoint(mouse_pos)

### NEU: LEVEL KONFIGURATION ###
# Definition der Level-Daten als Liste von Dictionaries
LEVEL_CONFIG = {
    # --- PHASE 1: Einführung & Basis-Herausforderung (Level 1-5) ---
    1: [ # Einziger, sehr einfacher Gegner (Starter)
        {"x_factor": 0.25, "max_life": 4, "max_hearts": 2, "allow_half": True, "geschw": 3, "interval": 2500, "count": 1},
    ],
    2: [ # Zwei mittelschwere Gegner (Geschwindigkeits-Test)
        {"x_factor": 0.25, "max_life": 6, "max_hearts": 3, "allow_half": False, "geschw": 4, "interval": 1800, "count": 1},
        {"x_factor": 0.75, "max_life": 5, "max_hearts": 3, "allow_half": True, "geschw": 6, "interval": 1000, "count": 1},
    ],
    3: [ # Ein starker Boss-Gegner (Boss 1)
        {"x_factor": 0.5, "max_life": 20, "max_hearts": 4, "allow_half": True, "geschw": 2, "interval": 800, "count": 1}
    ],
    4: [ # Drei langsame, aber zähe Gegner
        {"x_factor": 0.2, "max_life": 8, "max_hearts": 4, "allow_half": False, "geschw": 2, "interval": 2000, "count": 1},
        {"x_factor": 0.5, "max_life": 8, "max_hearts": 4, "allow_half": False, "geschw": 2, "interval": 2000, "count": 1},
        {"x_factor": 0.8, "max_life": 8, "max_hearts": 4, "allow_half": False, "geschw": 2, "interval": 2000, "count": 1},
    ],
    5: [ # Zwei schnelle Gegner mit mittlerem Leben
        {"x_factor": 0.35, "max_life": 10, "max_hearts": 5, "allow_half": True, "geschw": 7, "interval": 1500, "count": 1},
        {"x_factor": 0.65, "max_life": 10, "max_hearts": 5, "allow_half": True, "geschw": 7, "interval": 1500, "count": 1},
    ],

    # -------------------------------------------------------------------
    
    # --- PHASE 2: Vertiefung & Koordination (Level 6-10) ---
    6: [ # Wellen: Ein schneller Schütze, geschützt durch einen langsamen Tank
        {"x_factor": 0.2, "max_life": 15, "max_hearts": 3, "allow_half": True, "geschw": 1, "interval": 2500, "count": 1},
        {"x_factor": 0.7, "max_life": 6, "max_hearts": 3, "allow_half": False, "geschw": 8, "interval": 900, "count": 1},
    ],
    7: [ # Drei sehr schnelle 'Flitzer'
        {"x_factor": 0.1, "max_life": 4, "max_hearts": 2, "allow_half": True, "geschw": 10, "interval": 1600, "count": 1},
        {"x_factor": 0.5, "max_life": 4, "max_hearts": 2, "allow_half": True, "geschw": 10, "interval": 1600, "count": 1},
        {"x_factor": 0.9, "max_life": 4, "max_hearts": 2, "allow_half": True, "geschw": 10, "interval": 1600, "count": 1},
    ],
    8: [ # Boss-Level 2: Höheres Leben, aber sehr langsame Bewegung
        {"x_factor": 0.5, "max_life": 30, "max_hearts": 5, "allow_half": False, "geschw": 1, "interval": 700, "count": 1}
    ],
    9: [ # Drei mittelschwere, synchrone Gegner
        {"x_factor": 0.25, "max_life": 12, "max_hearts": 3, "allow_half": True, "geschw": 5, "interval": 1300, "count": 1},
        {"x_factor": 0.5, "max_life": 12, "max_hearts": 3, "allow_half": True, "geschw": 5, "interval": 1300, "count": 1},
        {"x_factor": 0.75, "max_life": 12, "max_hearts": 3, "allow_half": True, "geschw": 5, "interval": 1300, "count": 1},
    ],
    10: [ # Zwei zähe Gegner, einer schnell, einer langsam
        {"x_factor": 0.3, "max_life": 18, "max_hearts": 4, "allow_half": False, "geschw": 8, "interval": 1200, "count": 1},
        {"x_factor": 0.7, "max_life": 22, "max_hearts": 5, "allow_half": True, "geschw": 3, "interval": 1500, "count": 1},
    ],

    # -------------------------------------------------------------------

    # --- PHASE 3: Herausforderung & Dichte (Level 11-15) ---
    11: [ # Ein sehr schneller, einzelner Schütze mit mittlerem Leben
        {"x_factor": 0.5, "max_life": 15, "max_hearts": 3, "allow_half": True, "geschw": 12, "interval": 800, "count": 1}
    ],
    12: [ # Vier schwächere Gegner, die den Schirm füllen
        {"x_factor": 0.15, "max_life": 6, "max_hearts": 3, "allow_half": False, "geschw": 4, "interval": 1700, "count": 1},
        {"x_factor": 0.4, "max_life": 6, "max_hearts": 3, "allow_half": False, "geschw": 4, "interval": 1700, "count": 1},
        {"x_factor": 0.65, "max_life": 6, "max_hearts": 3, "allow_half": False, "geschw": 4, "interval": 1700, "count": 1},
        {"x_factor": 0.9, "max_life": 6, "max_hearts": 3, "allow_half": False, "geschw": 4, "interval": 1700, "count": 1},
    ],
    13: [ # Zwei Tank-Gegner mit halben Herzen (lange Überlebenszeit)
        {"x_factor": 0.3, "max_life": 25, "max_hearts": 5, "allow_half": True, "geschw": 4, "interval": 1600, "count": 1},
        {"x_factor": 0.7, "max_life": 25, "max_hearts": 5, "allow_half": True, "geschw": 4, "interval": 1600, "count": 1},
    ],
    14: [ # Ein schneller und ein stationärer, aber schnell feuernder Gegner
        {"x_factor": 0.3, "max_life": 10, "max_hearts": 5, "allow_half": False, "geschw": 10, "interval": 1200, "count": 1},
        {"x_factor": 0.7, "max_life": 10, "max_hearts": 5, "allow_half": False, "geschw": 0, "interval": 600, "count": 1}, # Geschw 0 = stationär
    ],
    15: [ # Boss-Level 3: Höhere Leben, sehr schnelle Schussfolge
        {"x_factor": 0.5, "max_life": 40, "max_hearts": 8, "allow_half": True, "geschw": 3, "interval": 500, "count": 1}
    ],

    # -------------------------------------------------------------------

    # --- PHASE 4: Endgame & Finale (Level 16-20) ---
    16: [ # Vier zufällig platzierte, mittelschwere Gegner
        {"x_factor": 0.1, "max_life": 15, "max_hearts": 3, "allow_half": False, "geschw": 6, "interval": 1300, "count": 1},
        {"x_factor": 0.3, "max_life": 15, "max_hearts": 3, "allow_half": False, "geschw": 6, "interval": 1300, "count": 1},
        {"x_factor": 0.6, "max_life": 15, "max_hearts": 3, "allow_half": False, "geschw": 6, "interval": 1300, "count": 1},
        {"x_factor": 0.8, "max_life": 15, "max_hearts": 3, "allow_half": False, "geschw": 6, "interval": 1300, "count": 1},
    ],
    17: [ # Ein extrem zäher Tank mit langsamer Bewegung
        {"x_factor": 0.5, "max_life": 50, "max_hearts": 10, "allow_half": True, "geschw": 1, "interval": 1800, "count": 1}
    ],
    18: [ # Ein schneller Schütze und ein Tank-Gegner mit sehr schnellem Schuss
        {"x_factor": 0.25, "max_life": 10, "max_hearts": 5, "allow_half": True, "geschw": 10, "interval": 800, "count": 1},
        {"x_factor": 0.75, "max_life": 30, "max_hearts": 5, "allow_half": False, "geschw": 5, "interval": 400, "count": 1},
    ],
    19: [ # Drei starke Gegner, die sich schnell bewegen und hart treffen
        {"x_factor": 0.15, "max_life": 20, "max_hearts": 4, "allow_half": True, "geschw": 8, "interval": 1000, "count": 1},
        {"x_factor": 0.5, "max_life": 20, "max_hearts": 4, "allow_half": True, "geschw": 8, "interval": 1000, "count": 1},
        {"x_factor": 0.85, "max_life": 20, "max_hearts": 4, "allow_half": True, "geschw": 8, "interval": 1000, "count": 1},
    ],
    20: [ # ENDBOSS: Sehr hohes Leben, viele Herzen, schnelle Bewegung, extrem schneller Schuss
        {"x_factor": 0.5, "max_life": 80, "max_hearts": 10, "allow_half": True, "geschw": 6, "interval": 300, "count": 1}
    ]
}


# NEU: Funktion zur Initialisierung der Gegner (abhängig vom Level)
def setup_enemies(level):
    """Erstellt die Gegner-Instanzen basierend auf der Level-Konfiguration."""
    
    if level not in LEVEL_CONFIG:
        print(f"Level {level} nicht gefunden, verwende Level 1.")
        level = 1
        
    config_list = LEVEL_CONFIG[level]
    new_enemies = []
    
    GEGNER_Y = 100
    GEGNER_BEREICH_LINKS = 20
    GEGNER_BEREICH_RECHTS = WIDTH - 20

    for config in config_list:
        start_x = int(WIDTH * config["x_factor"]) - (GEGNER_WIDTH // 2)
        
        # Sicherstellen, dass Start_X im Bereich liegt
        start_x = max(GEGNER_BEREICH_LINKS, min(start_x, GEGNER_BEREICH_RECHTS - GEGNER_WIDTH))
        
        for _ in range(config["count"]):
            # Das min_x und max_x sollte auch abhängig vom Gegner festgelegt werden,
            # aber für eine einfache Patrouille verwenden wir den gesamten Bereich.
            g = Gegner(
                x=start_x, 
                y=GEGNER_Y, 
                geschw=config["geschw"], 
                min_x=GEGNER_BEREICH_LINKS, 
                max_x=GEGNER_BEREICH_RECHTS,
                max_life=config["max_life"], 
                max_hearts=config["max_hearts"], 
                allow_half_hearts=config["allow_half"],
                schuss_interval=config["interval"]
            )
            new_enemies.append(g)
            
    return new_enemies


def reset_game():
    """Setzt alle Spielvariablen und Objekte auf ihren Ausgangszustand zurück."""
    global spieler1, gegner_liste, kugeln, gegnerKugeln, verloren, gewonnen, game_start_time, win_display_time, current_level

    # Level bei echtem Reset (von Menü) auf 1 setzen
    current_level = 1 
    verloren = False
    gewonnen = False # 'Gewonnen' ist nur für den gesamten Sieg
    win_display_time = 0
    
    
    spieler1.x = WIDTH // 2 - PLAYER_WIDTH // 2
    spieler1.y = spieler_start_y
    spieler1.rect.x = spieler1.x
    spieler1.rect.y = spieler1.y
    spieler1.stehen()
    spieler1.ok = True
    
    spieler1.leben = spieler1.max_leben
    spieler1.ist_tot = False
    
    # NEU: Initialisierung der Gegner-Liste
    gegner_liste = setup_enemies(current_level)

    kugeln.clear()
    gegnerKugeln.clear()

    game_start_time = pygame.time.get_ticks()
    
    
### NEU: Funktion zum Laden des nächsten Levels ###
def load_next_level():
    """Läd das nächste Level, falls verfügbar."""
    global current_level, gegner_liste, kugeln, gegnerKugeln, gewonnen
    
    current_level += 1
    
    if current_level > MAX_LEVEL:
        # Endgültiger Sieg!
        gewonnen = True
        return 
        
    # Setze Level-spezifische Dinge zurück
    gegner_liste = setup_enemies(current_level)
    kugeln.clear()
    gegnerKugeln.clear()
    
    # Der Spieler bleibt an seiner Position, Leben wird nicht zurückgesetzt (schwieriger!)
    # Falls das Leben zurückgesetzt werden soll: spieler1.leben = spieler1.max_leben


TEXT_COLOR = BLACK 
button_width, button_height = 300, 60
button_x = (WIDTH - button_width) // 2
button_y_start = HEIGHT // 2

singleplayer_button = Button(
    "Spiel starten", 
    button_x, button_y_start, 
    button_width, button_height, 
    LIGHT_GREY, WHITE, 
    TEXT_COLOR, 
    action="start_game"
)
quit_button = Button(
    "exit", 
    10, 10, 
    100, 50, 
    None, RED, 
    TEXT_COLOR, 
    action="start_game"
)
menu_buttons = [singleplayer_button]


def draw_menu(mouse_pos):
    """Zeichnet den Menü-Bildschirm"""
    screen.fill(BLACK)
    
    title_surface = font.render("Battle Bots", True, WHITE)
    title_rect = title_surface.get_rect(center=(WIDTH // 2, HEIGHT // 4))
    screen.blit(title_surface, title_rect)
    
    for button in menu_buttons:
        button.draw(screen, mouse_pos)
        
    pygame.display.flip()
    

def draw_game():
    global gewonnen, siegBild, verlorenBild
    
    
    if background_image:
        screen.blit(background_image, (0, 0))
    else:
        screen.fill(BLACK)
    
    # Zeichne Kugeln
    for k in kugeln:
        k.zeichnen()
        
    for k in gegnerKugeln:
        k.zeichnen()
        
    quit_button.draw(screen, pygame.mouse.get_pos())
    
    if not spieler1.ist_tot:
        spieler1.spZeichnen() 
    
    # Zeichne alle Gegner
    for gegner in gegner_liste:
        if not gegner.besiegt:
            gegner.gegnerZeichnen()
            # Zeichne Hitboxen (für Debugging)
            # pygame.draw.rect(screen, (255, 255, 0), gegner.rect, 2)
    
    # Spieler Hitbox
    # pygame.draw.rect(screen, RED, spieler1.rect, 2)
    
    
    # Timer-Anzeige (oben rechts)
    elapsed_time = pygame.time.get_ticks() - game_start_time
    # NEU: Level-Anzeige
    time_text = menu_font.render(f"Level: {current_level} - Zeit: {elapsed_time / 1000:.2f} s", True, WHITE) 
    screen.blit(time_text, (WIDTH - 550, 10))
    
    # Sieg/Verloren-Bildschirm
    if gewonnen and siegBild:
        win_text = font.render("ENDSIEG!", True, (0, 255, 0))
        win_rect = win_text.get_rect(center=(WIDTH // 2, HEIGHT // 4))
        trophy_rect = siegBild.get_rect(center=(WIDTH // 2, HEIGHT // 2))
        
        screen.blit(siegBild, trophy_rect)
        screen.blit(win_text, win_rect)
        
    elif verloren and verlorenBild:
        loss_text = font.render("VERLOREN!", True, RED)
        loss_rect = loss_text.get_rect(center=(WIDTH // 2, HEIGHT // 4))
        trophy_rect = verlorenBild.get_rect(center=(WIDTH // 2, HEIGHT // 2)) 
        
        screen.blit(verlorenBild, trophy_rect)
        screen.blit(loss_text, loss_rect)
        
    pygame.display.flip()
    

# Wände als einfache Rect-Objekte für die Kollision
linkeWand = pygame.Rect(-1, 0, 2, HEIGHT)
rechteWand = pygame.Rect(WIDTH - 1, 0, 2, HEIGHT)

# Initialisierung der Hauptobjekte
spieler_start_y = HEIGHT - PLAYER_HEIGHT - 70
spieler1 = spieler(WIDTH // 2 - PLAYER_WIDTH // 2, spieler_start_y, 6, PLAYER_WIDTH, [0, 0, 1, 0], 0, 0)

kugeln = []
gegnerKugeln = []

# Globale Liste für alle Gegner (wird in reset_game() initialisiert)
gegner_liste = setup_enemies(current_level)

# Globale Variable für die Startzeit
game_start_time = 0

# Async main loop (required by pygbag)
async def main():
    global game_state, running, gewonnen, verloren, win_display_time
    running = True

    WIN_SCREEN_DURATION = 2000 # Dauer für den Level-Ende-Bildschirm
    FINAL_WIN_SCREEN_DURATION = 5000 # Dauer für den End-Sieg-Bildschirm
    LOSS_SCREEN_DURATION = 3000 

    while running:
        mouse_pos = pygame.mouse.get_pos()
        current_time = pygame.time.get_ticks()

        # --- Event Handling ---
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if game_state == MENU:
                    for button in menu_buttons:
                        if button.is_clicked(mouse_pos):
                            if button.action == "start_game":
                                reset_game() 
                                game_state = GAME
                elif game_state == GAME and quit_button.is_clicked(mouse_pos):
                    game_state = MENU
                    
            
        # --- Zustandsspezifische Logik ---
        if game_state == MENU:
            draw_menu(mouse_pos)
            
        elif game_state == GAME:
            
            if gewonnen: # Endgültiger Sieg
                draw_game() 
                if current_time - win_display_time > FINAL_WIN_SCREEN_DURATION:
                    game_state = MENU 
                    reset_game() 
                    
            elif verloren: 
                draw_game()

                if current_time - win_display_time > LOSS_SCREEN_DURATION:
                    game_state = MENU 
                    reset_game() 
                
            elif all(g.besiegt for g in gegner_liste): # Alle Gegner dieses Levels besiegt
                # NEU: Hier Level-Wechsel-Logik einfügen
                if current_level < MAX_LEVEL:
                    # Kurze Pause (Level-Ende-Text anzeigen)
                    win_text = font.render(f"Level {current_level} Geschafft!", True, (255, 255, 0))
                    win_rect = win_text.get_rect(center=(WIDTH // 2, HEIGHT // 2))
                    screen.blit(win_text, win_rect)
                    pygame.display.flip()
                    await asyncio.sleep(WIN_SCREEN_DURATION / 1000) # Wartezeit
                    
                    load_next_level() # Lade nächstes Level
                else:
                    # Sollte eigentlich nicht erreicht werden, da "gewonnen" Flag gesetzt wird
                    gewonnen = True 
                    win_display_time = current_time
                    
            else: # Aktives Spiel
                # 1. Spieler-Logik
                keys = pygame.key.get_pressed()
                bewegt = False
                
                if keys[pygame.K_LEFT] and not spieler1.rect.colliderect(linkeWand):
                    spieler1.laufen([1, 0])
                    bewegt = True
                
                elif keys[pygame.K_RIGHT] and not spieler1.rect.colliderect(rechteWand):
                    spieler1.laufen([0, 1])
                    bewegt = True
                    
                if keys[pygame.K_SPACE]:
                    # Kugelgeschw von -10 auf -15 erhöht für mehr Reichweite
                    if len(kugeln) <= 3 and spieler1.ok:
                        kugel_x = round(spieler1.x + (spieler1.breite // 2)) 
                        kugel_y = round(spieler1.y)
                        kugeln.append(kugel(kugel_x, kugel_y, 8, RED, -15)) 
                        spieler1.ok = False

                if not keys[pygame.K_SPACE]:
                    spieler1.ok = True
                
                if not bewegt:
                    spieler1.stehen()
                
                # 2. Gegner-Logik
                # NEU: Iteriere über alle Gegner
                for gegner in gegner_liste:
                    if not gegner.besiegt:
                        gegner.bewegen()
                        gegner.schiessen(current_time) 
                
                # 3. Kugel-Handler
                kugelHandler(kugeln) 
                kugelHandler(gegnerKugeln)
                
                # 4. Kollision
                Kollision()
                
                # 5. Zeichnen
                draw_game()
                    
        # Limit FPS
        clock.tick(60)

        # Yield control to browser
        await asyncio.sleep(0)
    
# Run the async loop
asyncio.run(main())