"""
===============================================================================
 R E A K T I O N S S P I E L   -   8x8 RGB-Matrix am MAX1000
===============================================================================

Ein Spiel, welches die Geschwindigkeit der menschlichen Reaktion misset,
samt einem farbigen Bedienbild im Textfenster (TUI).

-------------------------------------------------------------------------------
 DAS BEDIENBILD
-------------------------------------------------------------------------------
Das Textfenster zeiget zu jeder Zeit:

  * einen SPIEGEL der 8x8-Matrix. Was auf der Hardware leuchtet, leuchtet
    zugleich im Fenster. Somit laesset sich das Spiel auch dann verfolgen,
    wenn man die Matrix gerade nicht vor Augen hat.
  * die RUNDENTAFEL mit Balken, Zeiten und Bewertungen
  * eine GROSSANZEIGE, welche den Countdown und hernach die Reaktionszeit
    als grosse Ziffern aufzaehlet
  * eine STATUSZEILE, welche saget, was soeben zu tun ist

-------------------------------------------------------------------------------
 ABLAUF EINER RUNDE
-------------------------------------------------------------------------------
1. WARTEMODUS  - eine ruhige Sinuswelle laeuft. Beliebige Taste startet.
2. AMPEL       - Rot, Orange, Gruen. Alsdann erlischt die Matrix.
3. BLITZ       - nach zufaelliger Weile schiesst eine tuerkise Linie herab.
4. REAKTION    - TAB druecken. Die Zeit wird in Millisekunden gemessen,
                 aufgezaehlt und der Liste angefuegt.
5. FEHLSTART   - wer vor dem Blitz druecket, sieht rotes Blinken; die Runde
                 wird wiederholt und NICHT gewertet.

-------------------------------------------------------------------------------
 SPIELARTEN
-------------------------------------------------------------------------------
  SPIEL     - fuenf gewertete Runden, hernach Statistik und Bestenliste
  TRAINING  - endlos viele Runden ohne Wertung, zum Ueben

-------------------------------------------------------------------------------
 SCHWIERIGKEITSGRADE
-------------------------------------------------------------------------------
  LEICHT - Der Blitz bleibet stehen, bis gedrueckt wird. Wartezeit 2 - 4 s.
  NORMAL - Der Blitz erlischt nach einer Sekunde. Wartezeit 2 - 5 s.
  SCHWER - Der Blitz zucket nur 150 ms lang. Wartezeit 2 - 6 s. Ueberdies
           erscheinen TAEUSCHUNGEN: ein kurzes rotes Aufleuchten, welches
           NICHT gedrueckt werden darf.

-------------------------------------------------------------------------------
 BEWERTUNG
-------------------------------------------------------------------------------
    unter 250 ms .......... BLITZ
    250 bis 500 ms ........ WIND
    ueber 500 ms .......... STEIN

  Wer mehrere BLITZE hintereinander erzielet, baut eine SERIE auf; diese
  wird eigens ausgewiesen.

-------------------------------------------------------------------------------
 BEDIENUNG
-------------------------------------------------------------------------------
  Im Menue:      1 Spiel   2 Training   3 Bestenliste
                 M Schwierigkeit   T Ton   Q Ende
  Im Spiel:      beliebige Taste startet die Runde
                 TAB ist die Reaktionstaste
                 ESC kehret ins Menue zurueck (setzt das Spiel zurueck)
                 Q beendet das Programm
                 Strg+C ist die Notbremse

-------------------------------------------------------------------------------
 VORKEHRUNGEN GEGEN HAENGENBLEIBEN
-------------------------------------------------------------------------------
  a) Der Schnellbearbeitungsmodus der Windows-Konsole wird abgeschaltet.
     Ebendieser haelt sonst das ganze Programm an, sobald jemand mit der
     Maus in das Fenster klicket - der haeufigste Grund fuer ein
     vermeintlich haengendes Konsolenprogramm.
  b) Das Warten auf die Reaktion ist zeitlich begrenzet (Zeitsperre).
  c) Das Senden an die Matrix hat eine Zeitsperre; ein stockender Anschluss
     kostet hoechstens ein Bild, niemals das Spiel.
  d) Der Tastaturpuffer wird bei jedem Wechsel des Abschnittes geleeret.

-------------------------------------------------------------------------------
 AUFRUF
-------------------------------------------------------------------------------
    python reaktionsspiel.py            # nutzt COM10
    python reaktionsspiel.py COM9       # anderer Anschluss
    python reaktionsspiel.py SIM        # ausdruecklich ohne Hardware

  Es wird eine echte Konsole benoetiget (Eingabeaufforderung, PowerShell).
  In einem Jupyter-Notebook kann die Tastatur nicht abgefragt werden.

-------------------------------------------------------------------------------
 SPIELEN OHNE HARDWARE
-------------------------------------------------------------------------------
  Das Spiel setzet keine Hardware voraus. Findet sich beim Start keine
  Matrix - weil keine Platine angesteckt ist, weil ein anderes Programm
  den Anschluss haelt oder weil ausdruecklich 'SIM' verlangt ward -, so
  tritt eine Attrappe an ihre Stelle und das Spiel laeuft vollstaendig
  weiter.

  Gespielt wird alsdann am Matrix-Spiegel des Bedienbildes, welcher jeden
  der 64 Bildpunkte in Farbe darstellet. Sinus, Ampel, Blitz, Taeuschung
  und Ergebnisschau erscheinen ebendort genau wie auf den Leuchtdioden.
  Der Kopfbalken weiset den Betrieb als SIMULATION aus.

-------------------------------------------------------------------------------
 WO WIRD WAS GEMACHT
-------------------------------------------------------------------------------
    Abschnitt  1 ... Einstellungen, Spielarten, Farben
    Abschnitt  2 ... Ansteuerung der Matrix: Klasse RgbMatrixUart
    Abschnitt  3 ... Grundlegende Hilfen zur Matrix
    Abschnitt  4 ... Konsole vorbereiten (Farben, Groesse, Mausklick-Sperre)
    Abschnitt  5 ... Tastatur: Filterung und Ruecksetzung der Eingaben
    Abschnitt  6 ... Bausteine des Bedienbildes (Farben, Kaesten, Grossziffern)
    Abschnitt  7 ... Der Spielstand und das Zeichnen des Bedienbildes
    Abschnitt  8 ... Die Anzeigen auf der Matrix
                     zeige_sinus(), zeige_start(), zeige_blitz()
    Abschnitt  9 ... Messung der Reaktionszeit: messe_reaktion()
    Abschnitt 10 ... Bewertung, Statistik, Bestenliste
    Abschnitt 11 ... Spielablauf: Runde, Spiel, Training
    Abschnitt 12 ... Menue und Hauptprogramm
===============================================================================
"""

import ctypes
import json
import math
import msvcrt
import os
import random
import re
import sys
import time

import serial

try:                        # Der Ton ist erwuenscht, aber nicht unerlaesslich
    import winsound
except ImportError:         # pragma: no cover - nur auf fremden Systemen
    winsound = None


# =============================================================================
# ABSCHNITT 1: EINSTELLUNGEN, SPIELARTEN, FARBEN
# =============================================================================

# --- Anschluss an die Hardware -----------------------------------------------
PORT_STANDARD = 'COM10'      # FTDI-Kanal B des MAX1000 (Alternative: COM9)
BAUDRATE = 921600            # Geschwindigkeit der UART-Schnittstelle
MATRIX_GROESSE = 8           # Die Matrix misset 8 x 8 Leuchtdioden
SENDE_ZEITSPERRE = 1.0       # Sekunden, laenger wird nie auf das Senden gewartet

# --- Spielregeln -------------------------------------------------------------
RUNDEN_ANZAHL = 5                # So viele gewertete Runden hat ein Spiel
REAKTION_ZEITSPERRE_MS = 5000.0  # Laenger wird auf TAB nicht gewartet

# --- Bewertungsgrenzen in Millisekunden --------------------------------------
GRENZE_BLITZ_MS = 250.0      # Darunter: hurtig wie der Blitz
GRENZE_WIND_MS = 500.0       # Darunter: flink wie der Wind, darueber: Stein

# --- Die Schwierigkeitsgrade -------------------------------------------------
# warte        = Bereich der zufaelligen Wartezeit bis zum Blitz (Sekunden)
# sicht_ms     = wie lange der Blitz sichtbar bleibet; None = bis zum Druck
# taeuschung   = Wahrscheinlichkeit eines roten Taeuschungsblitzes (0.0 - 1.0)
MODI = {
    'LEICHT': {'warte': (2.0, 4.0), 'sicht_ms': None,
               'taeuschung': 0.0,
               'text': 'Blitz bleibt stehen'},
    'NORMAL': {'warte': (2.0, 5.0), 'sicht_ms': 1000.0,
               'taeuschung': 0.0,
               'text': 'Blitz erlischt nach 1 s'},
    'SCHWER': {'warte': (2.0, 6.0), 'sicht_ms': 150.0,
               'taeuschung': 0.35,
               'text': 'Blitz nur 150 ms, mit Taeuschungen'},
}
MODUS_REIHE = ['LEICHT', 'NORMAL', 'SCHWER']
MODUS_STANDARD = 'NORMAL'

# --- Farben der Matrix (Werte 0..255; kleine Werte leuchten bereits hell) ----
FARBE_AUS = [0, 0, 0]
FARBE_SINUS = [0, 30, 30]      # Tuerkis, gedaempft, fuer den Wartemodus
FARBE_AMPEL_ROT = [45, 0, 0]
FARBE_AMPEL_ORANGE = [45, 18, 0]
FARBE_AMPEL_GRUEN = [0, 45, 0]
FARBE_BLITZ = [0, 60, 60]      # Tuerkis, hell, der eigentliche Startschuss
FARBE_FEHLSTART = [70, 0, 0]   # Rot, zur Mahnung bei zu fruehem Druck
FARBE_TAEUSCHUNG = [55, 0, 0]  # Rot, die Falle im schweren Grade
FARBE_VERPASST = [45, 30, 0]   # Bernstein, wenn die Reaktion ausbleibt
FARBE_JUBEL = [0, 60, 20]      # Gruen, fuer eine neue Bestzeit

# --- Zeitverhalten der Anzeigen ----------------------------------------------
SINUS_BILDRATE_HZ = 20.0       # Bilder je Sekunde im Wartemodus
SINUS_TEMPO_HZ = 0.35          # Wie gemaechlich die Welle wandert
SINUS_PERIODEN = 1.0           # Anzahl Wellenberge ueber die Breite
SINUS_AMPLITUDE = 3.0          # Ausschlag der Welle in Leuchtdioden

AMPEL_SCHRITT_SEKUNDEN = 0.7   # Dauer je Ampelfarbe
BLITZ_SCHRITT_SEKUNDEN = 0.015  # Dauer je Zeile, waehrend der Blitz faellt
BLINKEN_ANZAHL = 3             # So oft blinket eine Mahnung
BLINKEN_TAKT_SEKUNDEN = 0.15
ZAEHLWERK_SEKUNDEN = 0.55      # Dauer, in welcher die Grossziffern aufzaehlen

# --- Toene (Frequenz in Hertz, Dauer in Millisekunden) ----------------------
TON_AMPEL = [(440, 90), (554, 90), (740, 140)]   # Rot, Orange, Gruen
TON_FEHLSTART = (160, 320)
TON_VERPASST = (220, 260)
TON_ERGEBNIS = {'BLITZ': [(880, 70), (1175, 70), (1568, 140)],
                'WIND': [(660, 80), (880, 120)],
                'STEIN': [(392, 160)]}
TON_REKORD = [(784, 90), (988, 90), (1175, 90), (1568, 220)]

# --- Tastencodes, wie msvcrt sie liefert (Bytes) -----------------------------
TASTE_TAB = b'\t'
TASTE_ESC = b'\x1b'
TASTEN_ENDE = (b'q', b'Q')
TASTEN_VORZEICHEN = (b'\x00', b'\xe0')  # Vorbyte der Sondertasten (F1, Pfeile)

# --- Benennung der Tastenereignisse ------------------------------------------
# Alle Abschnitte des Spieles fragen dieselbe Funktion 'lies_ereignis()'.
# Diese liefert eine dieser Zeichenketten, wodurch die Auswertung der Tasten
# an einer einzigen Stelle geschieht und nicht an vielen verstreuten.
EREIGNIS_KEINS = 'keins'          # Es liegt kein Tastendruck vor
EREIGNIS_REAKTION = 'reaktion'    # TAB wurde gedrueckt
EREIGNIS_ZURUECK = 'zurueck'      # ESC wurde gedrueckt
EREIGNIS_ENDE = 'ende'            # Q wurde gedrueckt
EREIGNIS_ANDERE = 'andere'        # Irgendeine andere Taste

# --- Masse des Bedienbildes --------------------------------------------------
BREITE = 92                  # Gesamtbreite des Bedienbildes in Zeichen
BREITE_LINKS = 26            # Breite des Kastens mit dem Matrix-Spiegel
BREITE_RECHTS = BREITE - BREITE_LINKS   # Breite der Rundentafel

# --- Farben des Bedienbildes (Rot, Gruen, Blau) ------------------------------
TUI_RAHMEN = (71, 85, 105)
TUI_TITEL = (34, 211, 238)
TUI_TEXT = (226, 232, 240)
TUI_MATT = (100, 116, 139)
TUI_BLITZ = (56, 189, 248)
TUI_WIND = (74, 222, 128)
TUI_STEIN = (251, 146, 60)
TUI_WARNUNG = (248, 113, 113)
TUI_GOLD = (250, 204, 21)
TUI_DUNKEL = (30, 41, 59)

BEWERTUNGSFARBEN = {'BLITZ': TUI_BLITZ, 'WIND': TUI_WIND, 'STEIN': TUI_STEIN}

# --- Datei der Bestenliste ---------------------------------------------------
BESTENLISTE_DATEI = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), 'reaktionsspiel_bestenliste.json')
BESTENLISTE_LAENGE = 10      # So viele Eintraege werden aufbewahret

# --- Zustand der Farbausgabe -------------------------------------------------
# Wird von bereite_konsole_vor() gesetzt. Ist keine Konsole vorhanden, so
# werden saemtliche Farbbefehle weggelassen, damit die Ausgabe lesbar bleibet.
FARBEN_MOEGLICH = True

# --- Notbehelf fuer fremde Zeichensaetze -------------------------------------
# Wird die Ausgabe umgeleitet (in eine Datei, eine Weiterleitung oder ein
# Fenster mit altem Zeichensatz), so lassen sich die Rahmen- und Blockzeichen
# nicht darstellen. Alsdann treten diese schlichten Ersatzzeichen an ihre
# Stelle, damit das Spiel gleichwohl weiterlaeuft und nicht abstuerzet.
ERSATZZEICHEN = {
    '╔': '+', '╗': '+', '╚': '+', '╝': '+', '═': '=', '║': '|',
    '┌': '+', '┐': '+', '└': '+', '┘': '+', '─': '-', '│': '|',
    '█': '#', '░': '.', '·': '.', '▶': '>',
}


class SpielZurueck(Exception):
    """
    Wird geworfen, wenn der Spieler mittels ESC das Spiel zuruecksetzen will.
    Das Hauptprogramm faengt diese Ausnahme und kehret ins Menue zurueck.
    """


class SpielEnde(Exception):
    """Wird geworfen, wenn der Spieler mittels Q das Programm beenden will."""


# =============================================================================
# ABSCHNITT 2: ANSTEUERUNG DER MATRIX
# =============================================================================

class RgbMatrixUart:
    """
    Ansteuerung der 8x8 RGB-Matrix ueber die UART-Schnittstelle des MAX1000.

    Das Uebertragungsformat folget der Schnittstelle des FPGA-Aufbaus:
    Je Zeile wird eine Zeichenkette '<zz' + 24 Hexadezimalwerte + '>' gesandt.
    Die Leuchtdioden sind schlangenfoermig verdrahtet, weshalb die Umrechnung
    ueber eine Nachschlagetabelle geschieht, und sie erwarten die Farbfolge
    Gruen-Rot-Blau.

    Zwei Vorzuege machen diese Klasse widerstandsfaehig:
      - eine Zeitsperre beim Senden, damit ein stockender Anschluss das Spiel
        nicht zum Stillstand bringet
      - kein 'sys.exit()' im Fehlerfalle, sondern eine ordentliche Meldung
    """

    NACHSCHLAGETABELLE = [7, 8, 23, 24, 39, 40, 55, 56]

    def __init__(self, port=PORT_STANDARD, baudrate=BAUDRATE):
        """
        Erstellet das Objekt, ohne den Anschluss bereits zu oeffnen.

        :param port: str, Bezeichnung des Anschlusses, z.B. 'COM10'
        :param baudrate: int, Geschwindigkeit der Schnittstelle
        """
        self.port = port
        self.baudrate = baudrate
        self.instanz = None
        self.stoerungen = 0
        self.rgb_matrix = [
            [list(FARBE_AUS) for _ in range(MATRIX_GROESSE)]
            for _ in range(MATRIX_GROESSE)
        ]

    def oeffne(self):
        """
        Oeffnet den Anschluss zur Matrix.

        :raises serial.SerialException: sofern der Anschluss nicht bereit ist
        :return: None
        """
        self.instanz = serial.Serial(
            self.port,
            self.baudrate,
            timeout=0,
            write_timeout=SENDE_ZEITSPERRE,
            parity=serial.PARITY_NONE,
        )

    def schliesse(self):
        """
        Schliesset den Anschluss, sofern er denn offen ist.

        :return: None
        """
        if self.instanz is not None and self.instanz.is_open:
            self.instanz.close()

    def _baue_bytestrom(self):
        """
        Rechnet die Matrix in den schlangenfoermigen Bytestrom um.

        :return: Liste von int, 192 Werte in der Reihenfolge Gruen-Rot-Blau
        """
        strom = [0] * (MATRIX_GROESSE * MATRIX_GROESSE * 3)
        for spalte in range(MATRIX_GROESSE):
            for zeile in range(MATRIX_GROESSE):
                grundstelle = self.NACHSCHLAGETABELLE[spalte]
                if (spalte % 2) == 0:
                    stelle = grundstelle * 3 - (zeile * 3)
                else:
                    stelle = grundstelle * 3 + (zeile * 3)

                farbe = self.rgb_matrix[zeile][spalte]
                strom[stelle + 0] = max(0, min(255, int(farbe[1])))  # Gruen
                strom[stelle + 1] = max(0, min(255, int(farbe[0])))  # Rot
                strom[stelle + 2] = max(0, min(255, int(farbe[2])))  # Blau
        return strom

    def sende(self):
        """
        Sendet das gegenwaertige Bild an die Matrix.

        Bleibt das Senden haengen, so wird nach Ablauf der Zeitsperre der
        Sendepuffer verworfen und weitergespielt. Das Spiel kann somit
        niemals am Anschluss haengenbleiben.

        :return: bool, True bei ordentlicher Uebertragung, sonst False
        """
        strom = self._baue_bytestrom()
        try:
            for zeile in range(MATRIX_GROESSE):
                zeichenkette = '<{0:02x}'.format(zeile)
                anfang = zeile * MATRIX_GROESSE * 3
                for versatz in range(MATRIX_GROESSE * 3):
                    zeichenkette += '{0:02X}'.format(strom[anfang + versatz])
                zeichenkette += '>'
                self.instanz.write(zeichenkette.encode())
            return True

        except serial.SerialTimeoutException:
            self.stoerungen += 1
            self.instanz.reset_output_buffer()
            return False

        except serial.SerialException:
            self.stoerungen += 1
            return False


class RgbMatrixAttrappe:
    """
    Eine Matrix, welche es gar nicht gibt: der Betrieb OHNE Hardware.

    Ist keine Platine angeschlossen - etwa beim Entwickeln unterwegs oder
    wenn der MAX1000 anderweitig gebraucht wird -, so tritt diese Attrappe
    an die Stelle der echten Matrix. Sie bietet dieselben Felder und
    Verrichtungen, sendet jedoch nichts auf die Leitung. Das Spiel laeuft
    dadurch vollstaendig weiter; zu sehen ist alles im Matrix-Spiegel des
    Bedienbildes, welcher ohnehin jeden Bildpunkt darstellet.

    Ebendies ist der Sinn des Spiegels: er ist nicht nur Beiwerk, sondern
    die vollwertige Anzeige, wenn die Leuchtdioden fehlen.
    """

    def __init__(self, port='SIMULATION', baudrate=BAUDRATE):
        """
        Erstellet die Attrappe.

        :param port: str, allein zur Anzeige im Kopfbalken
        :param baudrate: int, wird nicht verwendet, der Gleichform halber
        """
        self.port = port
        self.baudrate = baudrate
        self.instanz = None
        self.stoerungen = 0
        self.gesendete_bilder = 0
        self.rgb_matrix = [
            [list(FARBE_AUS) for _ in range(MATRIX_GROESSE)]
            for _ in range(MATRIX_GROESSE)
        ]

    def oeffne(self):
        """
        Tut nichts, denn es ist nichts zu oeffnen.

        :return: None
        """

    def schliesse(self):
        """
        Tut nichts, denn es ist nichts zu schliessen.

        :return: None
        """

    def sende(self):
        """
        Nimmt das Bild entgegen und zaehlet es, sendet aber nichts.

        :return: bool, immer True
        """
        self.gesendete_bilder += 1
        return True


# =============================================================================
# ABSCHNITT 3: GRUNDLEGENDE HILFEN ZUR MATRIX
# =============================================================================

def faerbe_alles(rgb, farbe):
    """
    Faerbet saemtliche 64 Leuchtdioden in ein und derselben Farbe.

    Das Bild wird allein im Arbeitsspeicher vorbereitet; gesendet wird es
    erst durch den nachfolgenden Aufruf von 'rgb.sende()'.

    :param rgb: RgbMatrixUart, das geoeffnete Objekt der RGB-Matrix
    :param farbe: Liste [R, G, B] mit Werten von 0 bis 255
    :return: None
    """
    for zeile in range(MATRIX_GROESSE):
        for spalte in range(MATRIX_GROESSE):
            rgb.rgb_matrix[zeile][spalte] = list(farbe)


def loesche_matrix(rgb, spielstand=None):
    """
    Loeschet die Matrix und sendet dieses Bild sogleich an die Hardware.

    :param rgb: RgbMatrixUart, das geoeffnete Objekt der RGB-Matrix
    :param spielstand: Spielstand oder None; ist er gegeben, so wird auch
                       das Bedienbild neu gezeichnet
    :return: None
    """
    faerbe_alles(rgb, FARBE_AUS)
    rgb.sende()
    if spielstand is not None:
        zeichne_bild(spielstand, rgb)


def zeige_vollbild(rgb, farbe, dauer_sekunden, spielstand=None):
    """
    Faerbet die ganze Matrix in einer Farbe und haelt das Bild eine Weile.

    :param rgb: RgbMatrixUart, das geoeffnete Objekt der RGB-Matrix
    :param farbe: Liste [R, G, B], die gewuenschte Farbe
    :param dauer_sekunden: float, wie lange das Bild stehen bleibet
    :param spielstand: Spielstand oder None, zum Nachfuehren des Bedienbildes
    :return: None
    """
    faerbe_alles(rgb, farbe)
    rgb.sende()
    if spielstand is not None:
        zeichne_bild(spielstand, rgb)
    time.sleep(dauer_sekunden)


def blinke(rgb, farbe, spielstand=None, anzahl=BLINKEN_ANZAHL):
    """
    Laesset die ganze Matrix mehrmals in einer Farbe aufblinken.

    :param rgb: RgbMatrixUart, das geoeffnete Objekt der RGB-Matrix
    :param farbe: Liste [R, G, B], die Farbe des Blinkens
    :param spielstand: Spielstand oder None, zum Nachfuehren des Bedienbildes
    :param anzahl: int, wie oft geblinket wird
    :return: None
    """
    for _ in range(anzahl):
        zeige_vollbild(rgb, farbe, BLINKEN_TAKT_SEKUNDEN, spielstand)
        zeige_vollbild(rgb, FARBE_AUS, BLINKEN_TAKT_SEKUNDEN, spielstand)
    loesche_matrix(rgb, spielstand)


def spiele_ton(folge, spielstand):
    """
    Spielet eine Folge von Toenen, sofern der Ton eingeschaltet ist.

    Es wird bewusst NIEMALS im Augenblick des Blitzes ein Ton gespielt, da
    ein Ohr schneller ist als ein Auge und die Messung dadurch verfaelscht
    wuerde.

    :param folge: Liste von (Frequenz, Dauer_ms) oder ein einzelnes Paar
    :param spielstand: Spielstand, dessen Feld 'ton_an' befragt wird
    :return: None
    """
    if not spielstand.ton_an or winsound is None:
        return
    if isinstance(folge, tuple):
        folge = [folge]
    try:
        for frequenz, dauer_ms in folge:
            winsound.Beep(int(frequenz), int(dauer_ms))
    except (RuntimeError, ValueError, OSError):
        pass            # Ohne Tonausgabe wird eben stumm gespielt


# =============================================================================
# ABSCHNITT 4: KONSOLE VORBEREITEN
# =============================================================================

def schreibe(text):
    """
    Schreibt Text auf den Bildschirm und ertraeget fremde Zeichensaetze.

    Saemtliche Ausgaben des Spieles laufen ueber ebendiese Stelle. Kann der
    Zeichensatz des Fensters die Rahmen- und Blockzeichen nicht darstellen -
    was bei umgeleiteter Ausgabe geschieht -, so werden sie durch schlichte
    Ersatzzeichen vertreten. Das Spiel stuerzet dadurch niemals an einer
    blossen Darstellungsfrage ab.

    :param text: str, der auszugebende Text
    :return: None
    """
    try:
        sys.stdout.write(text)
        sys.stdout.flush()
    except UnicodeEncodeError:
        ersatz = text
        for zeichen, ersatzzeichen in ERSATZZEICHEN.items():
            ersatz = ersatz.replace(zeichen, ersatzzeichen)
        sys.stdout.write(ersatz.encode('ascii', 'replace').decode('ascii'))
        sys.stdout.flush()


def bereite_konsole_vor(spalten=BREITE + 4, zeilen=32):
    """
    Ruestet das Textfenster fuer das Bedienbild.

    Es geschehen vier Dinge:
      1. Das Fenster wird auf eine taugliche Groesse gebracht.
      2. Die Ausgabe wird auf UTF-8 gestellt, damit Rahmen und Bloecke
         richtig erscheinen.
      3. Die Farbbefehle (ANSI) werden freigeschaltet.
      4. Der Schnellbearbeitungsmodus wird abgeschaltet. Ebendieser haelt
         sonst das ganze Programm an, sobald jemand mit der Maus in das
         Fenster klicket - der haeufigste Grund fuer ein vermeintlich
         haengendes Konsolenprogramm.

    :param spalten: int, gewuenschte Anzahl Spalten des Fensters
    :param zeilen: int, gewuenschte Anzahl Zeilen des Fensters
    :return: bool, True sofern eine echte Konsole vorliegt
    """
    global FARBEN_MOEGLICH

    STD_EINGABE = -10
    STD_AUSGABE = -11
    ENABLE_INSERT_MODE = 0x0020
    ENABLE_QUICK_EDIT_MODE = 0x0040
    ENABLE_EXTENDED_FLAGS = 0x0080
    ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004

    # Die Umstellung auf UTF-8 geschieht in jedem Falle zuerst, gleichviel
    # ob eine Konsole vorliegt. Andernfalls scheiterte die Ausgabe der
    # Rahmenzeichen, sobald der Bildschirm umgeleitet wird.
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except (AttributeError, ValueError):
        pass

    try:
        kernel32 = ctypes.windll.kernel32
        griff_ein = kernel32.GetStdHandle(STD_EINGABE)
        modus = ctypes.c_uint32()

        # Liegt keine echte Konsole vor (etwa unter Jupyter), so schlaegt
        # bereits diese Abfrage fehl. Alsdann wird ohne Farben gearbeitet.
        if not kernel32.GetConsoleMode(griff_ein, ctypes.byref(modus)):
            FARBEN_MOEGLICH = False
            return False

        # 1. Fenstergroesse
        try:
            os.system('mode con: cols={0} lines={1}'.format(spalten, zeilen))
        except OSError:
            pass

        # 2. Zeichensatz UTF-8 fuer Rahmen und Bloecke
        kernel32.SetConsoleOutputCP(65001)
        try:
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        except (AttributeError, ValueError):
            pass

        # 3. Farbbefehle freischalten
        griff_aus = kernel32.GetStdHandle(STD_AUSGABE)
        modus_aus = ctypes.c_uint32()
        if kernel32.GetConsoleMode(griff_aus, ctypes.byref(modus_aus)):
            kernel32.SetConsoleMode(
                griff_aus,
                modus_aus.value | ENABLE_VIRTUAL_TERMINAL_PROCESSING)

        # 4. Mausklick-Sperre aufheben (Schnellbearbeitung abschalten).
        #    Das Kennzeichen ENABLE_EXTENDED_FLAGS muss dabei gesetzt sein,
        #    sonst bleibet die Umstellung wirkungslos.
        kernel32.GetConsoleMode(griff_ein, ctypes.byref(modus))
        kernel32.SetConsoleMode(
            griff_ein,
            (modus.value & ~ENABLE_QUICK_EDIT_MODE & ~ENABLE_INSERT_MODE)
            | ENABLE_EXTENDED_FLAGS)

        FARBEN_MOEGLICH = True
        return True

    except (AttributeError, OSError):
        FARBEN_MOEGLICH = False
        return False


def verstecke_zeiger():
    """
    Verbirgt den blinkenden Schreibzeiger, auf dass das Bild ruhig sei.

    :return: None
    """
    if FARBEN_MOEGLICH:
        schreibe('\x1b[?25l')


def zeige_zeiger():
    """
    Bringt den Schreibzeiger zurueck und stellet die Farben zurueck.

    :return: None
    """
    if FARBEN_MOEGLICH:
        schreibe('\x1b[?25h\x1b[0m\n')


# =============================================================================
# ABSCHNITT 5: TASTATUR
# =============================================================================

def leere_tastaturpuffer():
    """
    Leeret den Tastaturpuffer restlos.

    Dies ist bei jedem Wechsel des Spielabschnittes vonnoeten, damit
    Tastendruecke aus einer frueheren Phase nicht faelschlich als Reaktion
    oder als Fehlstart gelten. Wer etwa beim Blitz mehrmals hastig auf TAB
    schlaegt, soll damit nicht sogleich die naechste Runde ausloesen.

    :return: None
    """
    while msvcrt.kbhit():
        msvcrt.getch()


def lies_taste():
    """
    Liest einen einzelnen Tastendruck als rohes Byte, sofern einer vorliegt.

    Sondertasten (Pfeile, F-Tasten) melden sich mit einem Vorbyte; dieses
    wird samt dem folgenden Byte verworfen und als b'?' gemeldet.

    :return: bytes oder None, wenn nichts vorliegt
    """
    if not msvcrt.kbhit():
        return None
    taste = msvcrt.getch()
    if taste in TASTEN_VORZEICHEN:
        msvcrt.getch()               # zweites Byte der Sondertaste verwerfen
        return b'?'
    return taste


def lies_ereignis():
    """
    Liest hoechstens einen Tastendruck und deutet ihn.

    Dies ist die einzige Stelle im ganzen Programm, an welcher Tastencodes
    ausgewertet werden. Alle Spielabschnitte bedienen sich ebendieser
    Funktion, wodurch die Behandlung der Eingaben einheitlich bleibet.

    :return: str, eines der Ereignisse
             EREIGNIS_KEINS     - es liegt nichts vor
             EREIGNIS_REAKTION  - TAB
             EREIGNIS_ZURUECK   - ESC
             EREIGNIS_ENDE      - Q
             EREIGNIS_ANDERE    - irgendeine andere Taste
    """
    taste = lies_taste()
    if taste is None:
        return EREIGNIS_KEINS
    if taste == TASTE_TAB:
        return EREIGNIS_REAKTION
    if taste == TASTE_ESC:
        return EREIGNIS_ZURUECK
    if taste in TASTEN_ENDE:
        return EREIGNIS_ENDE
    return EREIGNIS_ANDERE


def pruefe_sondertasten(ereignis):
    """
    Wirft die zugehoerige Ausnahme, sofern ESC oder Q gedrueckt ward.

    Auf diese Weise wirken ESC und Q in jedem Abschnitt des Spieles gleich,
    ohne dass jeder Abschnitt dies eigens zu bedenken haette.

    :param ereignis: str, ein Ereignis aus lies_ereignis()
    :raises SpielZurueck: bei ESC
    :raises SpielEnde: bei Q
    :return: None
    """
    if ereignis == EREIGNIS_ZURUECK:
        raise SpielZurueck()
    if ereignis == EREIGNIS_ENDE:
        raise SpielEnde()


# =============================================================================
# ABSCHNITT 6: BAUSTEINE DES BEDIENBILDES
# =============================================================================

MUSTER_ANSI = re.compile(r'\x1b\[[0-9;?]*[a-zA-Z]')

# Die Grossschrift: je Zeichen 3 Punkte breit und 5 Punkte hoch.
# Sie umfasset Ziffern und Buchstaben, denn sie dienet sowohl der Anzeige
# der Millisekunden als auch der Bewertung und der Namenseingabe.
GROSSSCHRIFT = {
    '0': ['###', '# #', '# #', '# #', '###'],
    '1': ['  #', '  #', '  #', '  #', '  #'],
    '2': ['###', '  #', '###', '#  ', '###'],
    '3': ['###', '  #', '###', '  #', '###'],
    '4': ['# #', '# #', '###', '  #', '  #'],
    '5': ['###', '#  ', '###', '  #', '###'],
    '6': ['###', '#  ', '###', '# #', '###'],
    '7': ['###', '  #', '  #', '  #', '  #'],
    '8': ['###', '# #', '###', '# #', '###'],
    '9': ['###', '# #', '###', '  #', '###'],
    'A': ['###', '# #', '###', '# #', '# #'],
    'B': ['## ', '# #', '## ', '# #', '## '],
    'C': ['###', '#  ', '#  ', '#  ', '###'],
    'D': ['## ', '# #', '# #', '# #', '## '],
    'E': ['###', '#  ', '###', '#  ', '###'],
    'F': ['###', '#  ', '###', '#  ', '#  '],
    'G': ['###', '#  ', '# #', '# #', '###'],
    'H': ['# #', '# #', '###', '# #', '# #'],
    'I': ['###', ' # ', ' # ', ' # ', '###'],
    'J': ['  #', '  #', '  #', '# #', '###'],
    'K': ['# #', '# #', '## ', '# #', '# #'],
    'L': ['#  ', '#  ', '#  ', '#  ', '###'],
    'M': ['# #', '###', '###', '# #', '# #'],
    'N': ['## ', '# #', '# #', '# #', '# #'],
    'O': ['###', '# #', '# #', '# #', '###'],
    'P': ['###', '# #', '###', '#  ', '#  '],
    'Q': ['###', '# #', '# #', '###', '  #'],
    'R': ['###', '# #', '###', '## ', '# #'],
    'S': ['###', '#  ', '###', '  #', '###'],
    'T': ['###', ' # ', ' # ', ' # ', ' # '],
    'U': ['# #', '# #', '# #', '# #', '###'],
    'V': ['# #', '# #', '# #', '# #', ' # '],
    'W': ['# #', '# #', '###', '###', '# #'],
    'X': ['# #', '# #', ' # ', '# #', '# #'],
    'Y': ['# #', '# #', ' # ', ' # ', ' # '],
    'Z': ['###', '  #', ' # ', '#  ', '###'],
    '!': [' # ', ' # ', ' # ', '   ', ' # '],
    '-': ['   ', '   ', '###', '   ', '   '],
    '_': ['   ', '   ', '   ', '   ', '###'],
    '?': ['###', '  #', ' ##', '   ', ' # '],
    ' ': ['   ', '   ', '   ', '   ', '   '],
}
GROSSSCHRIFT_HOEHE = 5


def farbe(rot, gruen, blau):
    """
    Liefert den Befehl fuer eine Vordergrundfarbe (Echtfarben-ANSI).

    :param rot: int, 0 bis 255
    :param gruen: int, 0 bis 255
    :param blau: int, 0 bis 255
    :return: str, die Befehlsfolge oder '' ohne Farbunterstuetzung
    """
    if not FARBEN_MOEGLICH:
        return ''
    return '\x1b[38;2;{0};{1};{2}m'.format(int(rot), int(gruen), int(blau))


def zurueck():
    """
    Liefert den Befehl, welcher die Farbe zuruecksetzet.

    :return: str, die Befehlsfolge oder '' ohne Farbunterstuetzung
    """
    return '\x1b[0m' if FARBEN_MOEGLICH else ''


def gefaerbt(text, rgb_farbe, fett=False):
    """
    Faerbet einen Text ein.

    :param text: str, der einzufaerbende Text
    :param rgb_farbe: tuple (R, G, B) oder None fuer keine Faerbung
    :param fett: bool, ob der Text fett erscheinen soll
    :return: str, der eingefaerbte Text
    """
    if rgb_farbe is None or not FARBEN_MOEGLICH:
        return text
    anfang = '\x1b[1m' if fett else ''
    return anfang + farbe(*rgb_farbe) + text + zurueck()


def sichtbare_laenge(text):
    """
    Ermittelt die Anzahl sichtbarer Zeichen, ohne die Farbbefehle.

    :param text: str, moeglicherweise mit Farbbefehlen durchsetzt
    :return: int, Anzahl der sichtbaren Zeichen
    """
    return len(MUSTER_ANSI.sub('', text))


def fuelle(text, breite):
    """
    Fuellet einen Text rechts mit Leerzeichen auf die gewuenschte Breite.

    Die Farbbefehle werden hierbei nicht mitgezaehlet, weshalb das
    Bedienbild stets buendig bleibet.

    :param text: str, der aufzufuellende Text
    :param breite: int, die gewuenschte sichtbare Breite
    :return: str, der aufgefuellte Text
    """
    fehlt = breite - sichtbare_laenge(text)
    return text + ' ' * fehlt if fehlt > 0 else text


def kasten_oben(titel, breite, rahmenfarbe=TUI_RAHMEN, titelfarbe=TUI_TITEL):
    """
    Zeichnet die obere Kante eines Kastens samt Ueberschrift.

    :param titel: str, die Ueberschrift des Kastens
    :param breite: int, die aeussere Breite des Kastens
    :param rahmenfarbe: tuple (R, G, B) des Rahmens
    :param titelfarbe: tuple (R, G, B) der Ueberschrift
    :return: str, die fertige Zeile
    """
    rest = breite - len(titel) - 5
    return (gefaerbt('┌─ ', rahmenfarbe)
            + gefaerbt(titel, titelfarbe)
            + gefaerbt(' ' + '─' * max(0, rest) + '┐', rahmenfarbe))


def kasten_unten(breite, rahmenfarbe=TUI_RAHMEN):
    """
    Zeichnet die untere Kante eines Kastens.

    :param breite: int, die aeussere Breite des Kastens
    :param rahmenfarbe: tuple (R, G, B) des Rahmens
    :return: str, die fertige Zeile
    """
    return gefaerbt('└' + '─' * (breite - 2) + '┘', rahmenfarbe)


def kasten_zeile(inhalt, breite, rahmenfarbe=TUI_RAHMEN):
    """
    Setzet einen Inhalt zwischen die beiden senkrechten Rahmenstriche.

    :param inhalt: str, der Inhalt (darf Farbbefehle enthalten)
    :param breite: int, die aeussere Breite des Kastens
    :param rahmenfarbe: tuple (R, G, B) des Rahmens
    :return: str, die fertige Zeile
    """
    strich = gefaerbt('│', rahmenfarbe)
    return strich + fuelle(inhalt, breite - 2) + strich


def grossschrift(text):
    """
    Setzet einen Text in Grossziffern um.

    :param text: str, die darzustellenden Zeichen (Ziffern, M, S, !, -, ?)
    :return: Liste von 5 str, die Zeilen der Grossdarstellung.
             Ein Punkt wird als zwei Bloecke '██' gesetzt, damit die
             Schrift breit und stattlich wirket.
    """
    zeilen = []
    for hoehe in range(GROSSSCHRIFT_HOEHE):
        stueck = ''
        for zeichen in text.upper():
            muster = GROSSSCHRIFT.get(zeichen, GROSSSCHRIFT['?'])[hoehe]
            for punkt in muster:
                stueck += '██' if punkt == '#' else '  '
            stueck += '  '            # Abstand zwischen den Zeichen
        zeilen.append(stueck.rstrip())
    return zeilen


def mittig(text, breite):
    """
    Setzet einen Text mittig in eine gegebene Breite.

    :param text: str, der Text (darf Farbbefehle enthalten)
    :param breite: int, die gewuenschte Breite
    :return: str, der mittig gesetzte Text
    """
    frei = breite - sichtbare_laenge(text)
    if frei <= 0:
        return text
    links = frei // 2
    return ' ' * links + text


def balken(anteil, breite, voll_zeichen='█', leer_zeichen='░'):
    """
    Erzeugt einen waagrechten Balken.

    :param anteil: float, 0.0 bis 1.0
    :param breite: int, Laenge des Balkens in Zeichen
    :param voll_zeichen: str, Zeichen fuer den gefuellten Teil
    :param leer_zeichen: str, Zeichen fuer den leeren Teil
    :return: str, der fertige Balken
    """
    anteil = max(0.0, min(1.0, anteil))
    voll = int(round(anteil * breite))
    return voll_zeichen * voll + leer_zeichen * (breite - voll)


# =============================================================================
# ABSCHNITT 7: DER SPIELSTAND UND DAS ZEICHNEN DES BEDIENBILDES
# =============================================================================

class Spielstand:
    """
    Traeger saemtlicher Angaben, welche das Bedienbild darstellen soll.

    Die Anzeigefunktionen veraendern allein diesen Spielstand; das Zeichnen
    geschieht danach an einer einzigen Stelle. Dadurch bleibet das Bild
    ueberall gleich aufgebaut, gleichviel aus welchem Abschnitt es stammet.
    """

    def __init__(self, port=PORT_STANDARD, modus=MODUS_STANDARD):
        """
        Erstellet einen frischen Spielstand.

        :param port: str, der verwendete Anschluss (nur zur Anzeige)
        :param modus: str, der Schwierigkeitsgrad aus MODI
        """
        self.port = port
        self.modus = modus
        self.ton_an = True
        self.training = False
        self.ohne_hardware = False   # True, wenn ohne Platine gespielt wird

        self.zeiten = []            # Alle gewerteten Zeiten in Millisekunden
        self.fehlstarts = 0
        self.verpasste = 0
        self.serie = 0              # Laufende Folge von BLITZ-Ergebnissen
        self.beste_serie = 0

        self.status = 'Bereit.'
        self.statusfarbe = TUI_TEXT
        self.tafel_titel = 'REAKTIONSZEIT'
        self.gross = '- - -'        # Inhalt der Grossanzeige
        self.grossfarbe = TUI_MATT
        self.unterzeile = ''
        self.bestenliste = []

    def zuruecksetzen(self):
        """
        Setzet alle Werte eines Spieles zurueck, behaelt jedoch die
        Einstellungen wie Modus und Ton bei.

        :return: None
        """
        self.zeiten = []
        self.fehlstarts = 0
        self.verpasste = 0
        self.serie = 0
        self.beste_serie = 0
        self.gross = '- - -'
        self.grossfarbe = TUI_MATT
        self.unterzeile = ''
        self.tafel_titel = 'REAKTIONSZEIT'

    def setze_status(self, text, statusfarbe=TUI_TEXT):
        """
        Setzet die Statuszeile des Bedienbildes.

        :param text: str, der anzuzeigende Hinweis
        :param statusfarbe: tuple (R, G, B) der Schriftfarbe
        :return: None
        """
        self.status = text
        self.statusfarbe = statusfarbe

    def setze_gross(self, text, grossfarbe=TUI_TEXT, unterzeile='',
                    titel='REAKTIONSZEIT'):
        """
        Setzet den Inhalt der Grossanzeige.

        :param text: str, die grossen Zeichen (Ziffern, '!', '-')
        :param grossfarbe: tuple (R, G, B) der Schriftfarbe
        :param unterzeile: str, eine kleine Zeile unter den Grossziffern
        :param titel: str, die Ueberschrift des Kastens
        :return: None
        """
        self.gross = text
        self.grossfarbe = grossfarbe
        self.unterzeile = unterzeile
        self.tafel_titel = titel


def _zeilen_matrixspiegel(rgb):
    """
    Erzeugt die Zeilen des Matrix-Spiegels aus dem gegenwaertigen Bild.

    Jede Leuchtdiode wird als Doppelblock dargestellt. Da die Werte auf der
    Hardware bewusst klein gehalten sind, werden sie fuer die Darstellung im
    Fenster vervierfacht, damit die Farben deutlich hervortreten.

    :param rgb: RgbMatrixUart, dessen Feld 'rgb_matrix' gespiegelt wird
    :return: Liste von 8 str, die Zeilen des Spiegels
    """
    zeilen = []
    for zeile in range(MATRIX_GROESSE):
        stueck = ''
        for spalte in range(MATRIX_GROESSE):
            rot, gruen, blau = rgb.rgb_matrix[zeile][spalte]
            if rot + gruen + blau <= 0:
                stueck += gefaerbt('··', TUI_DUNKEL)
            else:
                hell = (min(255, int(rot) * 4),
                        min(255, int(gruen) * 4),
                        min(255, int(blau) * 4))
                stueck += gefaerbt('██', hell)
        zeilen.append(stueck)
    return zeilen


def _zeilen_rundentafel(spielstand):
    """
    Erzeugt die Zeilen der Rundentafel: Balken, Zeiten und Bewertungen.

    Die Balken sind auf 700 ms bezogen; eine kuerzere Zeit gibt somit einen
    kuerzeren Balken. Noch nicht gespielte Runden erscheinen gestrichelt.

    :param spielstand: Spielstand mit den bisherigen Zeiten
    :return: Liste von str, die Zeilen der Tafel
    """
    zeilen = []
    balkenbreite = 26
    anzahl = len(spielstand.zeiten) if spielstand.training else RUNDEN_ANZAHL

    for nummer in range(1, max(anzahl, RUNDEN_ANZAHL) + 1):
        if nummer > len(spielstand.zeiten):
            if spielstand.training:
                continue
            zeilen.append(
                ' {0}  {1}   {2}'.format(
                    gefaerbt('{0}'.format(nummer), TUI_MATT),
                    gefaerbt('░' * balkenbreite, TUI_DUNKEL),
                    gefaerbt('offen', TUI_MATT)))
            continue

        zeit = spielstand.zeiten[nummer - 1]
        note = bewerte_zeit(zeit)
        notenfarbe = BEWERTUNGSFARBEN[note]
        anteil = min(1.0, zeit / 700.0)
        zeilen.append(
            ' {0}  {1}  {2}  {3}'.format(
                gefaerbt('{0}'.format(nummer), TUI_TEXT),
                gefaerbt(balken(anteil, balkenbreite), notenfarbe),
                gefaerbt('{0:7.1f} ms'.format(zeit), TUI_TEXT),
                gefaerbt(note, notenfarbe, fett=True)))

    # Nur die letzten Zeilen zeigen, damit die Tafel nicht ueberlaeuft
    zeilen = zeilen[-6:]

    while len(zeilen) < 6:
        zeilen.append('')

    # Fusszeile der Tafel: Serie, Bestzeit, Fehlstarts
    if spielstand.zeiten:
        beste = min(spielstand.zeiten)
        schnitt = sum(spielstand.zeiten) / len(spielstand.zeiten)
        auskunft = ' {0}  {1}   {2}  {3}'.format(
            gefaerbt('Beste', TUI_MATT),
            gefaerbt('{0:.0f} ms'.format(beste), TUI_TEXT),
            gefaerbt('Schnitt', TUI_MATT),
            gefaerbt('{0:.0f} ms'.format(schnitt), TUI_TEXT))
    else:
        auskunft = ' ' + gefaerbt('Noch keine Zeiten erzielt.', TUI_MATT)

    serientext = ''
    if spielstand.serie > 1:
        serientext = gefaerbt(
            '  SERIE x{0}'.format(spielstand.serie), TUI_GOLD, fett=True)

    zeilen.append(gefaerbt('─' * (BREITE_RECHTS - 2), TUI_RAHMEN))
    zeilen.append(auskunft + serientext)
    zeilen.append(' {0} {1}   {2} {3}'.format(
        gefaerbt('Fehlstarts', TUI_MATT),
        gefaerbt(str(spielstand.fehlstarts), TUI_WARNUNG),
        gefaerbt('Verpasst', TUI_MATT),
        gefaerbt(str(spielstand.verpasste), TUI_STEIN)))
    return zeilen


def zeichne_bild(spielstand, rgb):
    """
    Zeichnet das gesamte Bedienbild in einem Zuge.

    Das Bild wird zuerst vollstaendig als Zeichenkette aufgebaut und alsdann
    mit einem einzigen Schreibvorgang ausgegeben. Dadurch flimmert nichts.
    Der Bildschirm wird nicht geloescht, sondern der Schreibzeiger nach oben
    gesetzt und ueber das alte Bild geschrieben.

    :param spielstand: Spielstand, woraus alle Angaben stammen
    :param rgb: RgbMatrixUart, dessen Matrix gespiegelt wird
    :return: None
    """
    zeilen = []

    # --- Kopfbalken ---------------------------------------------------------
    modusangabe = '{0}'.format(spielstand.modus)
    tonangabe = 'an' if spielstand.ton_an else 'aus'
    spielart = 'TRAINING' if spielstand.training else 'SPIEL'
    kopf = (' ' + gefaerbt('R E A K T I O N S S P I E L', TUI_TITEL, fett=True)
            + '   ' + gefaerbt('│', TUI_RAHMEN)
            + '  ' + gefaerbt(spielart, TUI_TEXT)
            + '   ' + gefaerbt('Grad', TUI_MATT) + ' '
            + gefaerbt(modusangabe, TUI_GOLD)
            + '   ' + gefaerbt('Anschluss', TUI_MATT) + ' '
            + gefaerbt(spielstand.port,
                       TUI_STEIN if spielstand.ohne_hardware else TUI_TEXT)
            + '   ' + gefaerbt('Ton', TUI_MATT) + ' '
            + gefaerbt(tonangabe, TUI_TEXT))
    zeilen.append(gefaerbt('╔' + '═' * (BREITE - 2) + '╗', TUI_RAHMEN))
    zeilen.append(gefaerbt('║', TUI_RAHMEN) + fuelle(kopf, BREITE - 2)
                  + gefaerbt('║', TUI_RAHMEN))
    zeilen.append(gefaerbt('╚' + '═' * (BREITE - 2) + '╝', TUI_RAHMEN))

    # --- Matrix-Spiegel und Rundentafel nebeneinander -----------------------
    spiegel = _zeilen_matrixspiegel(rgb)
    tafel = _zeilen_rundentafel(spielstand)
    hoehe = max(len(spiegel), len(tafel))

    zeilen.append(kasten_oben('MATRIX 8x8', BREITE_LINKS)
                  + kasten_oben('RUNDEN', BREITE_RECHTS))
    for nummer in range(hoehe):
        links = '    ' + spiegel[nummer] if nummer < len(spiegel) else ''
        rechts = tafel[nummer] if nummer < len(tafel) else ''
        zeilen.append(kasten_zeile(links, BREITE_LINKS)
                      + kasten_zeile(rechts, BREITE_RECHTS))
    zeilen.append(kasten_unten(BREITE_LINKS) + kasten_unten(BREITE_RECHTS))

    # --- Grossanzeige -------------------------------------------------------
    zeilen.append(kasten_oben(spielstand.tafel_titel, BREITE))
    for stueck in grossschrift(spielstand.gross):
        zeilen.append(kasten_zeile(
            mittig(gefaerbt(stueck, spielstand.grossfarbe, fett=True),
                   BREITE - 2),
            BREITE))
    zeilen.append(kasten_zeile(
        mittig(gefaerbt(spielstand.unterzeile, spielstand.grossfarbe),
               BREITE - 2), BREITE))
    zeilen.append(kasten_unten(BREITE))

    # --- Statuszeile --------------------------------------------------------
    zeilen.append(kasten_oben('STATUS', BREITE))
    zeilen.append(kasten_zeile(
        ' ' + gefaerbt('▶ ' + spielstand.status, spielstand.statusfarbe,
                       fett=True), BREITE))
    zeilen.append(kasten_unten(BREITE))

    # --- Hilfszeile ---------------------------------------------------------
    zeilen.append(' ' + gefaerbt(
        'TAB Reaktion    ESC zurueck ins Menue    Q beenden', TUI_MATT))

    ausgabe = '\x1b[H' if FARBEN_MOEGLICH else ''
    ausgabe += '\n'.join(fuelle(zeile, BREITE) for zeile in zeilen)
    ausgabe += '\x1b[J' if FARBEN_MOEGLICH else ''
    schreibe(ausgabe)


def loesche_bildschirm():
    """
    Loeschet das ganze Textfenster.

    :return: None
    """
    if FARBEN_MOEGLICH:
        schreibe('\x1b[2J\x1b[H')
    else:
        print('\n' * 3)


# =============================================================================
# ABSCHNITT 8: DIE ANZEIGEN AUF DER MATRIX
# =============================================================================

def zeige_sinus(rgb, spielstand, dauer_sekunden=None):
    """
    Zeiget die langsame Sinuswelle: die Anzeige des Wartemodus.

    Diese Anzeige erscheinet zu Beginn, zwischen den Runden und im Menue.
    Fuer jede Spalte wird die zugehoerige Zeile aus der Sinusfunktion
    berechnet und ebendort eine tuerkise Leuchtdiode gesetzt. Mit
    fortschreitender Zeit wandert die Welle gemaechlich. Das Bedienbild
    wird bei jedem Bild mitgefuehret, sodass der Spiegel lebet.

    Zu Beginn wird der Tastaturpuffer geleeret, damit ein liegengebliebener
    Tastendruck die naechste Runde nicht unversehens ausloest.

    :param rgb: RgbMatrixUart, das geoeffnete Objekt der RGB-Matrix
    :param spielstand: Spielstand, zum Zeichnen des Bedienbildes
    :param dauer_sekunden: float oder None.
                           None  = die Welle laeuft, bis eine Taste gedrueckt
                                   wird (Wartemodus auf den Startbefehl)
                           Zahl  = die Welle laeuft genau so viele Sekunden
    :raises SpielZurueck: sofern der Spieler ESC druecket
    :raises SpielEnde: sofern der Spieler Q druecket
    :return: bool, True sofern durch Tastendruck beendet,
                   False sofern die vorgegebene Dauer abgelaufen ist
    """
    bildabstand = 1.0 / SINUS_BILDRATE_HZ
    mitte = (MATRIX_GROESSE - 1) / 2.0
    beginn = time.perf_counter()

    leere_tastaturpuffer()

    while True:
        verstrichen = time.perf_counter() - beginn

        # --- Abbruchbedingung 1: der Spieler druecket eine Taste ------------
        ereignis = lies_ereignis()
        if ereignis != EREIGNIS_KEINS:
            pruefe_sondertasten(ereignis)      # ESC und Q wirken sofort
            leere_tastaturpuffer()
            loesche_matrix(rgb, spielstand)
            return True

        # --- Abbruchbedingung 2: die vorgegebene Dauer ist verstrichen ------
        if dauer_sekunden is not None and verstrichen >= dauer_sekunden:
            loesche_matrix(rgb, spielstand)
            return False

        # --- Das Wellenbild berechnen und senden ---------------------------
        faerbe_alles(rgb, FARBE_AUS)
        for spalte in range(MATRIX_GROESSE):
            ort = spalte / (MATRIX_GROESSE - 1)          # 0.0 bis 1.0
            winkel = (2.0 * math.pi * SINUS_PERIODEN * ort
                      - 2.0 * math.pi * SINUS_TEMPO_HZ * verstrichen)
            zeile = round(mitte - SINUS_AMPLITUDE * math.sin(winkel))
            zeile = max(0, min(MATRIX_GROESSE - 1, zeile))
            rgb.rgb_matrix[zeile][spalte] = list(FARBE_SINUS)
        rgb.sende()
        zeichne_bild(spielstand, rgb)

        time.sleep(bildabstand)


def zeige_start(rgb, spielstand):
    """
    Zeiget den Countdown nach Art einer Verkehrsampel: Rot, Orange, Gruen.

    Die Grossanzeige zaehlet dabei 3, 2, 1 herab. Nach dem gruenen Licht
    erlischt die ganze Matrix. Damit ist das Spiel eroeffnet und der Spieler
    harre des Blitzes. Waehrend der Ampel gedrueckte Tasten werden verworfen
    und gelten NICHT als Fehlstart; erst was in der darauf folgenden
    Dunkelheit geschieht, wird gewertet.

    :param rgb: RgbMatrixUart, das geoeffnete Objekt der RGB-Matrix
    :param spielstand: Spielstand, zum Zeichnen des Bedienbildes
    :raises SpielZurueck: sofern der Spieler ESC druecket
    :raises SpielEnde: sofern der Spieler Q druecket
    :return: None
    """
    stufen = [
        (FARBE_AMPEL_ROT, '3', TUI_WARNUNG, 'Achtung'),
        (FARBE_AMPEL_ORANGE, '2', TUI_STEIN, 'Fertig'),
        (FARBE_AMPEL_GRUEN, '1', TUI_WIND, 'Los'),
    ]

    for nummer, (matrixfarbe, ziffer, tuifarbe, wort) in enumerate(stufen):
        faerbe_alles(rgb, matrixfarbe)
        rgb.sende()
        spielstand.setze_gross(ziffer, tuifarbe, wort, titel='COUNTDOWN')
        spielstand.setze_status('Ampel laeuft ... ' + wort, tuifarbe)
        zeichne_bild(spielstand, rgb)
        spiele_ton(TON_AMPEL[nummer], spielstand)

        # Die Wartezeit wird in kleinen Schritten verbracht, damit ESC und Q
        # auch waehrend der Ampel unverzueglich wirken.
        ende = time.perf_counter() + AMPEL_SCHRITT_SEKUNDEN
        while time.perf_counter() < ende:
            pruefe_sondertasten(lies_ereignis())
            time.sleep(0.005)

    loesche_matrix(rgb)          # Dunkelheit: nun gilt es
    spielstand.setze_gross('- - -', TUI_MATT, 'bereithalten',
                           titel='REAKTIONSZEIT')
    spielstand.setze_status('BEREIT ... nicht zu frueh druecken!', TUI_GOLD)
    zeichne_bild(spielstand, rgb)
    leere_tastaturpuffer()


def _zeige_taeuschung(rgb, spielstand):
    """
    Laesset kurz ein rotes Trugbild aufleuchten, welches NICHT gilt.

    Waehrend des Trugbildes wird die Tastatur weiter ueberwachet, denn wer
    hierauf hereinfaellt, begehet einen Fehlstart.

    :param rgb: RgbMatrixUart, das geoeffnete Objekt der RGB-Matrix
    :param spielstand: Spielstand, zum Zeichnen des Bedienbildes
    :raises SpielZurueck: sofern der Spieler ESC druecket
    :raises SpielEnde: sofern der Spieler Q druecket
    :return: bool, True sofern der Spieler hereinfiel (Fehlstart)
    """
    faerbe_alles(rgb, FARBE_TAEUSCHUNG)
    rgb.sende()
    zeichne_bild(spielstand, rgb)

    ende = time.perf_counter() + 0.10
    hereingefallen = False
    while time.perf_counter() < ende:
        ereignis = lies_ereignis()
        if ereignis != EREIGNIS_KEINS:
            pruefe_sondertasten(ereignis)
            hereingefallen = True
            break
        time.sleep(0.001)

    loesche_matrix(rgb, spielstand)
    return hereingefallen


def zeige_blitz(rgb, spielstand):
    """
    Wartet eine zufaellige Weile und schiesst alsdann den Blitz herab.

    Zuerst verstreichet eine nach dem Zufall bemessene Zeit gemaess dem
    gewaehlten Schwierigkeitsgrade. Waehrend dieser Zeit wird die Tastatur
    ueberwachet: ein Tastendruck in ebendieser Phase ist ein Fehlstart. Im
    schweren Grade kann ueberdies ein rotes Trugbild erscheinen, welches
    nicht gedrueckt werden darf.

    Hernach faellt eine schnelle tuerkise Linie von der obersten bis zur
    untersten Zeile. Der Zeitpunkt, da die erste Zeile aufleuchtet, ist der
    Beginn der Messung; ebendieser Zeitstempel wird genommen, BEVOR das
    Bedienbild gezeichnet wird, damit die Messung unverfaelscht bleibet.

    :param rgb: RgbMatrixUart, das geoeffnete Objekt der RGB-Matrix
    :param spielstand: Spielstand, zum Zeichnen des Bedienbildes
    :raises SpielZurueck: sofern der Spieler ESC druecket
    :raises SpielEnde: sofern der Spieler Q druecket
    :return: tuple (erfolg, zeitpunkt)
             erfolg    = bool, True sofern der Blitz ordentlich erschien,
                         False bei einem Fehlstart
             zeitpunkt = float, der Zeitstempel des Blitzes aus
                         time.perf_counter(); bei Fehlstart 0.0
    """
    einstellung = MODI[spielstand.modus]
    kuerzeste, laengste = einstellung['warte']
    wartezeit = random.uniform(kuerzeste, laengste)
    ende_der_wartezeit = time.perf_counter() + wartezeit

    # Ein etwaiges Trugbild wird in die erste Haelfte der Wartezeit gelegt.
    zeitpunkt_trugbild = None
    if random.random() < einstellung['taeuschung']:
        zeitpunkt_trugbild = (time.perf_counter()
                              + random.uniform(0.6, max(0.7, wartezeit * 0.5)))

    while time.perf_counter() < ende_der_wartezeit:
        ereignis = lies_ereignis()
        if ereignis != EREIGNIS_KEINS:
            pruefe_sondertasten(ereignis)      # ESC und Q sind kein Fehlstart
            leere_tastaturpuffer()
            return (False, 0.0)                # zu frueh gedrueckt

        if (zeitpunkt_trugbild is not None
                and time.perf_counter() >= zeitpunkt_trugbild):
            zeitpunkt_trugbild = None
            if _zeige_taeuschung(rgb, spielstand):
                leere_tastaturpuffer()
                return (False, 0.0)            # auf die Taeuschung gefallen

        time.sleep(0.001)                      # schonet den Prozessor

    # --- Der Blitz faellt von oben nach unten -------------------------------
    zeitpunkt_des_blitzes = 0.0
    for zeile in range(MATRIX_GROESSE):
        faerbe_alles(rgb, FARBE_AUS)
        for spalte in range(MATRIX_GROESSE):
            rgb.rgb_matrix[zeile][spalte] = list(FARBE_BLITZ)
        rgb.sende()

        if zeile == 0:
            # Erst jetzt ist das Licht wahrhaftig sichtbar: Messung beginnt.
            # Der Zeitstempel wird vor jeder Bildschirmarbeit genommen.
            zeitpunkt_des_blitzes = time.perf_counter()
            spielstand.setze_gross('!', TUI_BLITZ, 'JETZT TAB DRUECKEN')
            spielstand.setze_status('JETZT!', TUI_BLITZ)

        zeichne_bild(spielstand, rgb)
        time.sleep(BLITZ_SCHRITT_SEKUNDEN)

    # --- Die ganze Flaeche leuchtet und wartet auf die Reaktion -------------
    faerbe_alles(rgb, FARBE_BLITZ)
    rgb.sende()
    zeichne_bild(spielstand, rgb)

    return (True, zeitpunkt_des_blitzes)


def zeige_fehlstart(rgb, spielstand):
    """
    Mahnet den Fehlstart mit mehrmaligem rotem Blinken.

    :param rgb: RgbMatrixUart, das geoeffnete Objekt der RGB-Matrix
    :param spielstand: Spielstand, zum Zeichnen des Bedienbildes
    :return: None
    """
    spielstand.setze_gross('- - -', TUI_WARNUNG, 'FEHLSTART')
    spielstand.setze_status('FEHLSTART! Zu frueh. Die Runde wird wiederholt.',
                            TUI_WARNUNG)
    spiele_ton(TON_FEHLSTART, spielstand)
    blinke(rgb, FARBE_FEHLSTART, spielstand)
    leere_tastaturpuffer()


def zeige_verpasst(rgb, spielstand):
    """
    Mahnet die ausgebliebene Reaktion mit bernsteinfarbenem Blinken.

    :param rgb: RgbMatrixUart, das geoeffnete Objekt der RGB-Matrix
    :param spielstand: Spielstand, zum Zeichnen des Bedienbildes
    :return: None
    """
    spielstand.setze_gross('- - -', TUI_STEIN, 'VERPASST')
    spielstand.setze_status('VERPASST! Keine Reaktion. Runde wird wiederholt.',
                            TUI_STEIN)
    spiele_ton(TON_VERPASST, spielstand)
    blinke(rgb, FARBE_VERPASST, spielstand)
    leere_tastaturpuffer()


def zeige_ergebnis(rgb, spielstand, zeit_ms):
    """
    Feiert das Ergebnis mit einer kleinen Schau auf beiden Anzeigen.

    Die Grossanzeige zaehlet die Millisekunden von null bis zum erzielten
    Werte hinauf, waehrend die Matrix in der Farbe der Bewertung pulsieret.
    Das Aufzaehlen folget einer sanften Kurve, sodass es zum Schlusse hin
    langsamer wird.

    :param rgb: RgbMatrixUart, das geoeffnete Objekt der RGB-Matrix
    :param spielstand: Spielstand, zum Zeichnen des Bedienbildes
    :param zeit_ms: float, die erzielte Reaktionszeit in Millisekunden
    :return: None
    """
    note = bewerte_zeit(zeit_ms)
    notenfarbe = BEWERTUNGSFARBEN[note]
    grundfarbe = {'BLITZ': [0, 55, 55],
                  'WIND': [0, 50, 15],
                  'STEIN': [50, 25, 0]}[note]

    beginn = time.perf_counter()
    while True:
        anteil = (time.perf_counter() - beginn) / ZAEHLWERK_SEKUNDEN
        if anteil >= 1.0:
            break

        # Sanfte Kurve: schnell beginnen, weich auslaufen
        geglaettet = 1.0 - (1.0 - anteil) ** 3
        spielstand.setze_gross(
            '{0:.0f} MS'.format(zeit_ms * geglaettet), notenfarbe, note)

        # Die Matrix pulsieret im Takte des Zaehlwerkes
        staerke = 0.35 + 0.65 * abs(math.sin(anteil * math.pi * 3.0))
        faerbe_alles(rgb, [int(wert * staerke) for wert in grundfarbe])
        rgb.sende()
        zeichne_bild(spielstand, rgb)
        time.sleep(1.0 / 40.0)

    # Endstand fest anzeigen
    spielstand.setze_gross('{0:.0f} MS'.format(zeit_ms), notenfarbe, note)
    faerbe_alles(rgb, grundfarbe)
    rgb.sende()
    zeichne_bild(spielstand, rgb)
    spiele_ton(TON_ERGEBNIS[note], spielstand)

    time.sleep(0.35)
    loesche_matrix(rgb, spielstand)


# =============================================================================
# ABSCHNITT 9: MESSUNG DER REAKTIONSZEIT
# =============================================================================

def messe_reaktion(zeitpunkt_des_blitzes, rgb=None, sicht_ms=None):
    """
    Misset die Zeit vom Blitz bis zum Druck der TAB-Taste.

    Es wird gewartet, bis der Spieler TAB druecket. Andere Tasten werden
    verworfen. Damit das Warten unter keinen Umstaenden ewig waehret, ist es
    zeitlich begrenzet: bleibt der Tastendruck laenger als
    REAKTION_ZEITSPERRE_MS aus, so gilt die Runde als verpasst.

    Waehrend der Messung wird das Bedienbild bewusst NICHT gezeichnet, damit
    die Abfrage der Tastatur so eng als moeglich geschieht und die Messung
    nicht durch Bildschirmarbeit verzoegert wird. Einzig das Erloeschen des
    Blitzes (in den hoeheren Schwierigkeitsgraden) geschieht hier.

    :param zeitpunkt_des_blitzes: float, Zeitstempel aus time.perf_counter(),
                                  wie ihn zeige_blitz() zurueckgegeben hat
    :param rgb: RgbMatrixUart oder None. Wird er gegeben, so kann der Blitz
                nach Ablauf seiner Sichtdauer geloescht werden.
    :param sicht_ms: float oder None. Nach so vielen Millisekunden erlischt
                     der Blitz; None bedeutet, er bleibet stehen.
    :raises SpielZurueck: sofern der Spieler ESC druecket
    :raises SpielEnde: sofern der Spieler Q druecket
    :return: float oder None
             float = die Reaktionszeit in Millisekunden
             None  = binnen der Zeitsperre ward nicht gedrueckt (verpasst)
    """
    blitz_geloescht = False

    while True:
        verstrichen_ms = (time.perf_counter() - zeitpunkt_des_blitzes) * 1000.0

        # --- Zeitsperre: es wird nicht ewig gewartet ------------------------
        if verstrichen_ms > REAKTION_ZEITSPERRE_MS:
            leere_tastaturpuffer()
            return None

        # --- Der Blitz erlischt nach seiner Sichtdauer ----------------------
        if (not blitz_geloescht and rgb is not None and sicht_ms is not None
                and verstrichen_ms >= sicht_ms):
            blitz_geloescht = True
            faerbe_alles(rgb, FARBE_AUS)
            rgb.sende()

        ereignis = lies_ereignis()

        if ereignis == EREIGNIS_REAKTION:
            jetzt = time.perf_counter()
            leere_tastaturpuffer()      # weitere Schlaege verwerfen
            return (jetzt - zeitpunkt_des_blitzes) * 1000.0

        if ereignis != EREIGNIS_KEINS:
            pruefe_sondertasten(ereignis)          # ESC und Q wirken sofort

        time.sleep(0.0005)              # feine Abtastung, schonet dennoch


# =============================================================================
# ABSCHNITT 10: BEWERTUNG, STATISTIK, BESTENLISTE
# =============================================================================

def bewerte_zeit(zeit_ms):
    """
    Ordnet einer Reaktionszeit ihr Sinnbild zu.

    :param zeit_ms: float, die Reaktionszeit in Millisekunden
    :return: str, 'BLITZ' (unter 250 ms), 'WIND' (250 bis 500 ms)
                  oder 'STEIN' (ueber 500 ms)
    """
    if zeit_ms < GRENZE_BLITZ_MS:
        return 'BLITZ'
    if zeit_ms <= GRENZE_WIND_MS:
        return 'WIND'
    return 'STEIN'


def lade_bestenliste():
    """
    Liest die Bestenliste aus der Datei.

    Ist keine Datei vorhanden oder ist sie beschaedigt, so wird eine leere
    Liste zurueckgegeben; das Spiel laeuft alsdann gleichwohl.

    :return: Liste von dict mit den Schluesseln
             'name', 'schnitt', 'beste', 'modus', 'datum'
    """
    try:
        with open(BESTENLISTE_DATEI, 'r', encoding='utf-8') as datei:
            eintraege = json.load(datei)
        if isinstance(eintraege, list):
            return eintraege
    except (OSError, ValueError):
        pass
    return []


def speichere_bestenliste(eintraege):
    """
    Schreibt die Bestenliste in die Datei.

    :param eintraege: Liste von dict, die zu sichernden Eintraege
    :return: bool, True sofern das Schreiben gelang
    """
    try:
        with open(BESTENLISTE_DATEI, 'w', encoding='utf-8') as datei:
            json.dump(eintraege, datei, ensure_ascii=False, indent=2)
        return True
    except OSError:
        return False


def ist_rekordverdaechtig(eintraege, schnitt_ms):
    """
    Prueft, ob ein Durchschnitt in die Bestenliste gehoeret.

    :param eintraege: Liste von dict, die bestehende Bestenliste
    :param schnitt_ms: float, der erzielte Durchschnitt in Millisekunden
    :return: bool, True sofern der Wert aufgenommen wuerde
    """
    if len(eintraege) < BESTENLISTE_LAENGE:
        return True
    schlechtester = max(eintrag['schnitt'] for eintrag in eintraege)
    return schnitt_ms < schlechtester


def fuege_bestenliste_hinzu(eintraege, name, schnitt_ms, beste_ms, modus):
    """
    Fueget einen Eintrag ein, sortieret und kuerzet die Liste.

    :param eintraege: Liste von dict, die bestehende Bestenliste
    :param name: str, der Name des Spielers
    :param schnitt_ms: float, der erzielte Durchschnitt
    :param beste_ms: float, die beste Einzelzeit
    :param modus: str, der Schwierigkeitsgrad
    :return: tuple (liste, rang)
             liste = die neue, sortierte Bestenliste
             rang  = int, der Platz des neuen Eintrages (1 = Spitze)
    """
    neuer = {
        'name': name,
        'schnitt': round(schnitt_ms, 1),
        'beste': round(beste_ms, 1),
        'modus': modus,
        'datum': time.strftime('%d.%m.%Y %H:%M'),
    }
    eintraege = list(eintraege) + [neuer]
    eintraege.sort(key=lambda eintrag: eintrag['schnitt'])
    eintraege = eintraege[:BESTENLISTE_LAENGE]
    rang = eintraege.index(neuer) + 1
    return eintraege, rang


def frage_namen(rgb, spielstand, rang):
    """
    Fraget nach Art der Spielhallen einen kurzen Namen ab.

    Die Eingabe geschieht Zeichen fuer Zeichen ueber die unmittelbare
    Tastaturabfrage, damit das Bedienbild sichtbar bleibet.

    :param rgb: RgbMatrixUart, das geoeffnete Objekt der RGB-Matrix
    :param spielstand: Spielstand, zum Zeichnen des Bedienbildes
    :param rang: int, der erreichte Platz in der Bestenliste
    :return: str, der eingegebene Name (hoechstens 8 Zeichen)
    """
    name = ''
    erlaubt = ('ABCDEFGHIJKLMNOPQRSTUVWXYZ'
               'abcdefghijklmnopqrstuvwxyz0123456789 -_')
    leere_tastaturpuffer()

    while True:
        spielstand.setze_gross(
            (name + '_') if len(name) < 8 else name,
            TUI_GOLD, 'Name eingeben und mit ENTER bestaetigen',
            titel='PLATZ {0} IN DER BESTENLISTE'.format(rang))
        spielstand.setze_status(
            'Neuer Eintrag in der Bestenliste! Wie heisst der Held?', TUI_GOLD)

        # Die Matrix jubelt in gruenem Pulsieren
        staerke = 0.4 + 0.6 * abs(math.sin(time.perf_counter() * 3.0))
        faerbe_alles(rgb, [int(wert * staerke) for wert in FARBE_JUBEL])
        rgb.sende()
        zeichne_bild(spielstand, rgb)

        taste = lies_taste()
        if taste is not None:
            if taste in (b'\r', b'\n'):
                break
            if taste == b'\x08' and name:            # Ruecktaste
                name = name[:-1]
            elif taste == TASTE_ESC:
                break
            else:
                try:
                    zeichen = taste.decode('latin-1')
                except UnicodeDecodeError:
                    zeichen = ''
                if zeichen in erlaubt and len(name) < 8:
                    name += zeichen

        time.sleep(1.0 / 30.0)

    loesche_matrix(rgb, spielstand)
    return name.strip() or 'GAST'


def zeige_statistik(rgb, spielstand):
    """
    Zeiget die Auswertung eines vollendeten Spieles als eigenes Bild.

    Die Balken wachsen der Reihe nach heran, wodurch die Auswertung lebendig
    wirket. Hernach stehen beste, schlechteste und mittlere Zeit samt der
    Gesamtbewertung zu Buche.

    :param rgb: RgbMatrixUart, das geoeffnete Objekt der RGB-Matrix
    :param spielstand: Spielstand mit den erzielten Zeiten
    :return: None
    """
    zeiten = spielstand.zeiten
    if not zeiten:
        return

    beste = min(zeiten)
    schlechteste = max(zeiten)
    schnitt = sum(zeiten) / len(zeiten)
    gesamtnote = bewerte_zeit(schnitt)

    # --- Die Balken wachsen der Reihe nach ---------------------------------
    # Der Bildschirm wird EINMAL geloescht; hernach wird stets ueber das
    # alte Bild geschrieben. Wuerde man in jedem Durchgang loeschen, so
    # flimmerte die Anzeige unschoen.
    loesche_bildschirm()
    for schritt in range(0, 21):
        anteil = schritt / 20.0
        zeilen = []
        zeilen.append(gefaerbt('╔' + '═' * (BREITE - 2) + '╗', TUI_RAHMEN))
        zeilen.append(gefaerbt('║', TUI_RAHMEN)
                      + fuelle(mittig(gefaerbt('A U S W E R T U N G',
                                               TUI_TITEL, fett=True),
                                      BREITE - 2), BREITE - 2)
                      + gefaerbt('║', TUI_RAHMEN))
        zeilen.append(gefaerbt('╚' + '═' * (BREITE - 2) + '╝', TUI_RAHMEN))
        zeilen.append(kasten_oben('RUNDEN', BREITE))

        for nummer, zeit in enumerate(zeiten, start=1):
            note = bewerte_zeit(zeit)
            notenfarbe = BEWERTUNGSFARBEN[note]
            gewachsen = min(1.0, zeit / 700.0) * anteil
            zeilen.append(kasten_zeile(
                '  Runde {0}   {1}  {2}  {3}'.format(
                    nummer,
                    gefaerbt(balken(gewachsen, 50), notenfarbe),
                    gefaerbt('{0:7.1f} ms'.format(zeit * anteil), TUI_TEXT),
                    gefaerbt(note, notenfarbe, fett=True)),
                BREITE))

        zeilen.append(kasten_unten(BREITE))
        schreibe(('\x1b[H' if FARBEN_MOEGLICH else '')
                         + '\n'.join(fuelle(zeile, BREITE) for zeile in zeilen)
                         + '\n')
        time.sleep(0.03)

    # --- Die Kennzahlen ----------------------------------------------------
    zeilen = []
    zeilen.append(kasten_oben('KENNZAHLEN', BREITE))
    for beschriftung, wert, wertfarbe in [
            ('Beste Zeit', beste, BEWERTUNGSFARBEN[bewerte_zeit(beste)]),
            ('Schlechteste Zeit', schlechteste,
             BEWERTUNGSFARBEN[bewerte_zeit(schlechteste)]),
            ('Durchschnitt', schnitt, BEWERTUNGSFARBEN[gesamtnote])]:
        zeilen.append(kasten_zeile(
            '  {0}{1}  {2}'.format(
                gefaerbt(beschriftung.ljust(22), TUI_MATT),
                gefaerbt('{0:8.1f} ms'.format(wert), TUI_TEXT),
                gefaerbt(bewerte_zeit(wert), wertfarbe, fett=True)),
            BREITE))
    zeilen.append(kasten_zeile(
        '  {0}{1}'.format(
            gefaerbt('Fehlstarts'.ljust(22), TUI_MATT),
            gefaerbt('{0:8d}    (nicht gewertet)'.format(
                spielstand.fehlstarts), TUI_WARNUNG)), BREITE))
    zeilen.append(kasten_zeile(
        '  {0}{1}'.format(
            gefaerbt('Verpasste Runden'.ljust(22), TUI_MATT),
            gefaerbt('{0:8d}    (nicht gewertet)'.format(
                spielstand.verpasste), TUI_STEIN)), BREITE))
    zeilen.append(kasten_zeile(
        '  {0}{1}'.format(
            gefaerbt('Laengste Serie'.ljust(22), TUI_MATT),
            gefaerbt('{0:8d}    BLITZE in Folge'.format(
                spielstand.beste_serie), TUI_GOLD)), BREITE))
    zeilen.append(kasten_unten(BREITE))

    for zeile in grossschrift(gesamtnote if len(gesamtnote) <= 5 else '?'):
        zeilen.append(mittig(gefaerbt(zeile, BEWERTUNGSFARBEN[gesamtnote],
                                      fett=True), BREITE))

    schreibe('\n'.join(zeilen) + '\n')
    time.sleep(0.2)


def zeige_bestenliste_bildschirm(rgb, spielstand):
    """
    Zeiget die Bestenliste als eigenes Bild, bis eine Taste gedrueckt wird.

    :param rgb: RgbMatrixUart, das geoeffnete Objekt der RGB-Matrix
    :param spielstand: Spielstand, dessen Bestenliste gezeigt wird
    :raises SpielEnde: sofern der Spieler Q druecket
    :return: None
    """
    eintraege = lade_bestenliste()
    loesche_bildschirm()

    zeilen = []
    zeilen.append(gefaerbt('╔' + '═' * (BREITE - 2) + '╗', TUI_RAHMEN))
    zeilen.append(gefaerbt('║', TUI_RAHMEN)
                  + fuelle(mittig(gefaerbt('B E S T E N L I S T E',
                                           TUI_GOLD, fett=True), BREITE - 2),
                           BREITE - 2)
                  + gefaerbt('║', TUI_RAHMEN))
    zeilen.append(gefaerbt('╚' + '═' * (BREITE - 2) + '╝', TUI_RAHMEN))
    zeilen.append(kasten_oben('DIE SCHNELLSTEN', BREITE))

    if not eintraege:
        zeilen.append(kasten_zeile(
            '  ' + gefaerbt('Noch ist niemand verzeichnet. '
                            'Sei du der Erste!', TUI_MATT), BREITE))
    else:
        zeilen.append(kasten_zeile(
            '  {0}{1}{2}{3}{4}'.format(
                gefaerbt('Platz  ', TUI_MATT),
                gefaerbt('Name'.ljust(12), TUI_MATT),
                gefaerbt('Schnitt'.rjust(11), TUI_MATT),
                gefaerbt('Beste'.rjust(11), TUI_MATT),
                gefaerbt('   Grad     Datum', TUI_MATT)), BREITE))
        for platz, eintrag in enumerate(eintraege, start=1):
            platzfarbe = TUI_GOLD if platz <= 3 else TUI_TEXT
            zeilen.append(kasten_zeile(
                '  {0}{1}{2}{3}   {4}  {5}'.format(
                    gefaerbt('{0:>2}.    '.format(platz), platzfarbe,
                             fett=platz == 1),
                    gefaerbt(str(eintrag.get('name', '?'))[:12].ljust(12),
                             platzfarbe),
                    gefaerbt('{0:>8.1f} ms'.format(
                        eintrag.get('schnitt', 0)), TUI_TEXT),
                    gefaerbt('{0:>8.1f} ms'.format(
                        eintrag.get('beste', 0)), TUI_MATT),
                    gefaerbt(str(eintrag.get('modus', '?')).ljust(7),
                             TUI_TITEL),
                    gefaerbt(str(eintrag.get('datum', '')), TUI_MATT)),
                BREITE))

    zeilen.append(kasten_unten(BREITE))
    zeilen.append('')
    zeilen.append(' ' + gefaerbt('Beliebige Taste kehret ins Menue zurueck.',
                                 TUI_MATT))
    schreibe('\n'.join(zeilen) + '\n')

    leere_tastaturpuffer()
    while True:
        ereignis = lies_ereignis()
        if ereignis == EREIGNIS_ENDE:
            raise SpielEnde()
        if ereignis != EREIGNIS_KEINS:
            return
        time.sleep(0.02)


# =============================================================================
# ABSCHNITT 11: SPIELABLAUF
# =============================================================================

def spiele_runde(rgb, spielstand, rundennummer):
    """
    Spielet eine einzelne Runde von der Wartewelle bis zur Reaktion.

    Der Ablauf ist ebenderselbe wie im Kopf dieser Datei beschrieben:
    Wartemodus, Ampel, Blitz, Messung.

    :param rgb: RgbMatrixUart, das geoeffnete Objekt der RGB-Matrix
    :param spielstand: Spielstand, welcher fortgeschrieben wird
    :param rundennummer: int, die laufende Nummer der Runde
    :raises SpielZurueck: sofern der Spieler ESC druecket
    :raises SpielEnde: sofern der Spieler Q druecket
    :return: tuple (ergebnis, zeit_ms)
             ergebnis = str, 'gewertet', 'fehlstart' oder 'verpasst'
             zeit_ms  = float bei 'gewertet', sonst None
    """
    if spielstand.training:
        hinweis = 'TRAINING - Runde {0}. Beliebige Taste startet.'.format(
            rundennummer)
    else:
        hinweis = 'Runde {0} von {1}. Beliebige Taste startet.'.format(
            rundennummer, RUNDEN_ANZAHL)

    # 1. Wartemodus: die Welle laeuft, bis der Spieler startet
    spielstand.setze_status(hinweis, TUI_TITEL)
    zeige_sinus(rgb, spielstand)

    # 2. Ampel: Rot, Orange, Gruen
    zeige_start(rgb, spielstand)

    # 3. Blitz: zufaellige Wartezeit, alsdann die tuerkise Linie
    erfolg, zeitpunkt_des_blitzes = zeige_blitz(rgb, spielstand)
    if not erfolg:
        zeige_fehlstart(rgb, spielstand)
        return ('fehlstart', None)

    # 4. Messung: warten auf TAB, jedoch nicht laenger als die Zeitsperre
    zeit_ms = messe_reaktion(zeitpunkt_des_blitzes, rgb,
                             MODI[spielstand.modus]['sicht_ms'])
    if zeit_ms is None:
        zeige_verpasst(rgb, spielstand)
        return ('verpasst', None)

    return ('gewertet', zeit_ms)


def verarbeite_ergebnis(rgb, spielstand, ergebnis, zeit_ms):
    """
    Traegt das Ergebnis einer Runde in den Spielstand ein.

    Fehlstarts und verpasste Runden brechen ueberdies eine laufende Serie.

    :param rgb: RgbMatrixUart, das geoeffnete Objekt der RGB-Matrix
    :param spielstand: Spielstand, welcher fortgeschrieben wird
    :param ergebnis: str, 'gewertet', 'fehlstart' oder 'verpasst'
    :param zeit_ms: float oder None, die gemessene Zeit
    :return: None
    """
    if ergebnis == 'fehlstart':
        spielstand.fehlstarts += 1
        spielstand.serie = 0
        return

    if ergebnis == 'verpasst':
        spielstand.verpasste += 1
        spielstand.serie = 0
        return

    spielstand.zeiten.append(zeit_ms)

    # Die Serie zaehlet nur lauter BLITZE
    if bewerte_zeit(zeit_ms) == 'BLITZ':
        spielstand.serie += 1
        spielstand.beste_serie = max(spielstand.beste_serie,
                                     spielstand.serie)
    else:
        spielstand.serie = 0

    zeige_ergebnis(rgb, spielstand, zeit_ms)


def spiele_ein_spiel(rgb, spielstand):
    """
    Spielet ein vollstaendiges Spiel ueber fuenf gewertete Runden.

    Fehlstarts und verpasste Runden verlaengern das Spiel, da die jeweilige
    Runde wiederholet wird und nicht in die Wertung eingeht. Zum Schlusse
    wird die Statistik gezeiget und gegebenenfalls die Bestenliste ergaenzt.

    :param rgb: RgbMatrixUart, das geoeffnete Objekt der RGB-Matrix
    :param spielstand: Spielstand, welcher zuvor zurueckgesetzt wird
    :raises SpielZurueck: sofern der Spieler ESC druecket
    :raises SpielEnde: sofern der Spieler Q druecket
    :return: None
    """
    spielstand.training = False
    spielstand.zuruecksetzen()
    loesche_bildschirm()

    while len(spielstand.zeiten) < RUNDEN_ANZAHL:
        ergebnis, zeit_ms = spiele_runde(
            rgb, spielstand, len(spielstand.zeiten) + 1)
        verarbeite_ergebnis(rgb, spielstand, ergebnis, zeit_ms)

    # --- Auswertung --------------------------------------------------------
    zeige_statistik(rgb, spielstand)
    time.sleep(1.2)

    # --- Bestenliste -------------------------------------------------------
    schnitt = sum(spielstand.zeiten) / len(spielstand.zeiten)
    eintraege = lade_bestenliste()
    if ist_rekordverdaechtig(eintraege, schnitt):
        loesche_bildschirm()
        spiele_ton(TON_REKORD, spielstand)
        # Zuerst wird der Rang nur ermittelt, damit er bei der Namensfrage
        # bereits angezeigt werden kann; eingetragen wird hernach.
        _, rang = fuege_bestenliste_hinzu(
            eintraege, 'GAST', schnitt, min(spielstand.zeiten),
            spielstand.modus)
        name = frage_namen(rgb, spielstand, rang)
        eintraege, rang = fuege_bestenliste_hinzu(
            eintraege, name, schnitt, min(spielstand.zeiten),
            spielstand.modus)
        speichere_bestenliste(eintraege)
        spielstand.setze_gross('{0}'.format(rang), TUI_GOLD,
                               'PLATZ IN DER BESTENLISTE',
                               titel='REKORD')
        spielstand.setze_status(
            '{0} steht nun auf Platz {1}! Beliebige Taste ...'.format(
                name, rang), TUI_GOLD)
    else:
        spielstand.setze_gross('{0:.0f} MS'.format(schnitt),
                               BEWERTUNGSFARBEN[bewerte_zeit(schnitt)],
                               'DURCHSCHNITT')
        spielstand.setze_status(
            'Spiel beendet. Beliebige Taste startet ein neues.', TUI_TITEL)

    loesche_bildschirm()
    zeige_sinus(rgb, spielstand)


def spiele_training(rgb, spielstand):
    """
    Spielet endlos viele Runden ohne Wertung, allein zur Uebung.

    Das Training endet durch ESC (zurueck ins Menue) oder Q (Programmende).

    :param rgb: RgbMatrixUart, das geoeffnete Objekt der RGB-Matrix
    :param spielstand: Spielstand, welcher zuvor zurueckgesetzt wird
    :raises SpielZurueck: sofern der Spieler ESC druecket
    :raises SpielEnde: sofern der Spieler Q druecket
    :return: None
    """
    spielstand.zuruecksetzen()
    spielstand.training = True
    loesche_bildschirm()

    while True:
        ergebnis, zeit_ms = spiele_runde(
            rgb, spielstand, len(spielstand.zeiten) + 1)
        verarbeite_ergebnis(rgb, spielstand, ergebnis, zeit_ms)


# =============================================================================
# ABSCHNITT 12: MENUE UND HAUPTPROGRAMM
# =============================================================================

def zeige_menue(rgb, spielstand):
    """
    Zeiget das Menue, waehrend auf der Matrix die Sinuswelle laeuft.

    :param rgb: RgbMatrixUart, das geoeffnete Objekt der RGB-Matrix
    :param spielstand: Spielstand, welcher Modus und Ton verwaltet
    :raises SpielEnde: sofern der Spieler Q druecket
    :return: str, die Wahl: 'spiel', 'training' oder 'bestenliste'
    """
    spielstand.training = False
    bildabstand = 1.0 / SINUS_BILDRATE_HZ
    mitte = (MATRIX_GROESSE - 1) / 2.0
    beginn = time.perf_counter()
    leere_tastaturpuffer()
    loesche_bildschirm()

    while True:
        verstrichen = time.perf_counter() - beginn

        # --- Die Sinuswelle auf der Matrix ---------------------------------
        faerbe_alles(rgb, FARBE_AUS)
        for spalte in range(MATRIX_GROESSE):
            ort = spalte / (MATRIX_GROESSE - 1)
            winkel = (2.0 * math.pi * SINUS_PERIODEN * ort
                      - 2.0 * math.pi * SINUS_TEMPO_HZ * verstrichen)
            zeile = round(mitte - SINUS_AMPLITUDE * math.sin(winkel))
            zeile = max(0, min(MATRIX_GROESSE - 1, zeile))
            rgb.rgb_matrix[zeile][spalte] = list(FARBE_SINUS)
        rgb.sende()

        # --- Das Menuebild --------------------------------------------------
        spiegel = _zeilen_matrixspiegel(rgb)
        eintraege = [
            ('1', 'SPIEL', '{0} gewertete Runden mit Statistik'.format(
                RUNDEN_ANZAHL)),
            ('2', 'TRAINING', 'Endlos ueben, ohne Wertung'),
            ('3', 'BESTENLISTE', 'Die schnellsten Haende dieses Rechners'),
            ('M', 'SCHWIERIGKEIT', '{0} - {1}'.format(
                spielstand.modus, MODI[spielstand.modus]['text'])),
            ('T', 'TON', 'gegenwaertig {0}'.format(
                'an' if spielstand.ton_an else 'aus')),
            ('Q', 'ENDE', 'Programm verlassen'),
        ]

        zeilen = []
        zeilen.append(gefaerbt('╔' + '═' * (BREITE - 2) + '╗', TUI_RAHMEN))
        zeilen.append(gefaerbt('║', TUI_RAHMEN)
                      + fuelle(mittig(gefaerbt('R E A K T I O N S S P I E L',
                                               TUI_TITEL, fett=True),
                                      BREITE - 2), BREITE - 2)
                      + gefaerbt('║', TUI_RAHMEN))
        zeilen.append(gefaerbt('║', TUI_RAHMEN)
                      + fuelle(mittig(gefaerbt(
                          '8x8 RGB-Matrix  ·  MAX1000  ·  ' + spielstand.port,
                          TUI_MATT), BREITE - 2), BREITE - 2)
                      + gefaerbt('║', TUI_RAHMEN))
        zeilen.append(gefaerbt('╚' + '═' * (BREITE - 2) + '╝', TUI_RAHMEN))

        zeilen.append(kasten_oben('MATRIX 8x8', BREITE_LINKS)
                      + kasten_oben('AUSWAHL', BREITE_RECHTS))
        for nummer in range(MATRIX_GROESSE):
            links = '    ' + spiegel[nummer]
            if nummer < len(eintraege):
                taste, name, erklaerung = eintraege[nummer]
                rechts = '  {0}  {1}  {2}'.format(
                    gefaerbt('[' + taste + ']', TUI_GOLD, fett=True),
                    gefaerbt(name.ljust(14), TUI_TEXT),
                    gefaerbt(erklaerung, TUI_MATT))
            else:
                rechts = ''
            zeilen.append(kasten_zeile(links, BREITE_LINKS)
                          + kasten_zeile(rechts, BREITE_RECHTS))
        zeilen.append(kasten_unten(BREITE_LINKS) + kasten_unten(BREITE_RECHTS))

        zeilen.append(kasten_oben('SO WIRD GESPIELT', BREITE))
        for text in [
                'Beliebige Taste startet die Runde. Es folget die Ampel: '
                'Rot, Orange, Gruen.',
                'Nach 2 bis 6 Sekunden schiesst der tuerkise Blitz herab - '
                'alsdann sogleich TAB druecken.',
                'Unter 250 ms ist BLITZ, bis 500 ms ist WIND, darueber '
                'ist STEIN. Zu frueh ist Fehlstart.']:
            zeilen.append(kasten_zeile('  ' + gefaerbt(text, TUI_MATT),
                                       BREITE))
        zeilen.append(kasten_unten(BREITE))

        ausgabe = '\x1b[H' if FARBEN_MOEGLICH else ''
        ausgabe += '\n'.join(fuelle(zeile, BREITE) for zeile in zeilen)
        ausgabe += '\x1b[J' if FARBEN_MOEGLICH else ''
        schreibe(ausgabe)

        # --- Die Tastenwahl -------------------------------------------------
        taste = lies_taste()
        if taste is not None:
            if taste in TASTEN_ENDE:
                raise SpielEnde()
            if taste == b'1':
                return 'spiel'
            if taste == b'2':
                return 'training'
            if taste == b'3':
                return 'bestenliste'
            if taste in (b'm', b'M'):
                stelle = MODUS_REIHE.index(spielstand.modus)
                spielstand.modus = MODUS_REIHE[(stelle + 1)
                                               % len(MODUS_REIHE)]
                loesche_bildschirm()
            if taste in (b't', b'T'):
                spielstand.ton_an = not spielstand.ton_an

        time.sleep(bildabstand)


def beschaffe_matrix(port):
    """
    Beschaffet die Matrix: die echte, wo moeglich, sonst die Attrappe.

    Das Spiel soll unter allen Umstaenden spielbar sein. Darum wird zuerst
    der Anschluss versucht; gelinget er nicht - weil keine Platine angesteckt
    ist, weil ein anderes Programm den Anschluss haelt oder weil ausdruecklich
    ohne Hardware gespielt werden soll -, so tritt die Attrappe an ihre
    Stelle und alles laeuft im Matrix-Spiegel des Bedienbildes.

    Ausdruecklich ohne Hardware spielet, wer als Anschluss eines der Woerter
    'SIM', 'SIMULATION', 'OHNE' oder 'KEIN' angibt.

    :param port: str, der gewuenschte Anschluss oder ein Schluesselwort
    :return: tuple (matrix, hinweis)
             matrix  = RgbMatrixUart oder RgbMatrixAttrappe, bereits geoeffnet
             hinweis = str, eine Erlaeuterung fuer den Spieler; leer, wenn
                       die echte Matrix gefunden ward
    """
    if port.strip().upper() in ('SIM', 'SIMULATION', 'OHNE', 'KEIN'):
        attrappe = RgbMatrixAttrappe(port='SIMULATION')
        attrappe.oeffne()
        return attrappe, 'Simulation auf Wunsch: es wird ohne Hardware gespielt.'

    echte = RgbMatrixUart(port=port)
    try:
        echte.oeffne()
        return echte, ''
    except (serial.SerialException, ValueError, OSError) as fehler:
        attrappe = RgbMatrixAttrappe(port='SIMULATION')
        attrappe.oeffne()
        return attrappe, ('Anschluss {0} nicht verfuegbar ({1}). '
                          'Es wird ohne Hardware gespielt.'.format(
                              port, type(fehler).__name__))


def main():
    """
    Hauptprogramm: ruestet die Konsole, beschaffet die Matrix und fuehret
    durch Menue, Spiel und Training, bis der Spieler mittels Q beendet.

    Der Anschluss kann als erstes Argument auf der Befehlszeile uebergeben
    werden; ohne Angabe gilt PORT_STANDARD. Wird keine Matrix gefunden, so
    spielet das Spiel gleichwohl weiter - alsdann eben allein im Fenster.

    :return: None
    """
    port = sys.argv[1] if len(sys.argv) > 1 else PORT_STANDARD

    echte_konsole = bereite_konsole_vor()
    verstecke_zeiger()
    loesche_bildschirm()

    if not echte_konsole:
        print('ACHTUNG: Es liegt keine echte Konsole vor. Die Tastatur kann')
        print('so nicht abgefragt werden. Bitte das Spiel in einer')
        print('Eingabeaufforderung starten.')
        print()

    # --- Die Matrix beschaffen: echt oder als Attrappe ----------------------
    rgb, hinweis = beschaffe_matrix(port)

    spielstand = Spielstand(port=rgb.port)
    spielstand.ohne_hardware = isinstance(rgb, RgbMatrixAttrappe)

    if hinweis:
        # Der Hinweis wird kurz gezeigt, damit niemand raetselt, warum die
        # Leuchtdioden dunkel bleiben.
        loesche_bildschirm()
        print()
        print('  ' + hinweis)
        print()
        print('  Das Spiel laeuft vollstaendig weiter. Die 8x8-Matrix ist')
        print('  im Bedienbild als Spiegel zu sehen und dort voll bespielbar.')
        print()
        print('  Mit angeschlossener Platine einfach neu starten, oder einen')
        print('  anderen Anschluss angeben:  python reaktionsspiel.py COM9')
        print()
        print('  Beliebige Taste beginnet ...')
        leere_tastaturpuffer()
        wartebeginn = time.perf_counter()
        while time.perf_counter() - wartebeginn < 20.0:
            if lies_taste() is not None:
                break
            time.sleep(0.02)
        loesche_bildschirm()

    try:
        while True:
            wahl = zeige_menue(rgb, spielstand)
            try:
                if wahl == 'spiel':
                    spiele_ein_spiel(rgb, spielstand)
                elif wahl == 'training':
                    spiele_training(rgb, spielstand)
                elif wahl == 'bestenliste':
                    zeige_bestenliste_bildschirm(rgb, spielstand)
            except SpielZurueck:
                # ESC: alles wird verworfen, es geht zurueck ins Menue.
                leere_tastaturpuffer()
                loesche_matrix(rgb)
                spielstand.zuruecksetzen()

    except SpielEnde:
        pass

    except KeyboardInterrupt:
        pass

    finally:
        # Was auch immer geschehe: die Matrix wird geloescht, der Anschluss
        # geschlossen und das Textfenster ordentlich hinterlassen.
        loesche_matrix(rgb)
        rgb.schliesse()
        loesche_bildschirm()
        zeige_zeiger()
        print('Reaktionsspiel beendet.'
              + (' (Es ward ohne Hardware gespielt.)'
                 if spielstand.ohne_hardware else ' Matrix geloescht, Anschluss zu.'))


if __name__ == '__main__':
    main()
