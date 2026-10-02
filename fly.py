import ctypes
import math
import random
import sys
import time
import tkinter as tk
from ctypes import wintypes
from pathlib import Path
from tkinter import messagebox
from PIL import Image, ImageTk


TRANSPARENT_COLOR = "#010203"
FRAME_INTERVAL = 0.09
TICK_INTERVAL = 33
WALK_SPEED = 115
DIRECTION_STEPS = 16
VK_CONTROL = 0x11
VK_MENU = 0x12
VK_F8 = 0x77
VK_F9 = 0x78


class DesktopFly:
    def __init__(self):
        self.root = tk.Tk()
        self.root.overrideredirect(True)
        self.root.configure(bg=TRANSPARENT_COLOR)
        self.root.wm_attributes("-transparentcolor", TRANSPARENT_COLOR)
        self.root.wm_attributes("-topmost", True)
        self.root.wm_attributes("-toolwindow", True)

        sprite_path = Path(__file__).with_name("1.png")
        if not sprite_path.is_file():
            raise FileNotFoundError(f"No se encontro el sprite: {sprite_path}")

        with Image.open(sprite_path) as image:
            sprite_sheet = image.convert("RGBA")
        self.clean_frames = self._load_frames(sprite_sheet, 0, 18)
        self.walk_frames = self._load_frames(sprite_sheet, 18, 36)
        self.frame_size = self.walk_frames[0].width
        self.direction_index = 0
        self.rotated_frames = {}

        self.canvas = tk.Canvas(
            self.root,
            width=self.frame_size,
            height=self.frame_size,
            bg=TRANSPARENT_COLOR,
            highlightthickness=0,
            borderwidth=0,
        )
        self.canvas.pack()
        self.image_id = self.canvas.create_image(0, 0, anchor="nw")
        self._show_frame(self.walk_frames[0])

        self.screen_width = self.root.winfo_screenwidth()
        self.screen_height = self.root.winfo_screenheight()
        self.max_x = max(0, self.screen_width - self.frame_size)
        self.max_y = max(0, self.screen_height - self.frame_size)
        self.x = random.uniform(0, self.max_x)
        self.y = random.uniform(0, self.max_y)
        self.target_x = self.x
        self.target_y = self.y
        self.root.geometry(f"{self.frame_size}x{self.frame_size}+{round(self.x)}+{round(self.y)}")

        self.user32 = ctypes.WinDLL("user32", use_last_error=True)
        self.root.after(100, self._configure_window)
        self.user32.GetAsyncKeyState.argtypes = (ctypes.c_int,)
        self.user32.GetAsyncKeyState.restype = ctypes.c_short
        self.hotkey_states = {VK_F8: False, VK_F9: False}

        now = time.monotonic()
        self.mode = "walking"
        self.frame_index = 0
        self.next_frame_at = now + FRAME_INTERVAL
        self.clean_at = now + random.uniform(6, 12)
        self.last_tick = now
        self.paused = False
        self.paused_at = None
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.root.after(TICK_INTERVAL, self._tick)

    def _load_frames(self, sprite_sheet, first, stop):
        cell_width = sprite_sheet.width // 6
        cell_height = sprite_sheet.height // 6
        frame_size = round(min(cell_width, cell_height) / 3.5)
        frames = []

        for index in range(first, stop):
            column, row = index % 6, index // 6
            tile = sprite_sheet.crop(
                (
                    column * cell_width,
                    row * cell_height,
                    (column + 1) * cell_width,
                    (row + 1) * cell_height,
                )
            )
            tile = tile.resize((frame_size, frame_size), Image.Resampling.LANCZOS)
            tile = self._clean_transparency(tile)
            rotation_size = math.ceil(frame_size * math.sqrt(2))
            padded_tile = Image.new("RGBA", (rotation_size, rotation_size), (0, 0, 0, 0))
            offset = (rotation_size - frame_size) // 2
            padded_tile.alpha_composite(tile, (offset, offset))
            frames.append(padded_tile)

        return frames

    def _clean_transparency(self, image):
        alpha = image.getchannel("A").point(lambda value: value if value >= 17 else 0)
        alpha_pixels = alpha.load()
        width, height = alpha.size
        visited = bytearray(width * height)

        for row_index in range(height):
            for column_index in range(width):
                offset = row_index * width + column_index
                if visited[offset] or alpha_pixels[column_index, row_index] == 0:
                    continue

                pending = [(column_index, row_index)]
                component = []
                visited[offset] = 1

                while pending:
                    current_x, current_y = pending.pop()
                    component.append((current_x, current_y))
                    for neighbor_y in range(max(0, current_y - 1), min(height, current_y + 2)):
                        for neighbor_x in range(max(0, current_x - 1), min(width, current_x + 2)):
                            neighbor_offset = neighbor_y * width + neighbor_x
                            if (
                                not visited[neighbor_offset]
                                and alpha_pixels[neighbor_x, neighbor_y] > 0
                            ):
                                visited[neighbor_offset] = 1
                                pending.append((neighbor_x, neighbor_y))

                if len(component) < 4:
                    for pixel_x, pixel_y in component:
                        alpha_pixels[pixel_x, pixel_y] = 0

        image.putalpha(alpha)
        return image

    def _show_frame(self, frame):
        cache_key = (id(frame), self.direction_index)
        photo = self.rotated_frames.get(cache_key)
        if photo is None:
            angle = -self.direction_index * (360 / DIRECTION_STEPS)
            rotated = frame.rotate(
                angle,
                resample=Image.Resampling.BICUBIC,
                fillcolor=(0, 0, 0, 0),
            )
            photo = ImageTk.PhotoImage(rotated, master=self.root)
            self.rotated_frames[cache_key] = photo
        self.canvas.itemconfigure(self.image_id, image=photo)
        self.current_frame = photo

    def _configure_window(self):
        user32 = self.user32
        user32.GetParent.argtypes = (wintypes.HWND,)
        user32.GetParent.restype = wintypes.HWND
        user32.GetWindowLongW.argtypes = (wintypes.HWND, ctypes.c_int)
        user32.GetWindowLongW.restype = ctypes.c_long
        user32.SetWindowLongW.argtypes = (wintypes.HWND, ctypes.c_int, ctypes.c_long)
        user32.SetWindowLongW.restype = ctypes.c_long
        user32.SetWindowPos.argtypes = (
            wintypes.HWND,
            wintypes.HWND,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            wintypes.UINT,
        )
        user32.SetWindowPos.restype = wintypes.BOOL

        hwnd = wintypes.HWND(self.root.winfo_id())
        hwnd = user32.GetParent(hwnd) or hwnd
        ex_style = user32.GetWindowLongW(hwnd, -20)
        ex_style |= 0x00000020 | 0x00000080 | 0x08000000
        user32.SetWindowLongW(hwnd, -20, ex_style)
        if not user32.SetWindowPos(hwnd, wintypes.HWND(-1), 0, 0, 0, 0, 0x0073):
            raise ctypes.WinError(ctypes.get_last_error())

    def _poll_hotkeys(self):
        modifiers_down = bool(self.user32.GetAsyncKeyState(VK_CONTROL) & 0x8000) and bool(
            self.user32.GetAsyncKeyState(VK_MENU) & 0x8000
        )
        for key in (VK_F8, VK_F9):
            key_down = modifiers_down and bool(self.user32.GetAsyncKeyState(key) & 0x8000)
            just_pressed = key_down and not self.hotkey_states[key]
            self.hotkey_states[key] = key_down
            if just_pressed and key == VK_F8:
                self._toggle_pause()
            elif just_pressed and key == VK_F9:
                self.close()
                return False
        return True

    def _toggle_pause(self):
        now = time.monotonic()
        self.paused = not self.paused
        if self.paused:
            self.paused_at = now
        else:
            paused_for = now - self.paused_at
            self.clean_at += paused_for
            self.next_frame_at += paused_for
            self.last_tick = now

    def _choose_target(self):
        self.target_x = random.uniform(0, self.max_x)
        self.target_y = random.uniform(0, self.max_y)

    def _tick(self):
        if not self._poll_hotkeys():
            return

        now = time.monotonic()
        if self.paused:
            self.root.after(TICK_INTERVAL, self._tick)
            return

        elapsed = min(now - self.last_tick, 0.1)
        self.last_tick = now

        if self.mode == "cleaning":
            if now >= self.next_frame_at:
                self.frame_index += 1
                if self.frame_index == len(self.clean_frames):
                    self.mode = "walking"
                    self.frame_index = 0
                    self.clean_at = now + random.uniform(9, 18)
                    self._show_frame(self.walk_frames[0])
                else:
                    self._show_frame(self.clean_frames[self.frame_index])
                self.next_frame_at = now + FRAME_INTERVAL
        elif now >= self.clean_at:
            self.mode = "cleaning"
            self.frame_index = 0
            self.next_frame_at = now + FRAME_INTERVAL
            self._show_frame(self.clean_frames[0])
        else:
            distance_x = self.target_x - self.x
            distance_y = self.target_y - self.y
            distance = (distance_x * distance_x + distance_y * distance_y) ** 0.5
            if distance > 1:
                heading = math.degrees(math.atan2(distance_x, -distance_y))
                direction_index = round(heading / (360 / DIRECTION_STEPS)) % DIRECTION_STEPS
                if direction_index != self.direction_index:
                    self.direction_index = direction_index
                    self._show_frame(self.walk_frames[self.frame_index])

            step = WALK_SPEED * elapsed
            if distance <= step or distance < 1:
                self.x, self.y = self.target_x, self.target_y
                self._choose_target()
            else:
                self.x += distance_x / distance * step
                self.y += distance_y / distance * step
            self.root.geometry(f"+{round(self.x)}+{round(self.y)}")

            if now >= self.next_frame_at:
                self.frame_index = (self.frame_index + 1) % len(self.walk_frames)
                self._show_frame(self.walk_frames[self.frame_index])
                self.next_frame_at = now + FRAME_INTERVAL

        self.root.after(TICK_INTERVAL, self._tick)

    def close(self):
        self.root.destroy()

    def run(self):
        self.root.mainloop()


def main():
    if sys.platform != "win32":
        raise SystemExit("Esta aplicacion necesita Windows.")

    try:
        DesktopFly().run()
    except (FileNotFoundError, OSError, tk.TclError) as error:
        dialog = tk.Tk()
        dialog.withdraw()
        messagebox.showerror("Mosca de escritorio", str(error), parent=dialog)
        dialog.destroy()


if __name__ == "__main__":
    main()