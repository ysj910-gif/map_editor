import cv2
import json
import numpy as np
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk

from app_config import Config
from map_logic import MapLogic
from ui_widgets import PropertyEditor, PortalEditor, SpawnEditor

class ImprovedMapEditor:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title(Config.TITLE)
        self.root.geometry(Config.WINDOW_SIZE)

        # 상태 및 데이터 변수
        self.mode = "PAN"
        self.platforms = []
        self.portals = [] 
        self.spawns = []  # [신규] 스폰 포인트 리스트
        self.selected_platform_idx = None # [추가] 현재 선택된 발판 인덱스
        self.selected_portal_idx = None   # [추가] 현재 선택된 포탈 인덱스
        self.selected_spawn_idx = None # [신규] 선택된 스폰 인덱스

        # [신규] 시각화 토글 변수 (체크박스용)
        self.show_platforms = tk.BooleanVar(value=True)
        self.show_portals = tk.BooleanVar(value=True)
        self.show_spawns = tk.BooleanVar(value=True)
        self.show_paths = tk.BooleanVar(value=False)

        # 2. [중요] 지형 인식 설정값 변수를 UI 생성 전에 먼저 선언해야 합니다.
        self.thresh_val = tk.IntVar(value=150)
        self.min_len_val = tk.IntVar(value=15)
        self.hsv_lower = [tk.IntVar(value=0), tk.IntVar(value=0), tk.IntVar(value=0)]
        self.hsv_upper = [tk.IntVar(value=180), tk.IntVar(value=255), tk.IntVar(value=255)]
        
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

        # 파일 관리 섹션
        file_frame = tk.LabelFrame(self.sidebar, text="파일 관리")
        file_frame.pack(fill="x", padx=10, pady=5)
        tk.Button(file_frame, text="🖼 이미지 불러오기", command=self.load_new_image).pack(fill="x", padx=5, pady=5)
        tk.Button(file_frame, text="📂 JSON 데이터 불러오기", command=self.load_map_data, bg="#fff9c4").pack(fill="x", padx=5, pady=2) # [신규]

        # 지형 인식 설정 섹션
        detect_frame = tk.LabelFrame(self.sidebar, text="🤖 지형 인식 설정")
        detect_frame.pack(fill="x", padx=10, pady=5)
        
        tk.Label(detect_frame, text="Threshold (밝기 임계값)").pack(anchor="w", padx=5)
        tk.Scale(detect_frame, from_=0, to=255, orient="horizontal", variable=self.thresh_val).pack(fill="x", padx=5)
        
        tk.Label(detect_frame, text="Min Length (최소 길이)").pack(anchor="w", padx=5)
        tk.Scale(detect_frame, from_=0, to=100, orient="horizontal", variable=self.min_len_val).pack(fill="x", padx=5)

        # 2. [신규] 시각화 설정 섹션
        vis_frame = tk.LabelFrame(self.sidebar, text="👁 시각화 설정")
        vis_frame.pack(fill="x", padx=10, pady=5)

        tk.Checkbutton(vis_frame, text="발판 보기", variable=self.show_platforms, command=self.redraw).pack(anchor="w", padx=5)
        tk.Checkbutton(vis_frame, text="포탈 보기", variable=self.show_portals, command=self.redraw).pack(anchor="w", padx=5)
        tk.Checkbutton(vis_frame, text="스폰 보기", variable=self.show_spawns, command=self.redraw).pack(anchor="w", padx=5)
        tk.Checkbutton(vis_frame, text="점프 경로 보기", variable=self.show_paths, command=self.redraw).pack(anchor="w", padx=5)


        # 자동 인식 버튼
        tk.Button(detect_frame, text="⚡ 전체 자동 감지", bg="#e1f5fe", command=self.auto_detect_platforms).pack(fill="x", padx=5, pady=2)
        self.btn_roi_detect = tk.Button(detect_frame, text="🎯 영역 지정 감지 (드래그)", bg="white", command=lambda: self.set_mode("ROI_DETECT"))
        self.btn_roi_detect.pack(fill="x", padx=5, pady=2)

        # 작업 모드 섹션
        mode_frame = tk.LabelFrame(self.sidebar, text="작업 모드")
        mode_frame.pack(fill="x", padx=10, pady=5)
        
        self.btn_draw = tk.Button(mode_frame, text="🛠 발판 그리기", command=lambda: self.set_mode("DRAW"))
        self.btn_draw.pack(fill="x", padx=5, pady=2)
        self.btn_portal = tk.Button(mode_frame, text="🌀 포탈 추가", command=lambda: self.set_mode("PORTAL"))
        self.btn_portal.pack(fill="x", padx=5, pady=2)
        self.btn_spawn = tk.Button(mode_frame, text="👾 스폰 추가", command=lambda: self.set_mode("SPAWN")) # [신규]
        self.btn_spawn.pack(fill="x", padx=5, pady=2)
        self.btn_pan = tk.Button(mode_frame, text="✋ 화면 이동 모드", bg=Config.COLOR_DRAW_ACTIVE, command=lambda: self.set_mode("PAN"))
        self.btn_pan.pack(fill="x", padx=5, pady=2)

        # 편집 도구
        edit_frame = tk.LabelFrame(self.sidebar, text="편집 도구")
        edit_frame.pack(fill="x", padx=10, pady=5)
        tk.Button(edit_frame, text="↩ 되돌리기 (Undo)", command=self.undo_last).pack(fill="x", padx=5, pady=2)
        tk.Button(edit_frame, text="💾 데이터 저장", bg=Config.COLOR_SAVE, font=Config.FONT_BOLD, command=self.save_data).pack(fill="x", padx=5, pady=5)
        
    def auto_detect_platforms(self, roi_rect=None):
        """지정된 영역(roi_rect) 또는 전체 이미지에서 발판 감지"""
        if self.orig_img is None: return
        
        threshold = self.thresh_val.get()
        min_len = self.min_len_val.get()
        
        # 영역 설정 (ROI)
        if roi_rect:
            x1, y1, x2, y2 = roi_rect
            target_img = self.orig_img[y1:y2, x1:x2]
        else:
            target_img = self.orig_img
            x1, y1 = 0, 0

        gray = cv2.cvtColor(target_img, cv2.COLOR_BGR2GRAY)
        _, thresh = cv2.threshold(gray, threshold, 255, cv2.THRESH_BINARY)
        
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (min_len, 1))
        detected = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel, iterations=1)
        contours, _ = cv2.findContours(detected, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        count = 0
        for cnt in contours:
            x, y, w, h = cv2.boundingRect(cnt)
            if w >= min_len and h < 8:
                self.platforms.append({'y': y + y1 + 1, 'x_start': x + x1, 'x_end': x + x1 + w})
                count += 1
        
        self.redraw()
        if not roi_rect: messagebox.showinfo("완료", f"{count}개의 발판을 감지했습니다.")

    def set_mode(self, mode):
        """작업 모드 전환 및 UI 상태 갱신"""
        self.mode = mode
        # 상태 초기화
        self.drawing = False
        self.roi_selecting = False
        self.picking_exit = False
        self.selected_platform_idx = None
        self.selected_portal_idx = None
        
        # 버튼 색상 업데이트
        self.btn_draw.config(bg=Config.COLOR_DRAW_ACTIVE if mode == "DRAW" else Config.COLOR_DRAW_INACTIVE)
        self.btn_portal.config(bg=Config.COLOR_PORTAL_ACTIVE if mode == "PORTAL" else Config.COLOR_PORTAL_INACTIVE)
        self.btn_pan.config(bg=Config.COLOR_DRAW_ACTIVE if mode == "PAN" else Config.COLOR_DRAW_INACTIVE)
        self.btn_roi_detect.config(bg="#bbdefb" if mode == "ROI_DETECT" else "white")

        # [수정]
        self.selected_spawn_idx = None # 초기화 추가

        self.btn_portal.config(bg=Config.COLOR_PORTAL_ACTIVE if mode == "PORTAL" else Config.COLOR_PORTAL_INACTIVE)
        self.btn_spawn.config(bg="#d1c4e9" if mode == "SPAWN" else "white") # [신규] 보라색
        
        self.redraw()

    def _bind_events(self):
        self.canvas.bind("<Button-1>", self.on_canvas_click)
        self.canvas.bind("<B1-Motion>", self.on_canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_canvas_release)
        self.canvas.bind("<MouseWheel>", self.on_mouse_wheel)
        self.canvas.bind("<Button-3>", self.on_right_click)
        # [추가] 키보드 미세조정 이벤트 바인딩
        self.root.bind("<Key>", self.on_key_press)

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
    
    def load_new_image(self):
        """실행 중 새로운 이미지를 불러오고 데이터를 초기화합니다."""
        # 기존 데이터가 있는 경우 확인 메시지
        if self.platforms or self.portals or self.spawns:
            if not messagebox.askyesno("데이터 초기화 확인", 
                                       "이미지를 새로 불러오면 현재 작성된 발판 및 포탈 데이터가 삭제됩니다. 계속하시겠습니까?"):
                return

        path = filedialog.askopenfilename(title="새 미니맵 이미지 선택",
                                          filetypes=[("Image files", "*.png *.jpg *.jpeg *.bmp")])
        if not path: 
            return

        # 이미지 로드 (한글 경로 지원을 위해 np.fromfile 사용)
        try:
            img_array = np.fromfile(path, np.uint8)
            new_img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
            
            if new_img is None:
                raise Exception("이미지 디코딩 실패")
                
            # 데이터 및 뷰 상태 초기화
            self.orig_img = new_img
            self.img_h, self.img_w = self.orig_img.shape[:2]
            self.pan_x, self.pan_y = self.img_w // 2, self.img_h // 2
            self.zoom_scale = 1.0
            self.platforms = []
            self.portals = []
            self.spawns = []
            self.selected_platform_idx = None
            self.selected_portal_idx = None
            
            self.redraw()
            messagebox.showinfo("완료", "새로운 이미지를 성공적으로 불러왔습니다.")
            
        except Exception as e:
            messagebox.showerror("오류", f"이미지를 불러오는 중 오류가 발생했습니다: {e}")

    # [신규 함수]
    def load_map_data(self):
        """[신규] 기존 JSON 파일 불러오기"""
        path = filedialog.askopenfilename(title="맵 데이터(JSON) 불러오기", filetypes=[("JSON files", "*.json")])
        if not path: return
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self.platforms = data.get('platforms', [])
            self.portals = data.get('portals', [])
            self.spawns = data.get('spawns', []) # 스폰 데이터 로드
            self.redraw()
            messagebox.showinfo("완료", f"데이터 로드 완료:\n발판 {len(self.platforms)}개\n포탈 {len(self.portals)}개\n스폰 {len(self.spawns)}개")
        except Exception as e:
            messagebox.showerror("오류", f"데이터 로드 실패: {e}")

    def redraw(self):
        if self.orig_img is None: return
        self.curr_img = self.orig_img.copy()
        
        # 발판 그리기
        if self.show_paths.get() and self.show_platforms.get():
            for i, p in enumerate(self.platforms):
                color = (0, 0, 255) if i == self.selected_platform_idx else (0, 255, 0) # 선택된 발판은 빨간색
                thickness = 3 if i == self.selected_platform_idx else 2
                cv2.line(self.curr_img, (p['x_start'], p['y']), (p['x_end'], p['y']), color, thickness)
            
        # 포탈 그리기
        if self.show_portals.get():
            for i, p in enumerate(self.portals):
                color = (0, 0, 255) if i == self.selected_portal_idx else Config.COLOR_PORTAL_LINE
                cv2.arrowedLine(self.curr_img, (p['in_x'], p['in_y']), (p['out_x'], p['out_y']), color, 2)
                cv2.circle(self.curr_img, (p['in_x'], p['in_y']), 4, (255, 0, 0), -1)

        # [수정] 스폰 포인트 그리기 추가
        if self.show_spawns.get():
            for i, s in enumerate(self.spawns):
                color = (0, 0, 255) if i == self.selected_spawn_idx else (128, 0, 128) # 보라색
                cv2.circle(self.curr_img, (s['x'], s['y']), 6, color, -1)
                cv2.putText(self.curr_img, "SPAWN", (s['x']-20, s['y']-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

        self.temp_preview_img = self.curr_img.copy()

    def win_to_real(self, wx, wy):
        """[해결] 줌 상태에서의 좌표 불일치 문제를 완벽하게 수정"""
        cw, ch = max(10, self.canvas.winfo_width()), max(10, self.canvas.winfo_height())
        
        # 1. 현재 화면에 표시되는 Crop 영역의 정확한 좌표를 계산 (get_disp_img 로직과 일치)
        vw, vh = self.img_w / self.zoom_scale, self.img_h / self.zoom_scale
        x1, y1 = int(self.pan_x - vw/2), int(self.pan_y - vh/2)
        tx1, ty1 = max(0, x1), max(0, y1)
        tx2, ty2 = min(self.img_w, int(x1+vw)), min(self.img_h, int(y1+vh))
        
        # 2. 실제로 크롭되어 캔버스에 꽉 채워진 이미지의 너비/높이
        real_vw = tx2 - tx1
        real_vh = ty2 - ty1
        
        # 3. 캔버스의 클릭 위치 비율을 크롭 영역에 투영
        rx = int(tx1 + (wx / cw) * real_vw)
        ry = int(ty1 + (wy / ch) * real_vh)
        return rx, ry

    def on_canvas_click(self, event):
        rx, ry = self.win_to_real(event.x, event.y)
        if self.mode == "PAN":
            # 포탈 선택 확인
            if self.show_portals.get(): # [추가된 조건]
                p_idx = MapLogic.find_clicked_portal(self.portals, rx, ry)
                if p_idx is not None:
                    self.selected_portal_idx, self.selected_platform_idx = p_idx, None
                    PortalEditor(self.root, p_idx, self.portals[p_idx], self.img_h, self.img_w, 
                                 self.on_item_update, self.on_portal_delete)
                    self.redraw()
                    return
            
            # 발판 선택 확인
            if self.show_platforms.get(): # [추가된 조건]
                idx = MapLogic.find_clicked_platform(self.platforms, rx, ry)
                if idx is not None:
                    self.selected_platform_idx, self.selected_portal_idx = idx, None
                    PropertyEditor(self.root, idx, self.platforms[idx], self.img_h, self.img_w, 
                                   self.on_item_update, self.on_platform_delete)
                    self.redraw()
                    return
            
            # 스폰 선택 확인
            if self.show_spawns.get(): # [추가된 조건]
                s_idx = MapLogic.find_clicked_spawn(self.spawns, rx, ry)
                if s_idx is not None:
                    self.selected_spawn_idx = s_idx
                    self.selected_platform_idx = self.selected_portal_idx = None
                    SpawnEditor(self.root, s_idx, self.spawns[s_idx], self.img_h, self.img_w, self.on_item_update, self.on_spawn_delete)
                    self.redraw()
                    return
            
            # 빈 공간 클릭 시 선택 해제 및 드래그 준비
            self.selected_platform_idx = self.selected_portal_idx = None
            self.panning, self.last_mouse_pos = True, (event.x, event.y)
            self.redraw()
            
        elif self.mode == "DRAW":
            self.drawing, self.start_p_real = True, (rx, ry)
        elif self.mode == "PORTAL":
            if not self.picking_exit:
                self.portal_in_temp, self.picking_exit = (rx, ry), True
            else:
                self.portals.append({'in_x': self.portal_in_temp[0], 'in_y': self.portal_in_temp[1], 'out_x': rx, 'out_y': ry})
                self.picking_exit = False
                self.redraw()
        elif self.mode == "SPAWN": # [신규] 스폰 추가
                self.spawns.append({'x': rx, 'y': ry, 'desc': 'Spawn Point'})
                self.redraw()

    def on_key_press(self, event):
        """[신규] 키보드를 이용한 미세조정 기능 (1픽셀 단위)"""
        if self.selected_platform_idx is None and self.selected_portal_idx is None:
            return

        step = 1
        key = event.keysym
        shift = (event.state & 0x1) # Shift 키 눌림 여부

        if self.selected_platform_idx is not None:
            p = self.platforms[self.selected_platform_idx]
            if key == "Up": p['y'] -= step
            elif key == "Down": p['y'] += step
            elif key == "Left":
                if shift: p['x_end'] -= step # Shift+Left: 끝점 축소
                else: p['x_start'] -= step; p['x_end'] -= step # Left: 전체 이동
            elif key == "Right":
                if shift: p['x_end'] += step # Shift+Right: 끝점 확장
                else: p['x_start'] += step; p['x_end'] += step # Right: 전체 이동
        
        elif self.selected_portal_idx is not None:
            p = self.portals[self.selected_portal_idx]
            if key == "Up": p['in_y'] -= step
            elif key == "Down": p['in_y'] += step
            elif key == "Left": p['in_x'] -= step
            elif key == "Right": p['in_x'] += step

        elif self.selected_spawn_idx is not None: # [신규] 스폰 이동
            s = self.spawns[self.selected_spawn_idx]
            if key == "Up": s['y'] -= step
            elif key == "Down": s['y'] += step
            elif key == "Left": s['x'] -= step
            elif key == "Right": s['x'] += step

        self.redraw()

    def on_item_update(self, idx, data):
        """[수정] 위젯에서 변경된 데이터 원본에 반영 및 실시간 리드로우"""
        # 1. 스폰 데이터인지 확인 ('desc' 키가 있으면 스폰)
        if "desc" in data:
             self.spawns[idx].update(data)
        
        # 2. 발판 데이터인지 확인 ('y' 키가 있으면 발판)
        elif "y" in data: 
            self.platforms[idx].update(data)
            
        # 3. 나머지는 포탈 데이터로 간주
        else: 
            self.portals[idx].update(data)
            
        self.redraw()

    # --- 이하 나머지 코드는 기존과 동일 (생략 가능하나 구조 유지를 위해 포함) ---
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

    def on_platform_delete(self, idx): 
        self.platforms.pop(idx)
        self.selected_platform_idx = None
        self.redraw()

    def on_portal_delete(self, idx): 
        self.portals.pop(idx)
        self.selected_portal_idx = None
        self.redraw()
    
    def on_mouse_wheel(self, event):
        self.zoom_scale = max(1.0, min(10.0, self.zoom_scale + (0.5 if event.delta > 0 else -0.5)))
        self.redraw()

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
                json.dump({"platforms": self.platforms, "portals": self.portals, "spawns": self.spawns}, f, indent=4, ensure_ascii=False)
            messagebox.showinfo("완료", "데이터가 저장되었습니다.")

    def on_right_click(self, event):
        self.panning, self.last_mouse_pos = True, (event.x, event.y)
    
    def undo_last(self):
        if self.picking_exit:
            self.picking_exit = False
            self.portal_in_temp = (-1, -1)
        elif self.portals: self.portals.pop()
        elif self.platforms: self.platforms.pop()
        elif self.spawns: self.spawns.pop()
        self.redraw()

    # main.py 내 ImprovedMapEditor 클래스에 추가할 메서드 예시

def auto_detect(self):
    if self.orig_img is None: return
    
    # 위에서 작성한 감지 로직 적용
    gray = cv2.cvtColor(self.orig_img, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)
    
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 1))
    detected = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel, iterations=2)
    contours, _ = cv2.findContours(detected, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    new_platforms = []
    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)
        if w > 15 and h < 8: # 맵 특성에 따라 수치 조절
            new_platforms.append({'y': y + 2, 'x_start': x, 'x_end': x + w})
    
    self.platforms.extend(new_platforms) # 기존 데이터에 추가
    self.redraw() # 화면 갱신
    messagebox.showinfo("완료", f"{len(new_platforms)}개의 발판을 자동으로 찾았습니다.")


    

if __name__ == "__main__":
    ImprovedMapEditor()