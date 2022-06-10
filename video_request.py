"""
请求视频资源，并解码为图片

- 调用者（渲染图像）

"""
import math
import threading
import json
import numpy as np
from typing import Optional, List

import decoders


# PASS
# 通过测试 /test/total_decoder.py
class VideoFetchDecoder:
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
                    # 临时的块质量选择算法（线性算法）
                    complexity: float = conf[fg]['textures']['complexity'][chunk_ind][tile_id]
                    while complexity >= 100.0:
                        complexity -= 1.0
                    levels: list = conf[fg]['levels']
                    span: float = 100.0 / len(levels)
                    return levels[int(complexity // span)]

                def chunk_level_func_log(tile_id: int, chunk_ind: int) -> str:
                    # log 形状的块质量选择算法:
                    # y = log_2(ax + 1), where a = (2^level - 1)/100
                    complexity: float = conf[fg]['textures']['complexity'][chunk_ind][tile_id]
                    while complexity >= 100.0:  # 0.0 <= complexity < 100.0
                        complexity -= 1.0
                    levels: list = conf[fg]['levels']
                    a = (2**len(levels) - 1) / 100
                    lv = int(math.log2(a * complexity + 1))
                    # print(f'lv is {lv}')
                    return levels[lv]

                self.FPS = int(conf['fps'])
                self.BG_CHUNK_NUM = int(conf[bg]['chunk-num'])
                self.BG_CHUNK_TIME = int(conf[bg]['chunk-time'])
                self.BG_START_CHUNK_URL = str(conf[bg]['start-chunk-url'])
                self.BG_MAX_CACHE_IMAGES = int(self.FPS * self.BG_CHUNK_TIME)
                self.bg_decoder = decoders.WholeChunkDecoder(self.FPS,
                                                             self.BG_CHUNK_NUM,
                                                             self.BG_CHUNK_TIME,
                                                             self.BG_START_CHUNK_URL,
                                                             self.BG_MAX_CACHE_IMAGES)
                self.bg_decoder_thread = threading.Thread(target=self.bg_decoder.start)

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
                                                              chunk_level_func=chunk_level_func_log)
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
        return self.bg_decoder.is_finished(frame_ind)

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
        bg = self.bg_decoder.get_image(frame_ind)
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
        self.bg_decoder_thread.start()
        for t in self.fr_decoders_threads:
            t.start()
        pass

    def stop(self):
        """请求关闭解码线程"""
        self.bg_decoder.terminate()
        for t in self.fr_decoders:
            t.terminate()
        pass

    def get_total_download(self):
        """获取当前对象总视频数据下载量（单位字节）"""
        total_bytes = self.bg_decoder.cap.total_download_bytes()
        for de in self.fr_decoders:
            total_bytes += de.cap.total_download_bytes()
        return total_bytes

