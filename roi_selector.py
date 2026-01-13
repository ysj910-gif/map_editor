import cv2
import numpy as np
import mss
import json
import win32gui
import win32con

# --- 설정 ---
WINDOW_TITLE = "MapleStory"
# --------------

def nothing(x):
    pass

def main():
    print("--- ROI 선택기 (v2.2) ---")
    print(f"'{WINDOW_TITLE}' 창을 찾고 있습니다...")

    hwnd = win32gui.FindWindow(None, WINDOW_TITLE)
    if not hwnd:
        print(f"오류: '{WINDOW_TITLE}' 창을 찾을 수 없습니다. 게임이 실행 중인지 확인하세요.")
        return

    if win32gui.IsIconic(hwnd):
        print(f"오류: '{WINDOW_TITLE}' 창이 최소화되어 있습니다. 창을 활성화한 후 다시 실행해 주세요.")
        return
        
    win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
    win32gui.SetForegroundWindow(hwnd)

    with mss.mss() as sct:
        left, top, right, bot = win32gui.GetWindowRect(hwnd)
        WINDOW_WIDTH = right - left
        WINDOW_HEIGHT = bot - top
        
        if WINDOW_WIDTH <= 0 or WINDOW_HEIGHT <= 0:
            print(f"오류: '{WINDOW_TITLE}' 창의 크기를 가져올 수 없습니다. (너비/높이 0 이하)")
            return

        print(f"창 발견! 위치:({left}, {top}), 크기:({WINDOW_WIDTH}x{WINDOW_HEIGHT})")
        capture_zone = {'top': top, 'left': left, 'width': WINDOW_WIDTH, 'height': WINDOW_HEIGHT}

        # --- 창 생성 ---
        cv2.namedWindow('Trackbars', cv2.WINDOW_NORMAL)
        cv2.resizeWindow('Trackbars', 600, 200)
        cv2.namedWindow('ROI Selector', cv2.WINDOW_NORMAL)
        # ===================== NEW: 컨트롤 패널 창 추가 =====================
        cv2.namedWindow('Controls', cv2.WINDOW_NORMAL)
        control_panel_img = np.zeros((150, 400, 3), dtype=np.uint8) # 제어판 영역 생성
        # =================================================================

        initial_params = {'Left': 10, 'Top': 50, 'Width': 200, 'Height': 150}
        
        cv2.createTrackbar('Left', 'Trackbars', initial_params['Left'], WINDOW_WIDTH, nothing)
        cv2.createTrackbar('Top', 'Trackbars', initial_params['Top'], WINDOW_HEIGHT, nothing)
        cv2.createTrackbar('Width', 'Trackbars', initial_params['Width'], WINDOW_WIDTH, nothing)
        cv2.createTrackbar('Height', 'Trackbars', initial_params['Height'], WINDOW_HEIGHT, nothing)
        
        print("\n--- 조작법 ---")
        print("ROI Selector 또는 Controls 창을 활성화한 상태에서 아래 키를 누르세요.")
        print("1, 2, 3, 4 키: Left, Top, Width, Height 선택")
        print("방향키: 선택된 값 1씩 조절")
        print("숫자 + Enter: 선택된 값 직접 설정")
        print("'s': 저장 | 'q': 종료")

        params = initial_params.copy()
        param_keys = ['Left', 'Top', 'Width', 'Height']
        active_param_idx = 0
        number_input_str = ""
        is_saved = False

        while True:
            game_img = np.array(sct.grab(capture_zone))

            mouse_moved = False
            for p_key in param_keys:
                trackbar_pos = cv2.getTrackbarPos(p_key, 'Trackbars')
                if params[p_key] != trackbar_pos:
                    params[p_key] = trackbar_pos
                    mouse_moved = True
            
            if mouse_moved:
                number_input_str = ""

            key = cv2.waitKeyEx(20)

            if key != -1:
                active_param_key = param_keys[active_param_idx]
                
                if ord('1') <= key <= ord('4'):
                    active_param_idx = key - ord('1')
                    number_input_str = ""
                elif ord('0') <= key <= ord('9'):
                    number_input_str += chr(key)
                elif key == 8: # Backspace
                    number_input_str = number_input_str[:-1]
                elif key == 13: # Enter
                    try:
                        if number_input_str:
                            params[active_param_key] = int(number_input_str)
                    except ValueError:
                        print("잘못된 숫자 형식입니다.")
                    finally:
                        number_input_str = ""
                elif key == 2490368: params[active_param_key] -= 1 # Up
                elif key == 2621440: params[active_param_key] += 1 # Down
                elif key == 2424832: params[active_param_key] -= 1 # Left
                elif key == 2555904: params[active_param_key] += 1 # Right
                elif key == ord('s'):
                    is_saved = True
                    break
                elif key == ord('q'):
                    break

            params['Left'] = max(0, min(params['Left'], WINDOW_WIDTH))
            params['Top'] = max(0, min(params['Top'], WINDOW_HEIGHT))
            params['Width'] = max(1, min(params['Width'], WINDOW_WIDTH - params['Left']))
            params['Height'] = max(1, min(params['Height'], WINDOW_HEIGHT - params['Top']))
            
            for p_key, p_val in params.items():
                cv2.setTrackbarPos(p_key, 'Trackbars', p_val)

            # ===================== NEW: 컨트롤 패널 업데이트 =====================
            control_panel_img.fill(20) # 매 프레임마다 패널을 검은색에 가깝게 초기화
            
            for i, p_key in enumerate(param_keys):
                color = (0, 255, 0) if i == active_param_idx else (255, 255, 255) # 활성 파라미터는 녹색, 나머지는 흰색
                text = f"{p_key}: {params[p_key]}"
                cv2.putText(control_panel_img, text, (10, 30 + i * 25), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
            
            cv2.putText(control_panel_img, "Input:", (10, 130), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
            if number_input_str:
                cv2.putText(control_panel_img, number_input_str, (80, 130), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
                
            cv2.imshow('Controls', control_panel_img)
            # =================================================================

            # ROI 사각형 그리기
            cv2.rectangle(game_img, (params['Left'], params['Top']), (params['Left'] + params['Width'], params['Top'] + params['Height']), (0, 255, 0), 2)
            cv2.imshow('ROI Selector', game_img)

        if is_saved:
            final_roi = {'top': top + params['Top'], 'left': left + params['Left'], 'width': params['Width'], 'height': params['Height']}
            with open('roi_config.json', 'w') as f:
                json.dump(final_roi, f, indent=4)
            print(f"\n좌표 정보 저장 완료: {final_roi}")
            roi_img = np.array(sct.grab(final_roi))
            cv2.imwrite('map_base.png', roi_img)
            print("미니맵 이미지 'map_base.png' 저장 완료.")
        else:
            print("\n저장하지 않고 종료합니다.")

    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()