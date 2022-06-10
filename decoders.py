import os
import queue
import requests as req
import tempfile as tmp
import cv2
import numpy as np
import threading
import time
from typing import Optional, Callable


# PASS
# 通过 test/whole_chunk_decoder.py 测试
# 通过 test/videocap_m4s.py 测试
# 通过 evaluattion/demo.py 测试
class VideoCapture:
    """cv2.VideoCapture wrapper"""

    def __init__(self):
        self.cur_url = ''
        self._total_download_bytes = 0.
        self.cv2_cap = cv2.VideoCapture()
        self.tmp_file = None
        pass

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()

    def open(self, url: str) -> bool:
        """此方法会阻塞，直到视频文件被下载完毕\n
           返回视频是否打开完毕"""

        # 先检测是否是本地文件
        def check_local_url(path: str) -> bool:
            return os.path.exists(path)

        if check_local_url(url):  # 处理本地视频文件
            self.tmp_file = open(url)
            self.cur_url = url
        elif self.cur_url != url or self.tmp_file.closed:  # 处理网络视频文件
            # 当改变了视频文件 URL，或者已经下载的视频缓存文件已经关闭（删除）
            # 则重新下载视频文件
            r = req.get(url=url)
            buf = r.content
            self.tmp_file = tmp.NamedTemporaryFile()
            self.tmp_file.write(buf)
            self.tmp_file.flush()
            self._total_download_bytes += len(buf)
            self.cur_url = url

        if not self.cv2_cap.open(self.tmp_file.name):
            return False
        return True

    def isOpened(self) -> bool:
        return self.cv2_cap.isOpened()

    def release(self):
        self.cv2_cap.release()
        if self.tmp_file is not None:
            self.tmp_file.close()

    def read(self) -> (bool, np.ndarray):
        return self.cv2_cap.read()

    def total_download_bytes(self) -> float:
        return self._total_download_bytes


# PASS
# 通过测试 test/whole_chunk_decoder.py
class WholeChunkDecoder:
    """这个类只有 VideoDecoder 使用，不要直接使用它！
    除非你知道自己在做什么"""

    def __init__(self, fps: int, chunk_num: int, chunk_time: int,
                 start_chunk_url: str, cache_size: int):
        self.FPS = fps  # 大写变量名表示常量！
        self.CHUNK_NUM = chunk_num
        self.CHUNK_TIME = chunk_time
        self.START_CHUNK_URL = start_chunk_url

        self.ALL_FRAME_NUM = self.CHUNK_TIME * self.FPS * self.CHUNK_NUM

        # 帧缓存
        self.CACHE_SIZE = cache_size
        self.cache = queue.Queue(self.CACHE_SIZE)
        self.first_frame_ind = 0  # 指向将要被读取的帧
        self.last_frame_ind = -1  # 指向加入缓存中的帧
        # last_frame_ind 不用加锁，因为只有 start 写，get_image 读
        # first_frame_ind 需要加锁，出现竞争
        self.lock_frame_ind = threading.Lock()

        # 帧同步
        self.real_time_frame_ind = -1

        self.terminate_flag = False

        self.cap: VideoCapture = None
        pass

    def _frame_ind_to_chunk_ind(self, frame_ind: int) -> int:
        return frame_ind // (self.FPS * self.CHUNK_TIME)
        pass

    def _check_skip_chunk(self, current_chunk_ind: int) -> (int, bool):
        request_chunk_ind = \
            self._frame_ind_to_chunk_ind(self.real_time_frame_ind)
        if current_chunk_ind < request_chunk_ind:  # 发生跳chunk的现象！（需要立即处理）
            # self.cap.release()
            # 清理缓存！！！
            with self.lock_frame_ind:
                self.cache = queue.Queue(self.CACHE_SIZE)
                self.first_frame_ind = request_chunk_ind * self.FPS * self.CHUNK_TIME
                self.last_frame_ind = self.first_frame_ind - 1
            return request_chunk_ind, True  # 结束当前chunk的解码，清理cache资源，修改ind指针
        return request_chunk_ind, False

    def _get_target_video_url(self, chunk_ind: int) -> str:
        return self.START_CHUNK_URL.replace('{chunk-number}', str(chunk_ind + 1))
        pass

    def _discard_old_frames(self) -> bool:
        discarded = False
        with self.lock_frame_ind:
            rt_frame_ind = self.real_time_frame_ind
            last_frame_ind = self.last_frame_ind
            first_frame_ind = self.first_frame_ind
            for ind in range(first_frame_ind, min(last_frame_ind, rt_frame_ind)):
                self.cache.get_nowait()
                self.first_frame_ind += 1
                discarded = True
        return discarded

    def start(self):
        self.cap = VideoCapture()
        chunk_ind = 0
        while chunk_ind < self.CHUNK_NUM:
            if self.terminate_flag:  # 结束线程
                break
            url = self._get_target_video_url(chunk_ind)  # ABR
            if not self.cap.open(url):
                print(f'cv2.VideoCapture can\'t open {url}')
            retry_times = 0
            while not self.cap.isOpened():  # 错误处理
                time.sleep(5 / self.FPS)
                if self.cap.open(url):
                    print(f'Retry successfully!')
                    break
                else:
                    retry_times += 1
                    print(f'Retry times {retry_times}...')
                if retry_times >= 3:
                    pass  # TODO：一直没有打开，怎么办？
            while True:  # 解码视频
                while self.cache.full():  # 缓存已满，清理无效缓存
                    if not self._discard_old_frames():
                        time.sleep(5 / self.FPS)
                # 重新计算当前 chunk_ind，判断是否跳帧
                rt_chunk_ind, skipped = self._check_skip_chunk(chunk_ind)
                if skipped:
                    self.cap.release()
                    break
                contuned, img = self.cap.read()
                if not contuned:
                    self.cap.release()
                    break  # 播放完毕，播放下一个chunk
                self.cache.put_nowait(img)
                self.last_frame_ind += 1
            if chunk_ind < rt_chunk_ind:
                chunk_ind = rt_chunk_ind
            else:
                chunk_ind += 1
        self.cap.release()
        print('BG Decoder Thread over!')
        pass

    def get_image(self, frame_ind: int) -> Optional[np.ndarray]:
        assert frame_ind >= self.first_frame_ind
        self.real_time_frame_ind = frame_ind
        frame = None
        with self.lock_frame_ind:
            if self.first_frame_ind <= frame_ind <= self.last_frame_ind:
                for ind in range(self.first_frame_ind, frame_ind):
                    self.cache.get_nowait()
                    self.first_frame_ind += 1
                frame: np.ndarray = self.cache.get_nowait()
                self.first_frame_ind += 1
                pass  # 直接返回对应帧即可，前面的帧都舍弃
            else:  # > self.last_frame_ind
                pass  # 失败
        return frame
        pass

    def is_finished(self, frame_ind: int):
        return frame_ind >= self.ALL_FRAME_NUM
        pass

    def terminate(self):
        self.terminate_flag = True
        pass

    def try_get_image(self, frame_ind: int) -> bool:
        assert frame_ind >= self.first_frame_ind
        with self.lock_frame_ind:
            if self.first_frame_ind <= frame_ind <= self.last_frame_ind:
                return True
        return False
        pass


# PASS
# 通过测试 /test/whole_chunk_decoder.py
class TileChunkDecoder:
    """这个类只有 VideoDecoder 使用，不要直接使用它！
    除非你知道自己在干什么！"""

    def __init__(self, tile_id: int, fps: int, chunk_num: int, chunk_time: int,
                 start_chunk_url: str, cache_size: int, chunk_level_func: Callable):
        self.ID = tile_id
        self.FPS = fps  # 大写变量名表示常量！
        self.CHUNK_NUM = chunk_num
        self.CHUNK_TIME = chunk_time
        self.START_CHUNK_URL = start_chunk_url
        self.CHUNK_LEVEL_FUNC = chunk_level_func

        self.ALL_FRAME_NUM = self.CHUNK_TIME * self.FPS * self.CHUNK_NUM

        # 帧缓存
        self.CACHE_SIZE = cache_size
        self.cache = queue.Queue(self.CACHE_SIZE)
        self.first_frame_ind = 0  # 指向将要被读取的帧
        self.last_frame_ind = -1  # 指向加入缓存中的帧
        # last_frame_ind 不用加锁，因为只有 start 写，get_image 读
        # first_frame_ind 需要加锁，出现竞争
        self.lock_frame_ind = threading.Lock()

        # 控制
        self.running_state = False
        self.cv_sync = threading.Condition()

        # 帧同步
        # TODO: 直接在 cache 中做帧标号，可以消灭当前帧同步的 bug
        self.real_time_frame_ind = -1  # 渲染端实时的帧索引（使用这个丢掉过时的帧）
        self.recent_request_frame_ind = -3  # （使用这个控制是否请求下一个chunk）

        self.terminate_flag = False

        self.cap: VideoCapture = None
        pass

    def _frame_ind_to_chunk_ind(self, frame_ind: int) -> int:
        return frame_ind // (self.FPS * self.CHUNK_TIME)
        pass

    def _check_skip_chunk(self, current_chunk_ind: int) -> (int, bool):
        rt_chunk_ind = self._frame_ind_to_chunk_ind(self.real_time_frame_ind)
        if current_chunk_ind < rt_chunk_ind:  # 发生跳chunk的现象！（需要立即处理）
            # self.cap.release()
            # 清理缓存！！！
            with self.lock_frame_ind:
                self.cache = queue.Queue(self.CACHE_SIZE)
                self.first_frame_ind = rt_chunk_ind * self.FPS * self.CHUNK_TIME
                self.last_frame_ind = self.first_frame_ind - 1
            return rt_chunk_ind, True  # 结束当前chunk的解码，清理cache资源，修改ind指针
        return rt_chunk_ind, False

    def _discard_old_frames(self) -> bool:
        discarded = False
        with self.lock_frame_ind:
            rt_frame_ind = self.real_time_frame_ind
            last_frame_ind = self.last_frame_ind
            first_frame_ind = self.first_frame_ind
            for ind in range(first_frame_ind, min(last_frame_ind, rt_frame_ind)):
                self.cache.get_nowait()
                self.first_frame_ind += 1
                discarded = True
        return discarded

    def _get_target_video_url(self, chunk_ind: int) -> str:
        # ABR 算法选择 chunk 的质量！
        level: str = self.CHUNK_LEVEL_FUNC(self.ID, chunk_ind)
        return self.START_CHUNK_URL.replace('{chunk-number}', str(chunk_ind + 1)) \
            .replace('{tile-number}', str(self.ID)) \
            .replace('{level}', level)
        pass

    def sync(self, frame_ind: int, wake_up=True):
        """渲染端无论用不用这个流，都需要调用这个，以同步帧"""
        self.real_time_frame_ind = frame_ind
        if wake_up:  # 由调用者通知该对象开始运行
            with self.cv_sync:
                if not self.running_state:
                    self.cv_sync.notify()
        pass

    def start(self):
        self.cap = VideoCapture()
        chunk_ind = 0
        while chunk_ind < self.CHUNK_NUM:
            if self.real_time_frame_ind - self.recent_request_frame_ind > 1:
                with self.cv_sync:  # 摸鱼，每次其他线程提醒，才会主动干活
                    self.running_state = False
                    if self.terminate_flag:  # 结束线程
                        break
                    self.cv_sync.wait()
                    self.running_state = True
                    # 重新计算当前 chunk_ind，判断是否跳帧
                    chunk_ind, skipped = self._check_skip_chunk(chunk_ind)
            if self.terminate_flag:  # 结束线程
                break
            # print(f'requst chunk {chunk_ind}')
            url = self._get_target_video_url(chunk_ind)  # ABR
            if not self.cap.open(url):
                print(f'cv2.VideoCapture can\'t open {url}')
            retry_times = 0
            while not self.cap.isOpened():  # 错误处理
                time.sleep(5 / self.FPS)
                if self.cap.open(url):
                    print(f'Retry successfully!')
                    break
                else:
                    retry_times += 1
                    print(f'Retry times {retry_times}...')
                if retry_times >= 3:
                    pass  # TODO：一直没有打开，怎么办？
            while True:  # 解码视频
                while self.cache.full():  # 缓存已满，清理无效缓存
                    if not self._discard_old_frames():
                        time.sleep(5 / self.FPS)
                # 重新计算当前 chunk_ind，判断是否跳帧
                rt_chunk_ind, skipped = self._check_skip_chunk(chunk_ind)
                if skipped:
                    self.cap.release()
                    break
                contuned, img = self.cap.read()
                if not contuned:
                    self.cap.release()
                    break  # 播放完毕，播放下一个chunk
                self.cache.put_nowait(img)
                self.last_frame_ind += 1
            if chunk_ind < rt_chunk_ind:
                chunk_ind = rt_chunk_ind
            else:
                chunk_ind += 1
        self.cap.release()
        print('Tile Decoder Thread over!')

    def get_image(self, frame_ind: int) -> Optional[np.ndarray]:
        assert frame_ind >= self.first_frame_ind
        frame = None
        with self.lock_frame_ind:
            if self.first_frame_ind <= frame_ind <= self.last_frame_ind:
                for ind in range(self.first_frame_ind, frame_ind):
                    self.cache.get_nowait()
                    self.first_frame_ind += 1
                frame: np.ndarray = self.cache.get_nowait()
                self.first_frame_ind += 1
                pass  # 直接返回对应帧即可，前面的帧都舍弃
            else:  # > self.last_frame_ind
                pass  # 失败
        self.recent_request_frame_ind = frame_ind
        return frame
        pass

    def is_finished(self, frame_ind: int):
        return frame_ind >= self.ALL_FRAME_NUM
        pass

    def terminate(self):
        self.terminate_flag = True
        with self.cv_sync:
            if not self.running_state:
                self.cv_sync.notify()
        pass

    def try_get_image(self, frame_ind: int) -> bool:
        assert frame_ind >= self.first_frame_ind
        with self.lock_frame_ind:
            if self.first_frame_ind <= frame_ind <= self.last_frame_ind:
                return True
        return False
        # return self.first_frame_ind <= frame_ind <= self.last_frame_ind
        pass
