"""
Controles:
    Clic: acariciar
    Doble clic: alimentar
    Arrastrar: mover a Pepo
    Clic derecho: menú
    Escape o Ctrl+Alt+Q: cerrar
    Ctrl+Alt+F9: celebrar compilación
"""

import random
import sys
import time
import ctypes
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, QPoint, QRect, QSize
from PySide6.QtGui import QPainter, QPixmap, QColor, QFont, QAction
from PySide6.QtWidgets import (
    QApplication, QWidget, QMenu, QMessageBox
)

BASE_DIR = Path(__file__).resolve().parent
ASSETS_DIR = BASE_DIR / "assets"

WINDOW_WIDTH = 260
WINDOW_HEIGHT = 250
SPRITE_AREA = QSize(220, 190)
FRAME_INTERVAL_MS = 220
CLICK_DELAY_MS = 270
STATUS_INTERVAL_MS = 1000

HUNGER_PER_MINUTE = 1.0
HAPPINESS_LOSS_PER_MINUTE = 0.25

ANIMATIONS = {
    "idle": 4,
    "happy": 4,
    "sleep": 4,
    "walk": 4,
    "angry": 4,
    "love": 4,
    "eat": 4,
    "surprise": 4,
}

MESSAGES = {
    "idle": ["holiii ♡", "¿estudiamos?", "aquí contigo ♡", "qué a gustito"],
    "happy": ["¡yupi!", "¡lo conseguimos!", "jeje ♡", "estoy feliz"],
    "sleep": ["zzz...", "cinco minutitos más", "dulces sueños ♡"],
    "angry": ["¿me has olvidado?", "¡quiero mimitos!", "hmph >:("],
    "love": ["te quiero ♡", "muchos mimitos", "eres mi humana favorita"],
    "eat": ["ñam ñam", "¡qué rico!", "gracias por la comidita ♡"],
    "surprise": ["¡anda!", "¿qué ha pasado?", "¡oh!"],
    "walk": ["voy de paseo", "explorando...", "pasito a pasito"],
}


class PepoPet(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.setAutoFillBackground(False)
        self.resize(WINDOW_WIDTH, WINDOW_HEIGHT)
        self.setWindowTitle("Pepo ♡")

        self.frames = {}
        self.load_assets()

        self.state = "idle"
        self.frame_index = 0
        self.action_state = None
        self.action_frames_left = 0

        self.message = "¡holaaa! soy Pepo ♡"
        self.message_until = time.time() + 4

        self.hunger = 10.0
        self.happiness = 90.0
        self.last_interaction = time.time()
        self.last_needs_update = time.time()
        self.next_walk_at = time.time() + 25

        self.drag_offset = QPoint()
        self.dragging = False
        self.press_position = QPoint()
        self.ignore_next_release = False
        self.click_timer = QTimer(self)
        self.click_timer.setSingleShot(True)
        self.click_timer.timeout.connect(self.pet)

        self.hotkey_f9_down = False
        self.hotkey_q_down = False

        self.move_to_corner()

        self.animation_timer = QTimer(self)
        self.animation_timer.timeout.connect(self.tick_animation)
        self.animation_timer.start(FRAME_INTERVAL_MS)

        self.needs_timer = QTimer(self)
        self.needs_timer.timeout.connect(self.tick_needs)
        self.needs_timer.start(STATUS_INTERVAL_MS)

        self.hotkey_timer = QTimer(self)
        self.hotkey_timer.timeout.connect(self.check_hotkeys)
        self.hotkey_timer.start(90)

        self.show()

        missing = [name for name in ANIMATIONS if not self.frames.get(name)]
        if missing:
            QTimer.singleShot(
                700,
                lambda: QMessageBox.warning(
                    self,
                    "Pepo: faltan sprites",
                    "No he podido cargar estas animaciones:\n"
                    + ", ".join(missing)
                    + "\n\nComprueba la carpeta assets y los nombres de los PNG."
                )
            )

    def move_to_corner(self):
        screen = QApplication.primaryScreen()
        if screen:
            area = screen.availableGeometry()
            self.move(
                area.right() - self.width() - 25,
                area.bottom() - self.height() - 25
            )

    def load_assets(self):
        self.frames = {}
        for state, count in ANIMATIONS.items():
            self.frames[state] = []
            for index in range(count):
                path = ASSETS_DIR / state / f"{state}_{index}.png"
                if not path.is_file():
                    continue

                pixmap = QPixmap(str(path))
                if pixmap.isNull():
                    print(f"No se pudo abrir: {path}")
                    continue

                scaled = pixmap.scaled(
                    SPRITE_AREA,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.FastTransformation
                )

                normalized = QPixmap(SPRITE_AREA)
                normalized.fill(Qt.GlobalColor.transparent)
                painter = QPainter(normalized)
                x = (SPRITE_AREA.width() - scaled.width()) // 2
                y = (SPRITE_AREA.height() - scaled.height()) // 2
                painter.drawPixmap(x, y, scaled)
                painter.end()

                self.frames[state].append(normalized)

    def say(self, text, seconds=3):
        self.message = text
        self.message_until = time.time() + seconds
        self.update()

    def start_action(self, state, loops, message):
        frame_list = self.frames.get(state, [])
        if not frame_list:
            self.say(f"No encuentro los sprites de {state} ♡", 3)
            return

        self.action_state = state
        self.action_frames_left = len(frame_list) * max(1, loops)
        self.frame_index = 0
        self.state = state
        self.last_interaction = time.time()

        duration = self.action_frames_left * FRAME_INTERVAL_MS / 1000
        self.say(message, duration + 0.5)
        self.update()

    def pet(self):
        self.happiness = min(100, self.happiness + 12)
        self.start_action("love", 2, random.choice(MESSAGES["love"]))

    def feed(self):
        self.hunger = max(0, self.hunger - 35)
        self.happiness = min(100, self.happiness + 8)
        self.start_action("eat", 4, random.choice(MESSAGES["eat"]))

    def celebrate(self):
        self.happiness = min(100, self.happiness + 15)
        self.start_action("happy", 3, "¡LO CONSEGUISTE! ♡")

    def surprise(self):
        self.start_action("surprise", 2, random.choice(MESSAGES["surprise"]))

    def background_state(self):
        idle_seconds = time.time() - self.last_interaction

        if self.hunger >= 90 or self.happiness <= 5 or idle_seconds >= 240:
            return "angry"

        if idle_seconds >= 75:
            return "sleep"

        return "idle"

    def tick_animation(self):
        if self.action_state:
            current = self.action_state
        else:
            current = self.background_state()

            now = time.time()
            if current == "idle" and now >= self.next_walk_at:
                self.next_walk_at = now + random.randint(45, 75)
                self.start_action(
                    "walk", 2, random.choice(MESSAGES["walk"])
                )
                current = self.action_state or current

        if not self.action_state and current != self.state:
            self.state = current
            self.frame_index = 0
            if current in ("sleep", "angry"):
                self.say(random.choice(MESSAGES[current]), 4)

        frame_list = self.frames.get(current, [])
        if frame_list:
            self.frame_index = (self.frame_index + 1) % len(frame_list)

            if self.action_state:
                self.action_frames_left -= 1
                if self.action_frames_left <= 0:
                    self.action_state = None
                    self.state = self.background_state()
                    self.frame_index = 0

        self.update()

    def tick_needs(self):
        now = time.time()
        elapsed_minutes = max(0, (now - self.last_needs_update) / 60)
        self.last_needs_update = now

        self.hunger = min(100, self.hunger + HUNGER_PER_MINUTE * elapsed_minutes)
        self.happiness = max(
            0, self.happiness - HAPPINESS_LOSS_PER_MINUTE * elapsed_minutes
        )

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, False)

        frame_list = self.frames.get(
            self.action_state or self.state, []
        )

        if frame_list:
            pixmap = frame_list[self.frame_index % len(frame_list)]
            x = (self.width() - pixmap.width()) // 2
            y = 43 + (SPRITE_AREA.height() - pixmap.height()) // 2
            painter.drawPixmap(x, y, pixmap)
        else:
            self.draw_fallback(painter)

        if time.time() <= self.message_until and self.message:
            bubble = QRect(34, 5, self.width() - 68, 29)
            painter.setPen(QColor("#A9C9EE"))
            painter.setBrush(QColor(244, 250, 255, 235))
            painter.drawRoundedRect(bubble, 9, 9)
            painter.setPen(QColor("#5878A8"))
            painter.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            painter.drawText(
                bubble,
                Qt.AlignmentFlag.AlignCenter,
                self.message
            )

        painter.end()

    def draw_fallback(self, painter):
        painter.setPen(QColor("#8AADEB"))
        painter.setBrush(QColor("white"))
        painter.drawEllipse(75, 78, 110, 105)
        painter.drawEllipse(48, 95, 55, 62)
        painter.drawEllipse(157, 95, 55, 62)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#5D9FE8"))
        painter.drawEllipse(100, 116, 10, 16)
        painter.drawEllipse(150, 116, 10, 16)
        painter.setPen(QColor("#52658C"))
        painter.drawText(119, 157, "ᴗ")

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            self.press_position = event.globalPosition().toPoint()
            self.dragging = False
            event.accept()
        elif event.button() == Qt.MouseButton.RightButton:
            self.show_context_menu(event.globalPosition().toPoint())
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.MouseButton.LeftButton:
            current = event.globalPosition().toPoint()
            if (current - self.press_position).manhattanLength() > 5:
                self.dragging = True
                self.move(current - self.drag_offset)
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if self.dragging:
                self.dragging = False
            elif self.ignore_next_release:
                self.ignore_next_release = False
            elif not self.click_timer.isActive():
                self.click_timer.start(CLICK_DELAY_MS)
            event.accept()

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if self.click_timer.isActive():
                self.click_timer.stop()
            self.ignore_next_release = True
            self.feed()
            event.accept()

    def show_context_menu(self, global_pos):
        menu = QMenu(self)
        menu.addAction("♡ Acariciar a Pepo", self.pet)
        menu.addAction("🍓 Dar de comer", self.feed)
        menu.addAction("✨ Celebrar compilación", self.celebrate)
        menu.addSeparator()
        menu.addAction("Ver estado", self.show_status)
        menu.addSeparator()
        menu.addAction("Cerrar Pepo", self.close)
        menu.exec(global_pos)

    def show_status(self):
        QMessageBox.information(
            self,
            "Pepo ♡",
            f"Hambre: {self.hunger:.0f}/100\n"
            f"Felicidad: {self.happiness:.0f}/100\n\n"
            "Clic: acariciar · Doble clic: comer\n"
            "Ctrl + Alt + F9: celebrar\n"
            "Ctrl + Alt + Q: cerrar"
        )

    def check_hotkeys(self):
        if sys.platform != "win32":
            return

        try:
            user32 = ctypes.windll.user32
            ctrl = bool(user32.GetAsyncKeyState(0x11) & 0x8000)
            alt = bool(user32.GetAsyncKeyState(0x12) & 0x8000)
            f9 = bool(user32.GetAsyncKeyState(0x78) & 0x8000)
            q = bool(user32.GetAsyncKeyState(ord("Q")) & 0x8000)

            combo_f9 = ctrl and alt and f9
            combo_q = ctrl and alt and q

            if combo_f9 and not self.hotkey_f9_down:
                self.celebrate()
            if combo_q and not self.hotkey_q_down:
                self.close()
                return

            self.hotkey_f9_down = combo_f9
            self.hotkey_q_down = combo_q
        except Exception:
            pass

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.close()
        else:
            super().keyPressEvent(event)


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(True)
    pet = PepoPet()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
