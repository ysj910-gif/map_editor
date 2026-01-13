# main.py
import cv2
import json
import numpy as np
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk

from app_config import Config
from map_logic import MapLogic
from ui_widgets import PropertyEditor

class ImprovedMapEditor:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title(Config.TITLE)
        self.root.geometry(Config.WINDOW_SIZE)
        self.portals = [] 
        self.picking_exit = False # 포탈 출구 선택 중인지 여부
        self.portal_in_temp = (-1, -1)


        # 상태 변수
        self.mode = "PAN"
        self.show_paths = True
        self.zoom_scale = 1.0
        self.platforms = []
        self.drawing = False
        self.panning = False
        self.start_p_real = (-1, -1)
        self.last_mouse_pos = (-1, -1)
        
        self.orig_img, self.curr_img, self.temp_preview_img = None, None, None
        self.img_h, self.img_w = 0, 0
        self.pan_x, self.pan_y = 0, 0

        self._setup_layout()
        if self.load_initial_image():
            self.run_main_loop()

    def _setup_layout(self):
        # Sidebar
        self.sidebar = tk.Frame(self.root, width=Config.SIDEBAR_WIDTH, relief="raised", borderwidth=1)
        self.sidebar.pack(side="left", fill="y")
        self._build_sidebar()

        # Canvas
        self.canvas = tk.Canvas(self.root, bg="black", cursor="cross")
        self.canvas.pack(side="right", expand=True, fill="both")
        self._bind_events()

    def _build_sidebar(self):
        tk.Label(self.sidebar, text="[컨트롤 패널]", font=Config.FONT_BOLD).pack(pady=15)
        
        # Mode Toggle
        mode_frame = tk.LabelFrame(self.sidebar, text="작업 모드")
        mode_frame.pack(fill="x", padx=10, pady=5)
        self.btn_draw = tk.Button(mode_frame, text="🛠 발판 그리기 시작", bg=Config.COLOR_DRAW_INACTIVE, command=self.toggle_draw_mode)
        self.btn_draw.pack(fill="x", padx=5, pady=5)

        # Visualization
        vis_frame = tk.LabelFrame(self.sidebar, text="시각화 설정")
        vis_frame.pack(fill="x", padx=10, pady=5)
        self.btn_path = tk.Button(vis_frame, text="점프 경로: ON", bg=Config.COLOR_PATH_ON, command=self.toggle_path_vis)
        self.btn_path.pack(fill="x", padx=5, pady=5)

        # Zoom
        zoom_frame = tk.LabelFrame(self.sidebar, text="줌 컨트롤")
        zoom_frame.pack(fill="x", padx=10, pady=5)
        tk.Button(zoom_frame, text="🔍 확대 (+)", command=lambda: self.adjust_zoom(0.2)).pack(side="left", expand=True, fill="x")
        tk.Button(zoom_frame, text="🔎 축소 (-)", command=lambda: self.adjust_zoom(-0.2)).pack(side="left", expand=True, fill="x")

        # Edit/Save
        edit_frame = tk.LabelFrame(self.sidebar, text="편집 도구")
        edit_frame.pack(fill="x", padx=10, pady=5)
        tk.Button(edit_frame, text="↩ 되돌리기 (Undo)", command=self.undo_last).pack(fill="x", padx=5, pady=2)
        tk.Button(edit_frame, text="💾 데이터 저장 (Save)", bg=Config.COLOR_SAVE, font=Config.FONT_BOLD, command=self.save_data).pack(fill="x", padx=5, pady=5)

        # ... 기존 발판 버튼 아래에 포탈 버튼 추가 ...
        self.btn_portal = tk.Button(mode_frame, text="🌀 포탈 추가 (클릭-클릭)", 
                                     bg=Config.COLOR_PORTAL_INACTIVE, command=lambda: self.set_mode("PORTAL"))
        self.btn_portal.pack(fill="x", padx=5, pady=5)
    
    def set_mode(self, mode):
        self.mode = mode
        self.picking_exit = False # 모드 변경 시 진행 중인 포탈 작업 취소
        self.btn_draw.config(bg=Config.COLOR_DRAW_ACTIVE if mode == "DRAW" else Config.COLOR_DRAW_INACTIVE)
        self.btn_portal.config(bg=Config.COLOR_PORTAL_ACTIVE if mode == "PORTAL" else Config.COLOR_PORTAL_INACTIVE)


    def _bind_events(self):
        self.canvas.bind("<Button-1>", self.on_canvas_click)
        self.canvas.bind("<B1-Motion>", self.on_canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_canvas_release)
        self.canvas.bind("<MouseWheel>", self.on_mouse_wheel)
        self.canvas.bind("<Button-3>", self.on_right_click)

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

    def on_platform_update(self, idx, new_data):
        self.platforms[idx] = new_data
        self.redraw()

    def on_platform_delete(self, idx):
        self.platforms.pop(idx)
        self.redraw()

    def redraw(self):
        if self.orig_img is None: return
        self.curr_img = self.orig_img.copy()
        if self.show_paths:
            for i, p1 in enumerate(self.platforms):
                for j, p2 in enumerate(self.platforms):
                    if i != j and MapLogic.check_jump(p1, p2):
                        c1 = ((p1['x_start']+p1['x_end'])//2, p1['y'])
                        c2 = ((p2['x_start']+p2['x_end'])//2, p2['y'])
                        cv2.line(self.curr_img, c1, c2, (255, 120, 0), 1)
        for p in self.platforms:
            cv2.line(self.curr_img, (p['x_start'], p['y']), (p['x_end'], p['y']), (0, 255, 0), 2)
        self.temp_preview_img = self.curr_img.copy()
        for p in self.portals:
            cv2.arrowedLine(self.curr_img, (p['in_x'], p['in_y']), (p['out_x'], p['out_y']), (255, 100, 0), 2)
            cv2.circle(self.curr_img, (p['in_x'], p['in_y']), 4, (255, 0, 0), -1)
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
                    info = f"Mode: {self.mode} | Zoom: x{self.zoom_scale:.1f} | Items: {len(self.platforms)}"
                    self.canvas.create_text(15, 25, text=info, fill="yellow", anchor="nw", font=("Arial", 14, "bold"))
                self.root.after(30, update)
            except: pass
        update()
        self.root.mainloop()

    # 이벤트 핸들러 및 기타 헬퍼 함수들은 기존 로직과 동일하게 유지...
    def win_to_real(self, wx, wy):
        cw, ch = self.canvas.winfo_width(), self.canvas.winfo_height()
        vw, vh = self.img_w / self.zoom_scale, self.img_h / self.zoom_scale
        rx = int((self.pan_x - vw/2) + (wx/cw)*vw)
        ry = int((self.pan_y - vh/2) + (wy/ch)*vh)
        return rx, ry

    def on_canvas_click(self, event):
        rx, ry = self.win_to_real(event.x, event.y)
        
        if self.mode == "PAN":
            # 1. 포탈 선택 확인
            p_idx = MapLogic.find_clicked_portal(self.portals, rx, ry)
            if p_idx is not None:
                PortalEditor(self.root, p_idx, self.portals[p_idx], self.img_h, self.img_w, 
                             self.on_portal_update, self.on_portal_delete)
                return
            # 2. 발판 선택 확인
            idx = MapLogic.find_clicked_platform(self.platforms, rx, ry)
            if idx is not None:
                PropertyEditor(self.root, idx, self.platforms[idx], self.img_h, self.img_w, 
                               self.on_platform_update, self.on_platform_delete)
                return
            self.panning, self.last_mouse_pos = True, (event.x, event.y)

        elif self.mode == "PORTAL":
            if not self.picking_exit:
                # 첫 클릭: 입구 고정
                self.portal_in_temp = (rx, ry)
                self.picking_exit = True
            else:
                # 두 번째 클릭: 포탈 완성
                self.portals.append({
                    'in_x': self.portal_in_temp[0], 'in_y': self.portal_in_temp[1],
                    'out_x': rx, 'out_y': ry
                })
                self.picking_exit = False
                self.redraw()

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

    def on_portal_update(self, idx, data):
        self.portals[idx] = data
        self.redraw()

    def on_portal_delete(self, idx):
        self.portals.pop(idx)
        self.redraw()

    def save_data(self):
        # ... (포탈 리스트 포함하여 저장) ...
        json.dump({"platforms": self.platforms, "portals": self.portals}, f, indent=4, ensure_ascii=False)

    def on_right_click(self, event):
        self.panning = True
        self.last_mouse_pos = (event.x, event.y)

    def on_mouse_wheel(self, event):
        self.adjust_zoom(0.2 if event.delta > 0 else -0.2)

    def toggle_draw_mode(self):
        if self.mode == "PAN":
            self.mode = "DRAW"; self.btn_draw.config(text="✋ 화면 이동 모드로", bg=Config.COLOR_DRAW_ACTIVE)
        else:
            self.mode = "PAN"; self.btn_draw.config(text="🛠 발판 그리기 시작", bg=Config.COLOR_DRAW_INACTIVE)

    def toggle_path_vis(self):
        self.show_paths = not self.show_paths
        self.btn_path.config(text=f"점프 경로: {'ON' if self.show_paths else 'OFF'}", bg=Config.COLOR_PATH_ON if self.show_paths else Config.COLOR_PATH_OFF)
        self.redraw()

    def adjust_zoom(self, val):
        self.zoom_scale = max(1.0, min(8.0, self.zoom_scale + val))

    def undo_last(self):
        if self.platforms: self.platforms.pop(); self.redraw()

    def save_data(self):
        path = filedialog.asksaveasfilename(defaultextension=".json", initialfile="map_data.json")
        if path:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump({"platforms": self.platforms}, f, indent=4, ensure_ascii=False)
            messagebox.showinfo("완료", "저장되었습니다.")
        

if __name__ == "__main__":
    ImprovedMapEditor()