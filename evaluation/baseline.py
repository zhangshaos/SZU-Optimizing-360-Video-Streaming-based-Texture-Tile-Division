import time
import json
import cv2
import math
import numpy as np
from typing import Optional, Tuple, List
import threading

import decoders


class BSVideoFetchDecoder:
    def __init__(self, manifest: str):
        with open(manifest) as f:
            conf = json.load(f)
            try:
                self.ORIGINAL_WIDTH = int(conf['original-width'])
                self.ORIGINAL_HEIGHT = int(conf['original-height'])
                fg: str = str(conf['layers'][0])
                bg: str = str(conf['layers'][1])
                self.TILE_ROWS = int(conf[fg]['tile-rows'])
                self.TILE_COLS = int(conf[fg]['tile-cols'])
                self.TILES_NUM = int(conf[fg]['tile-num'])

                # 设置 ABR 算法：选择 chunk level
                def chunk_level_func_test(tile_id: int, chunk_ind: int) -> str:
                    # 选择最高质量
                    complexity = 100.0
                    while complexity >= 100.0:
                        complexity -= 1.0
                    levels: list = conf[fg]['levels']
                    span: float = 100.0 / len(levels)
                    return levels[int(complexity // span)]

                self.FPS = int(conf['fps'])
                self.BG_CHUNK_NUM = int(conf[bg]['chunk-num'])
                self.BG_CHUNK_TIME = int(conf[bg]['chunk-time'])
                self.ALL_FRAME_NUM = self.BG_CHUNK_TIME * self.FPS * self.BG_CHUNK_NUM
                # self.BG_START_CHUNK_URL = str(conf[bg]['start-chunk-url'])
                # self.BG_MAX_CACHE_IMAGES = int(self.FPS * self.BG_CHUNK_TIME)
                # self.bg_decoder = decoders.WholeChunkDecoder(self.FPS,
                #                                              self.BG_CHUNK_NUM,
                #                                              self.BG_CHUNK_TIME,
                #                                              self.BG_START_CHUNK_URL,
                #                                              self.BG_MAX_CACHE_IMAGES)
                # self.bg_decoder_thread = threading.Thread(target=self.bg_decoder.start)

                self.FR_CHUNK_NUM = int(conf[fg]['chunk-num'])
                self.FR_CHUNK_TIME = int(conf[fg]['chunk-time'])
                self.FR_START_TILE_URL = str(conf[fg]['start-tile-url'])
                self.FR_MAX_CACHE_IMAGES = int(self.FPS * self.FR_CHUNK_TIME)
                self.fr_decoders = [decoders.TileChunkDecoder(i,
                                                              self.FPS,
                                                              self.FR_CHUNK_NUM,
                                                              self.FR_CHUNK_TIME,
                                                              self.FR_START_TILE_URL,
                                                              self.FR_MAX_CACHE_IMAGES,
                                                              chunk_level_func=chunk_level_func_test)
                                    for i in range(self.TILES_NUM)]
                self.fr_decoders_threads = [threading.Thread(target=self.fr_decoders[i].start)
                                            for i in range(self.TILES_NUM)]

                self.last_frame_ind = -1
            except KeyError as e:
                print(f'manifest file key error: {e}')
                exit(1)
            except IndexError as e:
                print(f'load json index error: {e}')
                exit(1)
            finally:
                pass
        pass

    def get_tile_config(self):
        """给渲染端提供基本的分片配置"""
        return {
            'original-width' : self.ORIGINAL_WIDTH,
            'original-height': self.ORIGINAL_HEIGHT,
            'tiles-num'      : self.TILES_NUM,
            'tile-cols'      : self.TILE_COLS,
            'tile-rows'      : self.TILE_ROWS,
        }

    def is_finished(self, frame_ind: int):
        return frame_ind >= self.ALL_FRAME_NUM

    def get_images(self, frame_ind: int, tile_inds: List[int]) -> (np.ndarray, List[List[np.ndarray]], int):
        """从图片缓冲中得到图片（纹理）
        @return tuple(images(0 or 1+分片数), flag)
        - flag == -2: video is over! (images is 0 only in this case)
        - flag == -1: fr frames are not full, and bg frame is absent, stalling
        - flag == 0:  fr frames are not full, but bg frame is okay
        - flag == 1:  fr frames are full
        """
        if self.is_finished(frame_ind):
            return None, None, -2
        tile_images = []
        images = []
        # bg = self.bg_decoder.get_image(frame_ind)
        bg = None
        count = 0
        for ind in range(self.TILES_NUM):
            decoder = self.fr_decoders[ind]
            if ind in tile_inds and decoder.try_get_image(frame_ind):
                count += 1
        fr_full = count >= len(tile_inds)
        bg_okay = bg is not None
        for ind in range(self.TILES_NUM):
            decoder = self.fr_decoders[ind]
            if ind in tile_inds:
                decoder.sync(frame_ind)
                fr = decoder.get_image(frame_ind) if fr_full else None
                images.append(fr)
            else:
                decoder.sync(frame_ind, False)
                images.append(None)
            if (ind + 1) % self.TILE_COLS == 0:
                tile_images.append(images)
                images = []
        self.last_frame_ind = frame_ind
        if fr_full:
            ans = 1
        elif bg_okay:
            ans = 0
        else:
            ans = -1
        return bg, tile_images, ans

    def start(self):
        """启动新线程，进行解码"""
        # self.bg_decoder_thread.start()
        for t in self.fr_decoders_threads:
            t.start()
        pass

    def stop(self):
        """请求关闭解码线程"""
        # self.bg_decoder.terminate()
        for t in self.fr_decoders:
            t.terminate()
        pass

    def get_total_download(self):
        """获取当前对象总视频数据下载量（单位字节）"""
        # total_bytes = self.bg_decoder.cap.total_download_bytes()
        total_bytes = 0
        for de in self.fr_decoders:
            total_bytes += de.cap.total_download_bytes()
        return total_bytes


if __name__ != '__main__':
    print('call this in main.py')
    exit(1)

# 加载轨迹文件
with open('./traces.json', 'r') as f:
    _global_trace = list(json.load(f)['traces'])


def get_viewed_center(ind: int) -> Optional[Tuple[float, float]]:
    return _global_trace[ind]


VIEWPORT_WIDTH, VIEWPORT_HEIGHT = 1280, 720
VIEWPORT_WIDTH_, VIEWPORT_HEIGHT_ = 2 * VIEWPORT_WIDTH, 2 * VIEWPORT_HEIGHT


def get_related_tiles(pt: Tuple[float, float]) -> []:
    w, h = pt
    w0, h0 = max(0, math.floor(w - VIEWPORT_WIDTH_ / 2)), \
             max(0, math.floor(h - VIEWPORT_HEIGHT_ / 2))
    w1, h1 = min(ORIGINAL_WIDTH - 1, math.ceil(w + VIEWPORT_WIDTH_ / 2)), \
             min(ORIGINAL_HEIGHT - 1, math.ceil(h + VIEWPORT_HEIGHT_ / 2))
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
        cv2.imwrite(f'./baseline-images/{frame_count}.png', view_pic)
        cv2.circle(bg, (int(pt[0]), int(pt[1])), radius=10, color=(0, 0, 255), thickness=5)
        cv2.rectangle(bg, (w0, h0), (w1, h1), color=(0, 0, 255), thickness=5)
    bg = cv2.resize(bg, (VIEWPORT_WIDTH, VIEWPORT_HEIGHT))
    return bg


# 创建解码器
URL = r'E:/Py_Projects/player/data/Cut_Tokyo_6_4_1000_min/manifest.json'
v_decoder = BSVideoFetchDecoder(URL)
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
    elif flag == -1 or flag == 0:
        # print('Waiting for caches...')
        time.sleep(5 / v_decoder.FPS)
        stall_times_per_second += 1
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
# with open('./baseline-bandwidth.txt', 'w') as f:
#     for bw in bandwidth_ps_list:
#         f.write(f'{bw}\n')
#     pass
# with open('./baseline-stall.txt', 'w') as f:
#     for st in stall_time_ps_list:
#         f.write(f'{st}\n')
#     pass
