import time
import json
import cv2
import math
import numpy as np
from typing import Optional, Tuple, List

import video_request as req

if __name__ != '__main__':
    print('call this in main.py')
    exit(1)

# 加载轨迹文件
with open('./traces.json', 'r') as f:
    _global_trace = list(json.load(f)['traces'])


def get_viewed_center(ind: int) -> Tuple[float, float]:
    return _global_trace[ind]


VIEWPORT_WIDTH, VIEWPORT_HEIGHT = 1280, 720


def get_related_tiles(pt: Tuple[float, float]) -> []:
    w, h = pt
    w0, h0 = max(0, math.floor(w - VIEWPORT_WIDTH / 2)), \
             max(0, math.floor(h - VIEWPORT_HEIGHT / 2))
    w1, h1 = min(ORIGINAL_WIDTH - 1, math.ceil(w + VIEWPORT_WIDTH / 2)), \
             min(ORIGINAL_HEIGHT - 1, math.ceil(h + VIEWPORT_HEIGHT / 2))
    luw = w0 // (ORIGINAL_WIDTH // TILE_COLS)
    luh = h0 // (ORIGINAL_HEIGHT // TILE_ROWS)
    rbw = w1 // (ORIGINAL_WIDTH // TILE_COLS)
    rbh = h1 // (ORIGINAL_HEIGHT // TILE_ROWS)
    tiles = []
    for h in range(luh, rbh + 1):
        tile_ind = h * TILE_COLS
        for w in range(luw, rbw + 1):
            tiles.append(tile_ind + w)
    assert len(tiles) > 0
    return tiles


def merge_images(bg: np.ndarray, tiles: List[List[np.ndarray]], pt=None) -> np.ndarray:
    """merge @tiles into @bg
    pt is (w, h)"""
    if bg is None:
        bg = np.zeros([ORIGINAL_HEIGHT, ORIGINAL_WIDTH, 3], dtype=np.uint8)
    else:
        bg = cv2.resize(bg, (ORIGINAL_WIDTH, ORIGINAL_HEIGHT))  # ndarray is [rows, cols] 和 resize(W,H)
    for h in range(0, TILE_ROWS):
        for w in range(0, TILE_COLS):
            if tiles[h][w] is None:
                continue
            tile = cv2.resize(tiles[h][w], (TILE_WIDTH, TILE_HEIGHT))
            h_start, w_start = h * TILE_HEIGHT, w * TILE_WIDTH
            bg[h_start:h_start + TILE_HEIGHT, w_start:w_start + TILE_WIDTH] = tile
    if pt is not None:
        w, h = pt
        w0, h0 = max(0, math.floor(w - VIEWPORT_WIDTH / 2)), \
                 max(0, math.floor(h - VIEWPORT_HEIGHT / 2))
        w1, h1 = min(ORIGINAL_WIDTH - 1, math.ceil(w + VIEWPORT_WIDTH / 2)), \
                 min(ORIGINAL_HEIGHT - 1, math.ceil(h + VIEWPORT_HEIGHT / 2))
        # 保存视口内容，为了之后计算 PSPNR
        view_pic = bg[h0:h1+1, w0:w1+1]
        cv2.imwrite(f'./view-images-2/{frame_count}.png', view_pic)
        cv2.circle(bg, (int(pt[0]), int(pt[1])), radius=10, color=(0, 0, 255), thickness=5)
        cv2.rectangle(bg, (w0, h0), (w1, h1), color=(0, 0, 255), thickness=5)
    bg = cv2.resize(bg, (VIEWPORT_WIDTH, VIEWPORT_HEIGHT))
    return bg


# 创建解码器
URL = r'E:/Py_Projects/player/data/Cut_Tokyo_6_4_1000_min/manifest.json'
v_decoder = req.VideoFetchDecoder(URL)
tile_conf = v_decoder.get_tile_config()
print(f'tile config is {tile_conf}')
ORIGINAL_WIDTH = tile_conf['original-width']
ORIGINAL_HEIGHT = tile_conf['original-height']
TILES_NUM = tile_conf['tiles-num']
TILE_COLS = tile_conf['tile-cols']
TILE_ROWS = tile_conf['tile-rows']
TILE_WIDTH = ORIGINAL_WIDTH // TILE_COLS
TILE_HEIGHT = ORIGINAL_HEIGHT // TILE_ROWS


def wait(t0: int, min_delay=10):
    t1 = time.time_ns()
    t_used_ms = int(abs(t1 - t0) / 1e6)
    t_frame_ms = int((1 / v_decoder.FPS) * 1e3)
    print(f'Used {t_used_ms} ms of a frame {t_frame_ms} ms.')
    delay = max(1, t_frame_ms - t_used_ms)
    cv2.waitKey(delay)


v_decoder.start()
frame_count = 0
stall_times_per_second = 0
stall_time_ps_list = []
old_bandwidth_usage = 0.0
bandwidth_ps_list = []
last_t0_ns = 0
while True:
    if frame_count >= 30 * v_decoder.FPS:  # 目前只播放30s
        print('30s video is over!')
        break
    t0 = time.time_ns()
    view = get_viewed_center(frame_count)
    tiles = get_related_tiles(view)
    bg, images, flag = v_decoder.get_images(frame_count, tiles)
    if flag == -2:
        print('Whole Video is over!')
        break
    elif flag == -1:
        # print('Waiting for caches...')
        time.sleep(5 / v_decoder.FPS)
        stall_times_per_second += 1
    elif flag == 0:
        # print('Use tiles with background.')
        bg = merge_images(bg, images, view)
        cv2.imshow('video', bg)
        wait(t0)
        frame_count += 1
    elif flag == 1:
        # print('Use all tiles!')
        bg = merge_images(bg, images, view)
        cv2.imshow('video', bg)
        wait(t0)
        frame_count += 1
    else:
        print('impossible!!!')
        break
    cur_t0_ns = time.time_ns()
    t0_duration = (cur_t0_ns - last_t0_ns) / 1e9
    if t0_duration >= 1.0:  # 1s
        stall_time_ps_list.append(stall_times_per_second)
        # print(f'stall time per second(s): '
        #       f'{stall_time_ps_list[-1]}')
        bandwidth_usage = v_decoder.get_total_download()
        bandwidth_ps_list.append((bandwidth_usage - old_bandwidth_usage) / 1e6)
        # print(f'bandwidth per second(MB/s): '
        #       f'{bandwidth_ps_list[-1]}')
        stall_times_per_second = 0
        old_bandwidth_usage = bandwidth_usage
        last_t0_ns = cur_t0_ns
print(f'Main Thread over! total {frame_count} images')
v_decoder.stop()

# 将统计数据保存
# with open('./demo-bandwidth.txt', 'w') as f:
#     for bw in bandwidth_ps_list:
#         f.write(f'{bw}\n')
#     pass
# with open('./demo-stall.txt', 'w') as f:
#     for st in stall_time_ps_list:
#         f.write(f'{st}\n')
#     pass
