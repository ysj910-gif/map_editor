# ui_widgets.py
import tkinter as tk
from app_config import Config

class PropertyEditor(tk.Toplevel):
    def __init__(self, parent, idx, platform, img_h, img_w, on_update, on_delete):
        super().__init__(parent)
        self.title(f"발판 #{idx} 상세수정")
        self.geometry("400x450")
        self.attributes("-topmost", True)
        self.config(padx=20, pady=20)
        
        self.var_y = tk.IntVar(value=platform['y'])
        self.var_xs = tk.IntVar(value=platform['x_start'])
        self.var_xe = tk.IntVar(value=platform['x_end'])

        self.var_y.trace_add("write", lambda *a: on_update(idx, self.get_values()))
        self.var_xs.trace_add("write", lambda *a: on_update(idx, self.get_values()))
        self.var_xe.trace_add("write", lambda *a: on_update(idx, self.get_values()))

        self._build_ui(idx, img_h, img_w, on_delete)

    def get_values(self):
        return {'y': self.var_y.get(), 'x_start': self.var_xs.get(), 'x_end': self.var_xe.get()}

    def _build_ui(self, idx, img_h, img_w, on_delete):
        tk.Label(self, text=f"■ 발판 {idx} 데이터 편집", font=("Arial", 15, "bold"), fg="blue").pack(pady=(0, 20))
        tk.Label(self, text="Y 좌표 (높이):", font=Config.FONT_LABEL).pack(anchor="w")
        tk.Spinbox(self, from_=0, to=img_h, textvariable=self.var_y, font=Config.FONT_SPIN).pack(pady=(0, 15), fill="x")
        tk.Label(self, text="X 시작점:", font=Config.FONT_LABEL).pack(anchor="w")
        tk.Spinbox(self, from_=0, to=img_w, textvariable=self.var_xs, font=Config.FONT_SPIN).pack(pady=(0, 15), fill="x")
        tk.Label(self, text="X 종료점:", font=Config.FONT_LABEL).pack(anchor="w")
        tk.Spinbox(self, from_=0, to=img_w, textvariable=self.var_xe, font=Config.FONT_SPIN).pack(pady=(0, 20), fill="x")
        
        btn_frame = tk.Frame(self)
        btn_frame.pack(fill="x")
        tk.Button(btn_frame, text="삭제", bg=Config.COLOR_DELETE, fg="white", font=Config.FONT_NORMAL,
                  command=lambda: [on_delete(idx), self.destroy()]).pack(side="left", expand=True, fill="x", padx=5)
        tk.Button(btn_frame, text="닫기", bg="lightgray", font=Config.FONT_NORMAL,
                  command=self.destroy).pack(side="left", expand=True, fill="x", padx=5)

class PortalEditor(tk.Toplevel):
    def __init__(self, parent, idx, portal, img_h, img_w, on_update, on_delete):
        super().__init__(parent)
        self.title(f"포탈 #{idx} 상세수정")
        self.geometry("350x450")
        self.attributes("-topmost", True)
        self.config(padx=15, pady=15)
        
        self.vars = {
            'in_x': tk.IntVar(value=portal['in_x']), 'in_y': tk.IntVar(value=portal['in_y']),
            'out_x': tk.IntVar(value=portal['out_x']), 'out_y': tk.IntVar(value=portal['out_y'])
        }

        for var in self.vars.values():
            var.trace_add("write", lambda *a: on_update(idx, self.get_values()))

        self._build_ui(idx, img_h, img_w, on_delete)

    def get_values(self):
        return {k: v.get() for k, v in self.vars.items()}

    def _build_ui(self, idx, img_h, img_w, on_delete):
        tk.Label(self, text=f"🌀 포탈 {idx} 좌표 편집", font=("Arial", 13, "bold")).pack(pady=10)
        for key in ['in_x', 'in_y', 'out_x', 'out_y']:
            label_text = f"{key.replace('_', ' ').upper()}:"
            tk.Label(self, text=label_text).pack(anchor="w")
            tk.Spinbox(self, from_=0, to=img_w if 'x' in key else img_h, 
                       textvariable=self.vars[key], font=("Arial", 12)).pack(fill="x", pady=2)
        tk.Button(self, text="삭제", bg="#ff4444", fg="white", 
                  command=lambda: [on_delete(idx), self.destroy()]).pack(fill="x", pady=20)

class SpawnEditor(tk.Toplevel):
    def __init__(self, parent, idx, spawn, img_h, img_w, on_update, on_delete):
        super().__init__(parent)
        self.title(f"스폰 #{idx} 상세수정")
        self.geometry("350x350")
        self.attributes("-topmost", True)
        self.config(padx=15, pady=15)
        
        self.var_x = tk.IntVar(value=spawn['x'])
        self.var_y = tk.IntVar(value=spawn['y'])
        self.var_desc = tk.StringVar(value=spawn.get('desc', ''))

        self.var_x.trace_add("write", lambda *a: on_update(idx, self.get_values()))
        self.var_y.trace_add("write", lambda *a: on_update(idx, self.get_values()))
        # Description은 trace하지 않고 닫을 때 저장하거나 엔터 칠 때 저장 (여기선 단순화)

        self._build_ui(idx, img_h, img_w, on_delete)

    def get_values(self):
        return {'x': self.var_x.get(), 'y': self.var_y.get(), 'desc': self.var_desc.get()}

    def _build_ui(self, idx, img_h, img_w, on_delete):
        tk.Label(self, text=f"👾 스폰 #{idx} 편집", font=("Arial", 13, "bold")).pack(pady=10)
        
        tk.Label(self, text="X 좌표:").pack(anchor="w")
        tk.Spinbox(self, from_=0, to=img_w, textvariable=self.var_x, font=("Arial", 12)).pack(fill="x", pady=2)
        
        tk.Label(self, text="Y 좌표:").pack(anchor="w")
        tk.Spinbox(self, from_=0, to=img_h, textvariable=self.var_y, font=("Arial", 12)).pack(fill="x", pady=2)
        
        tk.Label(self, text="설명 (옵션):").pack(anchor="w")
        tk.Entry(self, textvariable=self.var_desc, font=("Arial", 12)).pack(fill="x", pady=2)

        tk.Button(self, text="삭제", bg="#ff4444", fg="white", 
                  command=lambda: [on_delete(idx), self.destroy()]).pack(fill="x", pady=20)