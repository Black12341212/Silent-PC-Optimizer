import tkinter as tk
from tkinter import ttk
import psutil
import time


class DashboardWidget:
    def __init__(self, parent, theme):
        self.frame = tk.Frame(parent, bg=theme.get("bg_secondary"), bd=0,
                              highlightbackground=theme.get("border"),
                              highlightthickness=1)
        self.theme = theme
        self.labels = {}

    def set_title(self, title, color=None):
        lbl = tk.Label(self.frame, text=title,
                       bg=self.theme.get("bg_secondary"),
                       fg=color or self.theme.get("fg"),
                       font=("Segoe UI", 10, "bold"))
        lbl.pack(anchor="w", padx=10, pady=(8, 2))
        return lbl

    def add_metric(self, key, label_text):
        row = tk.Frame(self.frame, bg=self.theme.get("bg_secondary"))
        row.pack(fill="x", padx=10, pady=2)
        name = tk.Label(row, text=label_text,
                        bg=self.theme.get("bg_secondary"),
                        fg=self.theme.get("fg_secondary"),
                        font=("Segoe UI", 9))
        name.pack(side="left")
        value = tk.Label(row, text="--",
                         bg=self.theme.get("bg_secondary"),
                         fg=self.theme.get("fg"),
                         font=("Segoe UI", 9, "bold"))
        value.pack(side="right")
        self.labels[key] = value
        return row

    def add_bar(self, key, label_text):
        row = tk.Frame(self.frame, bg=self.theme.get("bg_secondary"))
        row.pack(fill="x", padx=10, pady=4)
        name = tk.Label(row, text=label_text,
                        bg=self.theme.get("bg_secondary"),
                        fg=self.theme.get("fg_secondary"),
                        font=("Segoe UI", 9))
        name.pack(anchor="w")
        bar_frame = tk.Frame(row, bg=self.theme.get("bg_tertiary"), height=8)
        bar_frame.pack(fill="x", pady=(2, 0))
        bar_frame.pack_propagate(False)
        bar = tk.Frame(bar_frame, bg=self.theme.get("accent"), height=8)
        bar.place(x=0, y=0, relheight=1.0, relwidth=0)
        self.labels[key] = {"bar": bar, "frame": bar_frame}
        return row

    def update_metric(self, key, value_text, color=None):
        if key in self.labels and isinstance(self.labels[key], tk.Label):
            self.labels[key].config(text=value_text, fg=color or self.theme.get("fg"))

    def update_bar(self, key, percent):
        if key in self.labels:
            bar = self.labels[key]["bar"]
            pct = max(0, min(100, percent))
            bar.place(x=0, y=0, relheight=1.0, relwidth=pct / 100.0)
            if pct > 85:
                bar.config(bg=self.theme.get("danger"))
            elif pct > 70:
                bar.config(bg=self.theme.get("warning"))
            else:
                bar.config(bg=self.theme.get("success"))

    def pack(self, **kwargs):
        self.frame.pack(**kwargs)

    def grid(self, **kwargs):
        self.frame.grid(**kwargs)


class MiniGraph(tk.Canvas):
    def __init__(self, parent, theme, width=200, height=60, max_points=60):
        super().__init__(parent, width=width, height=height,
                         bg=theme.get("bg_secondary"), highlightthickness=0)
        self.theme = theme
        self.max_points = max_points
        self.data = []
        self.width = width
        self.height = height

    def add_point(self, value):
        self.data.append(value)
        if len(self.data) > self.max_points:
            self.data = self.data[-self.max_points:]
        self.redraw()

    def set_data(self, data_list):
        self.data = data_list[-self.max_points:]
        self.redraw()

    def redraw(self):
        self.delete("all")
        if len(self.data) < 2:
            return
        margin = 4
        w = self.width - 2 * margin
        h = self.height - 2 * margin
        points = []
        for i, val in enumerate(self.data):
            x = margin + (i / max(1, len(self.data) - 1)) * w
            y = margin + h - (min(100, max(0, val)) / 100.0) * h
            points.append((x, y))
        for i in range(len(points) - 1):
            x1, y1 = points[i]
            x2, y2 = points[i + 1]
            val = self.data[i]
            if val > 85:
                color = self.theme.get("danger")
            elif val > 70:
                color = self.theme.get("warning")
            else:
                color = self.theme.get("success")
            self.create_line(x1, y1, x2, y2, fill=color, width=2)
        if len(points) > 1:
            fill_pts = list(points) + [(points[-1][0], margin + h), (points[0][0], margin + h)]
            flat = [c for p in fill_pts for c in p]
            self.create_polygon(flat, fill=self.theme.get("graph_fill"), outline="")
