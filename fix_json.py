import json
import os
import tkinter as tk
from tkinter import filedialog, messagebox

def batch_fix_map_ids():
    # 1. GUI 창 설정 (화면에는 띄우지 않음)
    root = tk.Tk()
    root.withdraw() 
    root.attributes("-topmost", True) # 창을 최상단으로

    # 2. 여러 파일 선택 창 열기
    files = filedialog.askopenfilenames(
        title="수정할 맵 데이터(JSON) 파일들을 선택하세요",
        filetypes=[("JSON files", "*.json")],
        initialdir=os.getcwd()
    )

    if not files:
        print("선택된 파일이 없습니다.")
        return

    success_count = 0
    error_count = 0

    # 3. 선택한 각 파일에 대해 처리
    for file_path in files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # 발판(platforms) 데이터가 있는지 확인
            if 'platforms' in data:
                platforms = data['platforms']
                modified = False
                
                for i, platform in enumerate(platforms):
                    # id가 없거나 데이터 구조를 보정해야 할 때
                    if 'id' not in platform:
                        platform['id'] = i
                        modified = True
                
                if modified:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        json.dump(data, f, indent=4, ensure_ascii=False)
                    success_count += 1
                else:
                    # 이미 id가 다 있는 경우
                    success_count += 1 
            else:
                print(f"스키마 오류: {os.path.basename(file_path)} 파일에 'platforms' 키가 없습니다.")
                error_count += 1

        except Exception as e:
            print(f"파일 처리 중 에러 발생 ({os.path.basename(file_path)}): {e}")
            error_count += 1

    # 4. 결과 보고
    result_msg = f"총 {len(files)}개의 파일 중:\n- 성공: {success_count}개\n- 실패: {error_count}개"
    messagebox.showinfo("처리 완료", result_msg)
    root.destroy()

if __name__ == "__main__":
    batch_fix_map_ids()