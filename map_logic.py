import math

class MapLogic:
    @staticmethod
    def check_jump(p1, p2):
        """두 발판 사이의 점프 가능 여부 계산"""
        overlap = not (p1['x_end'] < p2['x_start'] or p1['x_start'] > p2['x_end'])
        dy = p1['y'] - p2['y']
        dx = min(abs(p1['x_start'] - p2['x_end']), abs(p1['x_end'] - p2['x_start']))
        return (overlap and 10 < dy < 55) or (not overlap and dx < 70 and abs(dy) < 30)

    @staticmethod
    def find_clicked_platform(platforms, rx, ry, tolerance=6):
        """클릭한 위치의 발판 인덱스 반환"""
        for i, p in enumerate(platforms):
            if abs(ry - p['y']) < tolerance and p['x_start'] <= rx <= p['x_end']:
                return i
        return None
    
    @staticmethod # [수정] 정적 메서드 데코레이터 추가
    def find_clicked_portal(portals, rx, ry, tolerance=10):
        """클릭한 위치 근처의 포탈 인덱스 반환"""
        for i, p in enumerate(portals):
            if math.dist((rx, ry), (p['in_x'], p['in_y'])) < tolerance:
                return i
        return None