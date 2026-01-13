import cv2
import json
import numpy as np
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk

from app_config import Config
from map_logic import MapLogic
from ui_widgets import PropertyEditor, PortalEditor # [수정] PortalEditor 추가

class ImprovedMapEditor:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title(Config.TITLE)
        self.root.geometry(Config.WINDOW_SIZE)

        # 상태 및 데이터 변수
        self.mode = "PAN"
        self.platforms = []
        self.portals = [] 
        self.show_paths = True
        self.zoom_scale = 1.0
        self.drawing = False
        self.panning = False
        self.picking_exit = False
        self.portal_in_temp = (-1, -1)
        self.start_p_real = (-1, -1)
        self.last_mouse_pos = (-1, -1)
        
        self.orig_img, self.curr_img, self.temp_preview_img = None, None, None
        self.img_h, self.img_w = 0, 0
        self.pan_x, self.pan_y = 0, 0

        self._setup_layout()
        if self.load_initial_image():
            self.run_main_loop()

    def _setup_layout(self):
        self.sidebar = tk.Frame(self.root, width=Config.SIDEBAR_WIDTH, relief="raised", borderwidth=1)
        self.sidebar.pack(side="left", fill="y")
        self._build_sidebar()

        self.canvas = tk.Canvas(self.root, bg="black", cursor="cross")
        self.canvas.pack(side="right", expand=True, fill="both")
        self._bind_events()

    def _build_sidebar(self):
        tk.Label(self.sidebar, text="[컨트롤 패널]", font=Config.FONT_BOLD).pack(pady=15)
        
        mode_frame = tk.LabelFrame(self.sidebar, text="작업 모드")
        mode_frame.pack(fill="x", padx=10, pady=5)
        
        self.btn_draw = tk.Button(mode_frame, text="🛠 발판 그리기", bg=Config.COLOR_DRAW_INACTIVE, command=lambda: self.set_mode("DRAW"))
        self.btn_draw.pack(fill="x", padx=5, pady=2)

        self.btn_portal = tk.Button(mode_frame, text="🌀 포탈 추가 (클릭-클릭)", bg=Config.COLOR_PORTAL_INACTIVE, command=lambda: self.set_mode("PORTAL"))
        self.btn_portal.pack(fill="x", padx=5, pady=2)

        self.btn_pan = tk.Button(mode_frame, text="✋ 화면 이동 모드", bg=Config.COLOR_DRAW_ACTIVE, command=lambda: self.set_mode("PAN"))
        self.btn_pan.pack(fill="x", padx=5, pady=2)

        tk.Button(self.sidebar, text="💾 데이터 저장", bg=Config.COLOR_SAVE, font=Config.FONT_BOLD, command=self.save_data).pack(side="bottom", fill="x", pady=10)
        
        # [복구] 편집 도구 프레임 추가
        edit_frame = tk.LabelFrame(self.sidebar, text="편집 도구")
        edit_frame.pack(fill="x", padx=10, pady=5)
        
        # 되돌리기 버튼
        tk.Button(edit_frame, text="↩ 되돌리기 (Undo)", command=self.undo_last).pack(fill="x", padx=5, pady=2)
        
        # 데이터 저장 버튼 (Config 클래스 참조)
        tk.Button(edit_frame, text="💾 데이터 저장 (Save)", bg=Config.COLOR_SAVE, 
                  font=Config.FONT_BOLD, command=self.save_data).pack(fill="x", padx=5, pady=5)

    def set_mode(self, mode):
        """[개선] 모든 모드 전환을 통합 관리"""
        self.mode = mode
        self.picking_exit = False
        self.drawing = False
        self.btn_draw.config(bg=Config.COLOR_DRAW_ACTIVE if mode == "DRAW" else Config.COLOR_DRAW_INACTIVE)
        self.btn_portal.config(bg=Config.COLOR_PORTAL_ACTIVE if mode == "PORTAL" else Config.COLOR_PORTAL_INACTIVE)
        self.btn_pan.config(bg=Config.COLOR_DRAW_ACTIVE if mode == "PAN" else Config.COLOR_DRAW_INACTIVE)

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

    def redraw(self):
        if self.orig_img is None: return
        self.curr_img = self.orig_img.copy()
        # 발판 그리기
        for p in self.platforms:
            cv2.line(self.curr_img, (p['x_start'], p['y']), (p['x_end'], p['y']), (0, 255, 0), 2)
        # 포탈 그리기
        for p in self.portals:
            cv2.arrowedLine(self.curr_img, (p['in_x'], p['in_y']), (p['out_x'], p['out_y']), Config.COLOR_PORTAL_LINE, 2)
            cv2.circle(self.curr_img, (p['in_x'], p['in_y']), 4, (255, 0, 0), -1)
        self.temp_preview_img = self.curr_img.copy()

    def win_to_real(self, wx, wy):
        """[수정] 캔버스 크기 정밀 보정 및 좌표 변환"""
        cw, ch = max(10, self.canvas.winfo_width()), max(10, self.canvas.winfo_height())
        vw, vh = self.img_w / self.zoom_scale, self.img_h / self.zoom_scale
        rx = int((self.pan_x - vw/2) + (wx/cw)*vw)
        ry = int((self.pan_y - vh/2) + (wy/ch)*vh)
        return rx, ry

    def on_canvas_click(self, event):
        rx, ry = self.win_to_real(event.x, event.y)
        if self.mode == "PAN":
            # 1. 포탈 감지
            p_idx = MapLogic.find_clicked_portal(self.portals, rx, ry)
            if p_idx is not None:
                PortalEditor(self.root, p_idx, self.portals[p_idx], self.img_h, self.img_w, 
                             self.on_item_update, self.on_portal_delete)
                return
            # 2. 발판 감지
            idx = MapLogic.find_clicked_platform(self.platforms, rx, ry)
            if idx is not None:
                PropertyEditor(self.root, idx, self.platforms[idx], self.img_h, self.img_w, 
                               self.on_item_update, self.on_platform_delete)
                return
            self.panning, self.last_mouse_pos = True, (event.x, event.y)
        elif self.mode == "DRAW":
            self.drawing, self.start_p_real = True, (rx, ry)
        elif self.mode == "PORTAL":
            if not self.picking_exit:
                self.portal_in_temp, self.picking_exit = (rx, ry), True
            else:
                self.portals.append({'in_x': self.portal_in_temp[0], 'in_y': self.portal_in_temp[1], 'out_x': rx, 'out_y': ry})
                self.picking_exit = False
                self.redraw()

    def on_canvas_drag(self, event):
        rx, ry = self.win_to_real(event.x, event.y)
        if self.panning:
            dx, dy = event.x - self.last_mouse_pos[0], event.y - self.last_mouse_pos[1]
            cw, ch = max(10, self.canvas.winfo_width()), max(10, self.canvas.winfo_height())
            self.pan_x -= (dx / cw) * (self.img_w / self.zoom_scale)
            self.pan_y -= (dy / ch) * (self.img_h / self.zoom_scale)
            self.last_mouse_pos = (event.x, event.y)
        elif self.drawing:
            self.temp_preview_img = self.curr_img.copy()
            cv2.line(self.temp_preview_img, self.start_p_real, (rx, self.start_p_real[1]), (0, 0, 255), 2)
        elif self.picking_exit:
            self.temp_preview_img = self.curr_img.copy()
            cv2.arrowedLine(self.temp_preview_img, self.portal_in_temp, (rx, ry), Config.COLOR_PORTAL_LINE, 2)

    def on_canvas_release(self, event):
        if self.drawing:
            rx, ry = self.win_to_real(event.x, event.y)
            if abs(self.start_p_real[0] - rx) > 3:
                self.platforms.append({'y': self.start_p_real[1], 'x_start': min(self.start_p_real[0], rx), 'x_end': max(self.start_p_real[0], rx)})
                self.redraw()
            self.drawing = False
        self.panning = False

    def on_item_update(self, idx, data): self.redraw()
    def on_platform_delete(self, idx): self.platforms.pop(idx); self.redraw()
    def on_portal_delete(self, idx): self.portals.pop(idx); self.redraw()
    
    def on_mouse_wheel(self, event):
        self.zoom_scale = max(1.0, min(8.0, self.zoom_scale + (0.2 if event.delta > 0 else -0.2)))

    def get_disp_img(self):
        src = self.temp_preview_img if (self.drawing or self.picking_exit) else self.curr_img
        if src is None: return None
        vw, vh = self.img_w / self.zoom_scale, self.img_h / self.zoom_scale
        x1, y1 = int(self.pan_x - vw/2), int(self.pan_y - vh/2)
        tx1, ty1, tx2, ty2 = max(0, x1), max(0, y1), min(self.img_w, int(x1+vw)), min(self.img_h, int(y1+vh))
        cropped = src[ty1:ty2, tx1:tx2]
        cw, ch = max(10, self.canvas.winfo_width()), max(10, self.canvas.winfo_height())
        return cv2.resize(cropped, (cw, ch))

    def run_main_loop(self):
        def update():
            try:
                disp = self.get_disp_img()
                if disp is not None:
                    img_pil = Image.fromarray(cv2.cvtColor(disp, cv2.COLOR_BGR2RGB))
                    self.tk_img = ImageTk.PhotoImage(img_pil)
                    self.canvas.delete("all")
                    self.canvas.create_image(0, 0, anchor="nw", image=self.tk_img)
                    info = f"Mode: {self.mode} | Zoom: x{self.zoom_scale:.1f} | Platforms: {len(self.platforms)}"
                    self.canvas.create_text(15, 25, text=info, fill="yellow", anchor="nw", font=("Arial", 14, "bold"))
                self.root.after(30, update)
            except: pass
        update(); self.root.mainloop()

    def save_data(self):
        path = filedialog.asksaveasfilename(defaultextension=".json", initialfile="map_data.json")
        if path:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump({"platforms": self.platforms, "portals": self.portals}, f, indent=4, ensure_ascii=False)
            messagebox.showinfo("완료", "데이터가 저장되었습니다.")

    def on_right_click(self, event):
        self.panning, self.last_mouse_pos = True, (event.x, event.y)
    
    def undo_last(self):
        """[복구 및 개선] 마지막 작업을 취소합니다."""
        # 1. 포탈 입구만 찍은 상태라면 입력을 취소
        if self.picking_exit:
            self.picking_exit = False
            self.portal_in_temp = (-1, -1)
        # 2. 포탈 데이터가 있다면 마지막 포탈 삭제
        elif self.portals:
            self.portals.pop()
        # 3. 발판 데이터가 있다면 마지막 발판 삭제
        elif self.platforms:
            self.platforms.pop()
            
        self.redraw() # 화면 갱신

if __name__ == "__main__":
    ImprovedMapEditor()