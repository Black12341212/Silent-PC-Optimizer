import tkinter as tk
import time
from ui.i18n import t


def open_ram_graph(app_state):
    tracker = app_state["memory_tracker"]
    lang = app_state["config"].get("language", "ru")
    theme = app_state.get("theme_manager")
    theme_name = app_state["config"].get("theme", "dark")

    if theme:
        bg = theme.get("bg")
        fg = theme.get("fg")
        grid_color = theme.get("graph_grid")
        text_color = theme.get("graph_text")
        line_color = theme.get("graph_line")
        fill_color = theme.get("graph_fill")
    else:
        bg = "#1e1e1e"
        fg = "#ffffff"
        grid_color = "#333333"
        text_color = "#888888"
        line_color = "#0078d4"
        fill_color = "#003d6b"

    data = tracker.get_data()
    if not data:
        return

    tk_root = app_state.get("tk_root")
    if callable(tk_root):
        tk_root = tk_root()
    if tk_root:
        win = tk.Toplevel(tk_root)
    else:
        win = tk.Toplevel()
    win.title(t(lang, "stats_title", n=tracker.max_minutes))
    win.geometry("700x400")
    win.resizable(False, False)
    win.configure(bg=bg)

    canvas = tk.Canvas(win, width=680, height=340, bg=bg, highlightthickness=0)
    canvas.pack(padx=10, pady=10)

    margin_left = 60
    margin_right = 20
    margin_top = 30
    margin_bottom = 40
    w = 680 - margin_left - margin_right
    h = 340 - margin_top - margin_bottom

    canvas.create_text(
        margin_left + w // 2, 15,
        text=t(lang, "stats_title", n=tracker.max_minutes),
        fill=fg, font=("Segoe UI", 12, "bold")
    )

    now = time.time()
    time_range = tracker.max_minutes * 60
    min_time = now - time_range

    filtered = [d for d in data if d["time"] >= min_time]
    if len(filtered) < 2:
        filtered = data[-2:] if len(data) >= 2 else data

    for pct in [0, 25, 50, 75, 100]:
        y = margin_top + h - (pct / 100.0) * h
        canvas.create_line(margin_left, y, margin_left + w, y,
                           fill=grid_color, dash=(2, 4))
        canvas.create_text(margin_left - 10, y, text=f"{pct}%",
                           fill=text_color, font=("Segoe UI", 9), anchor="e")

    if len(filtered) >= 2:
        points = []
        for i, d in enumerate(filtered):
            x = margin_left + (i / (len(filtered) - 1)) * w
            y = margin_top + h - (d["ram_percent"] / 100.0) * h
            points.append((x, y))

        for i in range(len(points) - 1):
            x1, y1 = points[i]
            x2, y2 = points[i + 1]
            ram_val = filtered[i]["ram_percent"]
            if ram_val > 85:
                color = "#ff4444"
            elif ram_val > 70:
                color = "#ffaa00"
            else:
                color = "#44bb44"
            canvas.create_line(x1, y1, x2, y2, fill=color, width=2)

        fill_points = list(points)
        fill_points.append((points[-1][0], margin_top + h))
        fill_points.append((points[0][0], margin_top + h))
        flat_coords = [coord for p in fill_points for coord in p]

        last_ram = filtered[-1]["ram_percent"]
        if last_ram > 85:
            fc = "#331111"
        elif last_ram > 70:
            fc = "#332200"
        else:
            fc = "#112211"
        canvas.create_polygon(flat_coords, fill=fc, outline="")

    x_labels_count = min(7, len(filtered))
    if x_labels_count >= 2 and len(filtered) > 1:
        step = max(1, (len(filtered) - 1) // (x_labels_count - 1))
        for idx in range(0, len(filtered), step):
            d = filtered[idx]
            x = margin_left + (idx / max(1, len(filtered) - 1)) * w
            ts = time.strftime("%H:%M", time.localtime(d["time"]))
            canvas.create_text(x, margin_top + h + 20, text=ts,
                               fill=text_color, font=("Segoe UI", 8))

    latest = filtered[-1]
    canvas.create_text(
        margin_left + w // 2, margin_top + h + 35,
        text=t(lang, "ram_chart",
               ram=latest["ram_percent"], free=latest["free_gb"]),
        fill=fg, font=("Segoe UI", 10)
    )
