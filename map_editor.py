import cv2
import json
import numpy as np
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk
import os

class ImprovedMapEditor:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("지능형 매크로 맵 에디터 v4.6 (UI Enhanced)")
        self.root.geometry("1200x800") 

        # --- 상태 변수 ---
        self.mode = "PAN" 
        self.show_paths = True
        self.zoom_scale = 1.0
        self.platforms = []
        self.drawing = False
        self.panning = False
        self.start_p_real = (-1, -1)
        self.last_mouse_pos = (-1, -1)
        
        self.orig_img = None
        self.curr_img = None
        self.temp_preview_img = None
        self.tk_img = None
        
        self.img_h, self.img_w = 0, 0
        self.pan_x, self.pan_y = 0, 0

        # --- 레이아웃 설정 ---
        self.sidebar = tk.Frame(self.root, width=250, relief="raised", borderwidth=1)
        self.sidebar.pack(side="left", fill="y")
        self._build_sidebar()

        self.canvas = tk.Canvas(self.sidebar.master, bg="black", cursor="cross")
        self.canvas.pack(side="right", expand=True, fill="both")

        self.canvas.bind("<Button-1>", self.on_canvas_click)
        self.canvas.bind("<B1-Motion>", self.on_canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_canvas_release)
        self.canvas.bind("<MouseWheel>", self.on_mouse_wheel)
        self.canvas.bind("<Button-3>", self.on_right_click)

        if self.load_initial_image():
            self.run_main_loop()

    def _build_sidebar(self):
        tk.Label(self.sidebar, text="[컨트롤 패널]", font=("Arial", 14, "bold")).pack(pady=15)

        mode_frame = tk.LabelFrame(self.sidebar, text="작업 모드", font=("Arial", 10))
        mode_frame.pack(fill="x", padx=10, pady=5)
        self.btn_draw = tk.Button(mode_frame, text="🛠 발판 그리기 시작", bg="lightgray", font=("Arial", 11), command=self.toggle_draw_mode)
        self.btn_draw.pack(fill="x", padx=5, pady=5)

        vis_frame = tk.LabelFrame(self.sidebar, text="시각화 설정", font=("Arial", 10))
        vis_frame.pack(fill="x", padx=10, pady=5)
        self.btn_path = tk.Button(vis_frame, text="점프 경로: ON", bg="lightblue", font=("Arial", 11), command=self.toggle_path_vis)
        self.btn_path.pack(fill="x", padx=5, pady=5)

        zoom_frame = tk.LabelFrame(self.sidebar, text="줌 컨트롤", font=("Arial", 10))
        zoom_frame.pack(fill="x", padx=10, pady=5)
        tk.Button(zoom_frame, text="🔍 확대 (+)", font=("Arial", 11), command=lambda: self.adjust_zoom(0.2)).pack(side="left", expand=True, fill="x")
        tk.Button(zoom_frame, text="🔎 축소 (-)", font=("Arial", 11), command=lambda: self.adjust_zoom(-0.2)).pack(side="left", expand=True, fill="x")

        edit_frame = tk.LabelFrame(self.sidebar, text="편집 도구", font=("Arial", 10))
        edit_frame.pack(fill="x", padx=10, pady=5)
        tk.Button(edit_frame, text="↩ 되돌리기 (Undo)", font=("Arial", 11), command=self.undo_last).pack(fill="x", padx=5, pady=2)
        tk.Button(edit_frame, text="💾 데이터 저장 (Save)", font=("Arial", 11, "bold"), command=self.save_data, bg="lightgreen").pack(fill="x", padx=5, pady=5)

    def load_initial_image(self):
        path = filedialog.askopenfilename(title="미니맵 이미지 선택")
        if not path: self.root.destroy(); return False
        img_array = np.fromfile(path, np.uint8)
        self.orig_img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
        if self.orig_img is None: return False
        self.img_h, self.img_w = self.orig_img.shape[:2]
        self.pan_x, self.pan_y = self.img_w // 2, self.img_h // 2
        self.redraw()
        return True

    def open_property_editor(self, idx):
        """[수정] 더 크고 시인성이 좋은 속성 편집창"""
        p = self.platforms[idx]
        edit_win = tk.Toplevel(self.root)
        edit_win.title(f"발판 #{idx} 상세수정")
        
        # 1. 창 크기 확대
        edit_win.geometry("400x450") 
        edit_win.attributes("-topmost", True)
        edit_win.config(padx=20, pady=20)

        # 폰트 설정 (크게)
        label_font = ("Arial", 13, "bold")
        spin_font = ("Arial", 16) # 화살표 버튼 크기는 폰트 크기에 비례함

        var_y = tk.IntVar(value=p['y'])
        var_xs = tk.IntVar(value=p['x_start'])
        var_xe = tk.IntVar(value=p['x_end'])

        def live_update(*args):
            try:
                self.platforms[idx] = {'y': var_y.get(), 'x_start': var_xs.get(), 'x_end': var_xe.get()}
                self.redraw()
            except: pass

        for var in [var_y, var_xs, var_xe]: 
            var.trace_add("write", live_update)

        # UI 구성요소 배치
        tk.Label(edit_win, text=f"■ 발판 {idx} 데이터 편집", font=("Arial", 15, "bold"), fg="blue").pack(pady=(0, 20))

        # Y 좌표
        tk.Label(edit_win, text="Y 좌표 (높이):", font=label_font).pack(anchor="w")
        tk.Spinbox(edit_win, from_=0, to=self.img_h, textvariable=var_y, font=spin_font, width=15).pack(pady=(0, 15), fill="x")

        # X 시작
        tk.Label(edit_win, text="X 시작점:", font=label_font).pack(anchor="w")
        tk.Spinbox(edit_win, from_=0, to=self.img_w, textvariable=var_xs, font=spin_font, width=15).pack(pady=(0, 15), fill="x")

        # X 종료
        tk.Label(edit_win, text="X 종료점:", font=label_font).pack(anchor="w")
        tk.Spinbox(edit_win, from_=0, to=self.img_w, textvariable=var_xe, font=spin_font, width=15).pack(pady=(0, 20), fill="x")

        # 버튼 영역
        btn_frame = tk.Frame(edit_win)
        btn_frame.pack(fill="x")
        
        tk.Button(btn_frame, text="삭제", font=("Arial", 12, "bold"), bg="#ff4444", fg="white", 
                  command=lambda: [self.platforms.pop(idx), self.redraw(), edit_win.destroy()], height=2).pack(side="left", expand=True, fill="x", padx=5)
        
        tk.Button(btn_frame, text="닫기", font=("Arial", 12), bg="lightgray", 
                  command=edit_win.destroy, height=2).pack(side="left", expand=True, fill="x", padx=5)

    def redraw(self):
        if self.orig_img is None: return
        self.curr_img = self.orig_img.copy()
        if self.show_paths:
            for i, p1 in enumerate(self.platforms):
                for j, p2 in enumerate(self.platforms):
                    if i != j and self.check_jump(p1, p2):
                        c1 = ((p1['x_start']+p1['x_end'])//2, p1['y'])
                        c2 = ((p2['x_start']+p2['x_end'])//2, p2['y'])
                        cv2.line(self.curr_img, c1, c2, (255, 120, 0), 1)
        for p in self.platforms:
            cv2.line(self.curr_img, (p['x_start'], p['y']), (p['x_end'], p['y']), (0, 255, 0), 2)
        self.temp_preview_img = self.curr_img.copy()

    def get_disp_img(self):
        src = self.temp_preview_img if self.drawing else self.curr_img
        if src is None: return None
        vw, vh = self.img_w / self.zoom_scale, self.img_h / self.zoom_scale
        x1, y1 = int(self.pan_x - vw/2), int(self.pan_y - vh/2)
        tx1, ty1, tx2, ty2 = max(0, x1), max(0, y1), min(self.img_w, int(x1+vw)), min(self.img_h, int(y1+vh))
        cropped = src[ty1:ty2, tx1:tx2]
        if cropped.size == 0: return src
        cw, ch = self.canvas.winfo_width(), self.canvas.winfo_height()
        if cw < 10: cw, ch = 800, 600
        return cv2.resize(cropped, (cw, ch), interpolation=cv2.INTER_LINEAR)

    def run_main_loop(self):
        def update():
            try:
                disp = self.get_disp_img()
                if disp is not None:
                    disp_rgb = cv2.cvtColor(disp, cv2.COLOR_BGR2RGB)
                    img_pil = Image.fromarray(disp_rgb)
                    self.tk_img = ImageTk.PhotoImage(img_pil)
                    self.canvas.delete("all")
                    self.canvas.create_image(0, 0, anchor="nw", image=self.tk_img)
                    info_text = f"Mode: {self.mode} | Zoom: x{self.zoom_scale:.1f} | Items: {len(self.platforms)}"
                    self.canvas.create_text(15, 25, text=info_text, fill="yellow", anchor="nw", font=("Arial", 14, "bold"))
                self.root.after(30, update)
            except: pass
        update()
        self.root.mainloop()

    def win_to_real(self, wx, wy):
        cw, ch = self.canvas.winfo_width(), self.canvas.winfo_height()
        vw, vh = self.img_w / self.zoom_scale, self.img_h / self.zoom_scale
        rx = int((self.pan_x - vw/2) + (wx/cw)*vw)
        ry = int((self.pan_y - vh/2) + (wy/ch)*vh)
        return rx, ry

    def on_canvas_click(self, event):
        rx, ry = self.win_to_real(event.x, event.y)
        if self.mode == "PAN":
            for i, p in enumerate(self.platforms):
                if abs(ry - p['y']) < 6 and p['x_start'] <= rx <= p['x_end']:
                    self.open_property_editor(i)
                    return
            self.panning = True
            self.last_mouse_pos = (event.x, event.y)
        elif self.mode == "DRAW":
            self.drawing = True
            self.start_p_real = (rx, ry)

    def on_canvas_drag(self, event):
        if self.panning:
            dx, dy = event.x - self.last_mouse_pos[0], event.y - self.last_mouse_pos[1]
            vw, vh = self.img_w / self.zoom_scale, self.img_h / self.zoom_scale
            cw, ch = self.canvas.winfo_width(), self.canvas.winfo_height()
            self.pan_x -= (dx / cw) * vw
            self.pan_y -= (dy / ch) * vh
            self.last_mouse_pos = (event.x, event.y)
            self.pan_x = max(0, min(self.img_w, self.pan_x))
            self.pan_y = max(0, min(self.img_h, self.pan_y))
        elif self.drawing:
            rx, ry = self.win_to_real(event.x, event.y)
            self.temp_preview_img = self.curr_img.copy()
            cv2.line(self.temp_preview_img, (self.start_p_real[0], self.start_p_real[1]), (rx, self.start_p_real[1]), (0, 0, 255), 2)

    def on_canvas_release(self, event):
        if self.drawing:
            rx, ry = self.win_to_real(event.x, event.y)
            if abs(self.start_p_real[0] - rx) > 3:
                self.platforms.append({'y': self.start_p_real[1], 'x_start': min(self.start_p_real[0], rx), 'x_end': max(self.start_p_real[0], rx)})
                self.redraw()
            self.drawing = False
        self.panning = False

    def on_right_click(self, event):
        self.panning = True
        self.last_mouse_pos = (event.x, event.y)

    def on_mouse_wheel(self, event):
        self.adjust_zoom(0.2 if event.delta > 0 else -0.2)

    def toggle_draw_mode(self):
        if self.mode == "PAN":
            self.mode = "DRAW"; self.btn_draw.config(text="✋ 화면 이동 모드로", bg="orange")
        else:
            self.mode = "PAN"; self.btn_draw.config(text="🛠 발판 그리기 시작", bg="lightgray")

    def toggle_path_vis(self):
        self.show_paths = not self.show_paths
        self.btn_path.config(text=f"점프 경로: {'ON' if self.show_paths else 'OFF'}", bg="lightblue" if self.show_paths else "gray")
        self.redraw()

    def adjust_zoom(self, val):
        self.zoom_scale = max(1.0, min(8.0, self.zoom_scale + val))

    def undo_last(self):
        if self.platforms: self.platforms.pop(); self.redraw()

    def check_jump(self, p1, p2):
        overlap = not (p1['x_end'] < p2['x_start'] or p1['x_start'] > p2['x_end'])
        dy = p1['y'] - p2['y']
        dx = min(abs(p1['x_start']-p2['x_end']), abs(p1['x_end']-p2['x_start']))
        return (overlap and 10 < dy < 55) or (not overlap and dx < 70 and abs(dy) < 30)

    def save_data(self):
        path = filedialog.asksaveasfilename(defaultextension=".json", initialfile="map_data.json")
        if path:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump({"platforms": self.platforms}, f, indent=4, ensure_ascii=False)
            messagebox.showinfo("완료", "저장되었습니다.")

if __name__ == "__main__":
    ImprovedMapEditor()