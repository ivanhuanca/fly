import ctypes
import math
import random
import sys
import time
import tkinter as tk
from ctypes import wintypes
from pathlib import Path
from tkinter import messagebox, ttk

from PIL import Image, ImageTk
import pystray


TRANSPARENT_COLOR = "#010203"
FRAME_INTERVAL = 0.09
TICK_INTERVAL = 33
WALK_SPEED = 115
DIRECTION_STEPS = 16
MIN_SIZE = 24
MAX_SIZE = 128
MAX_FLIES = 20
SPRITES = ("1.png", "2.png", "3.png")
VK_CONTROL = 0x11
VK_MENU = 0x12
VK_F8 = 0x77
VK_F9 = 0x78


class FlySprite:
    def __init__(self, app):
        self.app = app
        self.window = tk.Toplevel(app.root)
        self.window.overrideredirect(True)
        self.window.configure(bg=TRANSPARENT_COLOR)
        self.window.wm_attributes("-transparentcolor", TRANSPARENT_COLOR)
        self.window.wm_attributes("-topmost", True)
        self.window.wm_attributes("-toolwindow", True)

        self.canvas = tk.Canvas(
            self.window,
            width=app.window_size,
            height=app.window_size,
            bg=TRANSPARENT_COLOR,
            highlightthickness=0,
            borderwidth=0,
        )
        self.canvas.pack()
        self.image_id = self.canvas.create_image(0, 0, anchor="nw")

        self.screen_width = app.root.winfo_screenwidth()
        self.screen_height = app.root.winfo_screenheight()
        self.max_x = max(0, self.screen_width - app.window_size)
        self.max_y = max(0, self.screen_height - app.window_size)
        self.x = random.uniform(0, self.max_x)
        self.y = random.uniform(0, self.max_y)
        self.target_x = self.x
        self.target_y = self.y
        self.window.geometry(
            f"{app.window_size}x{app.window_size}+{round(self.x)}+{round(self.y)}"
        )

        now = time.monotonic()
        self.mode = "walking"
        self.frame_index = 0
        self.direction_index = 0
        self.next_frame_at = now + FRAME_INTERVAL
        self.clean_at = now + random.uniform(6, 12)
        self.last_tick = now
        self._show_frame()
        self.overlay_job = self.window.after(
            100, app._configure_overlay_window, self.window
        )

    def _show_frame(self):
        image = self.app._get_photo(self.mode, self.frame_index, self.direction_index)
        self.canvas.itemconfigure(self.image_id, image=image)

    def update_appearance(self):
        self.max_x = max(0, self.screen_width - self.app.window_size)
        self.max_y = max(0, self.screen_height - self.app.window_size)
        self.x = min(self.x, self.max_x)
        self.y = min(self.y, self.max_y)
        self.canvas.configure(width=self.app.window_size, height=self.app.window_size)
        self.window.geometry(
            f"{self.app.window_size}x{self.app.window_size}+{round(self.x)}+{round(self.y)}"
        )
        self._show_frame()

    def _choose_target(self):
        self.target_x = random.uniform(0, self.max_x)
        self.target_y = random.uniform(0, self.max_y)

    def tick(self, now):
        elapsed = min(now - self.last_tick, 0.1)
        self.last_tick = now

        if self.mode == "cleaning":
            if now >= self.next_frame_at:
                self.frame_index += 1
                if self.frame_index == 18:
                    self.mode = "walking"
                    self.frame_index = 0
                    self.clean_at = now + random.uniform(9, 18)
                self._show_frame()
                self.next_frame_at = now + FRAME_INTERVAL
            return

        if now >= self.clean_at:
            self.mode = "cleaning"
            self.frame_index = 0
            self.next_frame_at = now + FRAME_INTERVAL
            self._show_frame()
            return

        distance_x = self.target_x - self.x
        distance_y = self.target_y - self.y
        distance = (distance_x * distance_x + distance_y * distance_y) ** 0.5
        if distance > 1:
            heading = math.degrees(math.atan2(distance_x, -distance_y))
            direction_index = round(heading / (360 / DIRECTION_STEPS)) % DIRECTION_STEPS
            if direction_index != self.direction_index:
                self.direction_index = direction_index
                self._show_frame()

        step = WALK_SPEED * elapsed
        if distance <= step or distance < 1:
            self.x, self.y = self.target_x, self.target_y
            self._choose_target()
        else:
            self.x += distance_x / distance * step
            self.y += distance_y / distance * step
        self.window.geometry(f"+{round(self.x)}+{round(self.y)}")

        if now >= self.next_frame_at:
            self.frame_index = (self.frame_index + 1) % 18
            self._show_frame()
            self.next_frame_at = now + FRAME_INTERVAL

    def destroy(self):
        if self.overlay_job is not None:
            self.window.after_cancel(self.overlay_job)
            self.overlay_job = None
        self.window.destroy()


class DesktopFly:
    def __init__(self):
        if sys.platform != "win32":
            raise RuntimeError("Esta aplicacion necesita Windows.")

        self.root = tk.Tk()
        self.root.title("Moscas de escritorio")
        self.root.geometry("380x270")
        self.root.resizable(False, False)
        self.root.configure(bg="#edf2ee")
        self.root.protocol("WM_DELETE_WINDOW", self.hide_to_tray)

        self.user32 = ctypes.WinDLL("user32", use_last_error=True)
        self._configure_windows_api()
        self.user32.GetAsyncKeyState.argtypes = (ctypes.c_int,)
        self.user32.GetAsyncKeyState.restype = ctypes.c_short
        self.hotkey_states = {VK_F8: False, VK_F9: False}

        self.flies = []
        self.photo_cache = {}
        self.animations = {}
        self.active_appearance = None
        self.paused = False
        self.paused_at = None
        self.count_job = None
        self.appearance_job = None
        self.tick_job = None
        self.setting_count = False
        self.tray_icon = None
        self.tray_image = None
        self.closed = False

        self.count_var = tk.StringVar(value="3")
        self.size_var = tk.IntVar(value=56)
        self.sprite_var = tk.StringVar(value="1.png")
        self._build_panel()
        self._apply_appearance()
        self._apply_count()
        self._start_tray_icon()
        self.tick_job = self.root.after(TICK_INTERVAL, self._tick)

    def _start_tray_icon(self):
        icon_path = Path(__file__).with_name("fly.ico")
        with Image.open(icon_path) as image:
            self.tray_image = image.convert("RGBA").resize(
                (32, 32), Image.Resampling.LANCZOS
            )

        menu = pystray.Menu(
            pystray.MenuItem("Mostrar controles", self._tray_show_panel, default=True),
            pystray.MenuItem("Pausar / reanudar", self._tray_toggle_pause),
            pystray.MenuItem("Salir", self._tray_exit),
        )
        self.tray_icon = pystray.Icon(
            "MoscasEscritorio",
            self.tray_image,
            "Moscas de escritorio",
            menu=menu,
        )
        self.tray_icon.run_detached()

    def _tray_show_panel(self, _icon, _item):
        self.root.after(0, self.show_panel)

    def _tray_toggle_pause(self, _icon, _item):
        self.root.after(0, self._toggle_pause)

    def _tray_exit(self, _icon, _item):
        self.root.after(0, self.close)

    def hide_to_tray(self):
        self.root.withdraw()

    def show_panel(self):
        self.root.deiconify()
        self.root.state("normal")
        self.root.lift()
        self.root.focus_force()

    def _configure_windows_api(self):
        self.user32.GetParent.argtypes = (wintypes.HWND,)
        self.user32.GetParent.restype = wintypes.HWND
        self.user32.GetWindowLongW.argtypes = (wintypes.HWND, ctypes.c_int)
        self.user32.GetWindowLongW.restype = ctypes.c_long
        self.user32.SetWindowLongW.argtypes = (wintypes.HWND, ctypes.c_int, ctypes.c_long)
        self.user32.SetWindowLongW.restype = ctypes.c_long
        self.user32.SetWindowPos.argtypes = (
            wintypes.HWND,
            wintypes.HWND,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            wintypes.UINT,
        )
        self.user32.SetWindowPos.restype = wintypes.BOOL

    def _build_panel(self):
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure("App.TFrame", background="#edf2ee")
        style.configure(
            "Title.TLabel",
            background="#edf2ee",
            foreground="#183a34",
            font=("Segoe UI", 14, "bold"),
        )
        style.configure(
            "Status.TLabel",
            background="#edf2ee",
            foreground="#48665c",
            font=("Segoe UI", 9),
        )
        style.configure("TLabel", background="#edf2ee", foreground="#263c36")
        style.configure("TButton", padding=(10, 5))
        style.configure("TCombobox", padding=4)
        style.configure("TSpinbox", padding=4)

        panel = ttk.Frame(self.root, style="App.TFrame", padding=(20, 18))
        panel.pack(fill="both", expand=True)
        panel.columnconfigure(1, weight=1)

        ttk.Label(panel, text="Moscas de escritorio", style="Title.TLabel").grid(
            row=0, column=0, columnspan=2, sticky="w"
        )
        ttk.Separator(panel).grid(row=1, column=0, columnspan=2, sticky="ew", pady=(12, 14))

        ttk.Label(panel, text="Cantidad").grid(row=2, column=0, sticky="w", pady=5)
        count_input = ttk.Spinbox(
            panel,
            from_=0,
            to=MAX_FLIES,
            width=7,
            textvariable=self.count_var,
            command=self._apply_count,
        )
        count_input.grid(row=2, column=1, sticky="e", pady=5)
        count_input.bind("<KeyRelease>", self._queue_count_update)
        count_input.bind("<FocusOut>", self._apply_count)
        count_input.bind("<Return>", self._apply_count)
        self.count_var.trace_add("write", self._queue_count_update)

        size_row = ttk.Frame(panel, style="App.TFrame")
        size_row.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(4, 0))
        ttk.Label(size_row, text="Tamano").pack(side="left")
        self.size_value = ttk.Label(size_row, text="56 px", style="Status.TLabel")
        self.size_value.pack(side="right")
        self.size_scale = tk.Scale(
            panel,
            from_=MIN_SIZE,
            to=MAX_SIZE,
            resolution=4,
            orient="horizontal",
            variable=self.size_var,
            showvalue=False,
            highlightthickness=0,
            bd=0,
            bg="#edf2ee",
            fg="#263c36",
            troughcolor="#cbd9cf",
            activebackground="#d45c37",
            command=self._queue_appearance_update,
        )
        self.size_scale.grid(row=4, column=0, columnspan=2, sticky="ew")

        ttk.Label(panel, text="Sprite").grid(row=5, column=0, sticky="w", pady=(5, 10))
        sprite_input = ttk.Combobox(
            panel,
            textvariable=self.sprite_var,
            values=SPRITES,
            state="readonly",
            width=12,
        )
        sprite_input.grid(row=5, column=1, sticky="e", pady=(5, 10))
        sprite_input.bind("<<ComboboxSelected>>", self._select_sprite)

        actions = ttk.Frame(panel, style="App.TFrame")
        actions.grid(row=6, column=0, columnspan=2, sticky="ew", pady=(3, 0))
        self.pause_button = ttk.Button(actions, text="Pausar", command=self._toggle_pause)
        self.pause_button.pack(side="left")
        self.status_label = ttk.Label(actions, text="", style="Status.TLabel")
        self.status_label.pack(side="right", pady=5)

    def _load_animation(self, sprite_name, size):
        sprite_path = Path(__file__).with_name(sprite_name)
        if not sprite_path.is_file():
            raise FileNotFoundError(f"No se encontro el sprite: {sprite_path}")

        with Image.open(sprite_path) as image:
            sprite_sheet = image.convert("RGBA")

        animations = {"cleaning": [], "walking": []}
        window_size = math.ceil(size * math.sqrt(2))
        for index in range(36):
            column, row = index % 6, index // 6
            left = round(column * sprite_sheet.width / 6)
            top = round(row * sprite_sheet.height / 6)
            right = round((column + 1) * sprite_sheet.width / 6)
            bottom = round((row + 1) * sprite_sheet.height / 6)
            tile = sprite_sheet.crop((left, top, right, bottom))
            tile = tile.resize((size, size), Image.Resampling.LANCZOS)
            tile = self._clean_transparency(tile)
            padded_tile = Image.new("RGBA", (window_size, window_size), (0, 0, 0, 0))
            offset = ((window_size - size) // 2, (window_size - size) // 2)
            padded_tile.alpha_composite(tile, offset)
            mode = "cleaning" if index < 18 else "walking"
            animations[mode].append(padded_tile)

        return animations, window_size

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

    def _get_photo(self, mode, frame_index, direction_index):
        cache_key = (mode, frame_index, direction_index)
        photo = self.photo_cache.get(cache_key)
        if photo is None:
            frame = self.animations[mode][frame_index]
            angle = -direction_index * (360 / DIRECTION_STEPS)
            rotated = frame.rotate(
                angle,
                resample=Image.Resampling.BICUBIC,
                fillcolor=(0, 0, 0, 0),
            )
            photo = ImageTk.PhotoImage(rotated, master=self.root)
            self.photo_cache[cache_key] = photo
        return photo

    def _configure_overlay_window(self, window):
        hwnd = wintypes.HWND(window.winfo_id())
        hwnd = self.user32.GetParent(hwnd) or hwnd
        ex_style = self.user32.GetWindowLongW(hwnd, -20)
        ex_style |= 0x00000020 | 0x00000080 | 0x08000000
        self.user32.SetWindowLongW(hwnd, -20, ex_style)
        if not self.user32.SetWindowPos(hwnd, wintypes.HWND(-1), 0, 0, 0, 0, 0x0073):
            raise ctypes.WinError(ctypes.get_last_error())

    def _queue_count_update(self, *_):
        if self.setting_count or not self.count_var.get().isdigit():
            return
        if self.count_job is not None:
            self.root.after_cancel(self.count_job)
        self.count_job = self.root.after(120, self._apply_count)

    def _apply_count(self, _event=None):
        self.count_job = None
        value = self.count_var.get()
        if not value.isdigit():
            self.setting_count = True
            self.count_var.set(str(len(self.flies)))
            self.setting_count = False
            return

        requested = max(0, min(MAX_FLIES, int(value)))
        if requested != int(value):
            self.setting_count = True
            self.count_var.set(str(requested))
            self.setting_count = False

        while len(self.flies) < requested:
            self.flies.append(FlySprite(self))
        while len(self.flies) > requested:
            self.flies.pop().destroy()
        self._update_status()

    def _queue_appearance_update(self, value=None):
        if value is not None:
            size = int(round(float(value) / 4) * 4)
            self.size_value.configure(text=f"{size} px")
        if self.appearance_job is not None:
            self.root.after_cancel(self.appearance_job)
        self.appearance_job = self.root.after(120, self._apply_appearance)

    def _select_sprite(self, _event=None):
        if self.appearance_job is not None:
            self.root.after_cancel(self.appearance_job)
            self.appearance_job = None
        self._apply_appearance()

    def _apply_appearance(self):
        self.appearance_job = None
        sprite_name = self.sprite_var.get()
        size = int(self.size_var.get())
        appearance = (sprite_name, size)
        if appearance == self.active_appearance:
            return

        self.animations, self.window_size = self._load_animation(sprite_name, size)
        self.active_appearance = appearance
        self.photo_cache.clear()
        for fly in self.flies:
            fly.update_appearance()
        self._update_status()

    def _update_status(self):
        count = len(self.flies)
        noun = "mosca" if count == 1 else "moscas"
        self.status_label.configure(text=f"{count} {noun} | {self.sprite_var.get()}")

    def _toggle_pause(self):
        now = time.monotonic()
        if self.paused:
            paused_for = now - self.paused_at
            for fly in self.flies:
                fly.clean_at += paused_for
                fly.next_frame_at += paused_for
                fly.last_tick = now
            self.paused = False
            self.pause_button.configure(text="Pausar")
        else:
            self.paused = True
            self.paused_at = now
            self.pause_button.configure(text="Reanudar")

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

    def _tick(self):
        self.tick_job = None
        if not self._poll_hotkeys():
            return
        if not self.paused:
            now = time.monotonic()
            for fly in tuple(self.flies):
                fly.tick(now)
        self.tick_job = self.root.after(TICK_INTERVAL, self._tick)

    def close(self):
        if self.closed:
            return
        self.closed = True
        for job in (self.count_job, self.appearance_job, self.tick_job):
            if job is not None:
                self.root.after_cancel(job)
        self.count_job = None
        self.appearance_job = None
        self.tick_job = None
        if self.tray_icon is not None:
            self.tray_icon.stop()
            self.tray_icon = None
        for fly in self.flies:
            fly.destroy()
        self.flies.clear()
        self.root.destroy()

    def run(self):
        self.root.mainloop()


def main():
    try:
        DesktopFly().run()
    except (FileNotFoundError, OSError, RuntimeError, tk.TclError) as error:
        dialog = tk.Tk()
        dialog.withdraw()
        messagebox.showerror("Moscas de escritorio", str(error), parent=dialog)
        dialog.destroy()


if __name__ == "__main__":
    main()