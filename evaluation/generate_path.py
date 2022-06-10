import json
import random
import numpy as np
import cv2


if __name__ != '__main__':
    print('call this in main!')
    exit(1)

WIDTH = 7680
HEIGHT = 3840

ALL_FRAMES = 30 * 30

# 每一帧生成一个点，保存到 json 文件里
# 1.选择一个角落中的生成一个点作为起点
# 2.在另外三个个角落生成三个点：
#     3.随机选择一个点做终点，随机选择一个移动速度(pixel/frame)
#     4.从起点向终点移动，然后将终点赋予起点
#     5.重复3.4.知道三个点都遍历，则转到2.


def generate_corner(w: int, w_max: int, h: int, h_max: int) -> (int, int):
    """return (w_coord, h_coord)
    where w <= w_coord < w_max, h <= h_coord < h_max"""
    assert w < w_max and h < h_max
    w_coord = random.randrange(w, w_max)
    h_coord = random.randrange(h, h_max)
    return w_coord, h_coord


def get_area(area_ind: int) -> (int, int, int, int):
    """return (w, w_max, h, h_max)"""
    assert 0 <= area_ind < 4
    if area_ind == 0:
        w, w_max = 0, WIDTH // 2
        h, h_max = 0, HEIGHT // 2
    elif area_ind == 1:
        w, w_max = WIDTH // 2, WIDTH
        h, h_max = 0, HEIGHT // 2
    elif area_ind == 2:
        w, w_max = 0, WIDTH // 2
        h, h_max = HEIGHT // 2, HEIGHT
    elif area_ind == 3:
        w, w_max = WIDTH // 2, WIDTH
        h, h_max = HEIGHT // 2, HEIGHT
    else:
        assert 0
    return w, w_max, h, h_max


def generate_trace() -> []:
    global_traces = []
    start_qu = []
    end_qu = [0, 1, 2, 3]
    random.shuffle(end_qu)
    start_qu.append(end_qu.pop(0))  # 起点和终点准备好
    (start_w, start_h) = generate_corner(*get_area(start_qu[0]))
    while True:
        if len(start_qu) >= 4 or len(end_qu) <= 0:  # 刷新轨迹
            random.shuffle(start_qu)
            for i in range(3):
                end_qu.append(start_qu.pop(0))
            pass
        end = end_qu[0]  # 计算目标位置
        (target_w, target_h) = generate_corner(*get_area(end))
        frames_num = random.randint(10, 50)
        for frame_ind in range(1, frames_num + 1):  # 生成 start_ -> end_ 的一条路径
            r = frame_ind / frames_num
            w = start_w + r * (target_w - start_w)
            h = start_h + r * (target_h - start_h)
            global_traces.append([w, h])
            pass
        start_w, start_h = target_w, target_h  # 更新起点
        start_qu.append(end_qu.pop(0))
        if len(global_traces) >= ALL_FRAMES:
            print('generated global traces!')
            with open('./traces.json', 'w') as f:
                js_obj = {'traces': global_traces}
                json.dump(js_obj, f)
            break
    return global_traces


def draw_trace(trace_path: str):
    mat = np.random.randint(200, 201, size=(HEIGHT, WIDTH, 3), dtype=np.uint8)
    trace_0 = []
    with open('./traces.json', 'r') as f:
        trace_0 = list(json.load(f)['traces'])
    cv2.imshow('trace', mat)
    for wh in trace_0:
        w, h = int(wh[0]), int(wh[1])
        cv2.circle(mat, (w, h), radius=5, color=(0, 0, 255))
        cv2.imshow('trace', mat)
        cv2.waitKey(100)
    cv2.destroyAllWindows()
    pass


generate_trace()
# draw_trace('./traces.json')

