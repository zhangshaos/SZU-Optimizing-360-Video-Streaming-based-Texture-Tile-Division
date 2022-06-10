import os
import cv2
import numpy as np
from typing import List
import matplotlib.pyplot as plt
from math import log10, sqrt


def get_stall_linespace(fs: str, fps: float) -> List[float]:
    stall_times_list = []
    with open(fs) as f:
        for line in f:
            stall_times = int(line)
            stall_times_list.append(stall_times)
    for i in range(0, len(stall_times_list)):
        stall_times_list[i] /= fps
    return stall_times_list
    # 返回结果表示，每 1s 中，阻塞的平均时长
    # 两幅图画在一起，双条柱形图
    pass


def draw_stall():
    stalls_1 = get_stall_linespace(r'E:\Py_Projects\player\evaluation\demo-stall.txt', 30.)
    stalls_2 = get_stall_linespace(r'E:\Py_Projects\player\evaluation\baseline-stall.txt', 30.)
    plt.plot(
        stalls_1, label='Our work', color='orange', linestyle='solid'
    )
    plt.plot(
        stalls_2, label='Baseline', color='gray', linestyle='dashed'
    )
    # plt.title('Bandwidth Comparison')
    plt.xlabel('Time (second)')
    plt.ylabel('Stalling time (second)')
    plt.legend()
    plt.show()

# draw_stall()


def get_bandwidth_linesapce(fs: str):
    bandwidthes = []
    with open(fs) as f:
        for line in f:
            bw = float(line)
            bandwidthes.append(bw)
    return bandwidthes
    # 将两幅图画在一起，做折线图
    pass


def draw_bandwidths():
    demo_bws = get_bandwidth_linesapce(r'E:\Py_Projects\player\evaluation\demo-bandwidth.txt')
    baseline_bws = get_bandwidth_linesapce(r'E:\Py_Projects\player\evaluation\baseline-bandwidth.txt')
    plt.plot(
        demo_bws, label='Our work', color='orange', linestyle='solid'
    )
    plt.plot(
        baseline_bws, label='Baseline', color='gray', linestyle='dashed'
    )
    # plt.title('Bandwidth Comparison')
    plt.xlabel('Time (second)')
    plt.ylabel('Bandwidth (MB/s)')
    plt.legend()
    plt.show()


# draw_bandwidths()


def PSNR(original, compressed):
    mse = np.mean((original - compressed) ** 2)
    if (mse == 0):  # MSE is zero means no noise is present in the signal .
        # Therefore PSNR have no importance.
        return 100
    max_pixel = 255.0
    psnr = 20 * log10(max_pixel / sqrt(mse))
    return psnr


def get_PSNR_linespace(img_path1: str, img_path2: str, num: int) -> List[float]:
    PSNRs = []
    for i in range(0, num):
        pth1 = f'{img_path1}/{i}.png'
        pth2 = f'{img_path2}/{i}.png'
        im1: np.ndarray = cv2.imread(pth1)
        im2: np.ndarray = cv2.imread(pth2)
        psnr = PSNR(im1, im2)
        PSNRs.append(psnr)
    return PSNRs
    # 做折线图，选 30 db 作为基准
    pass

def draw_PSNRs():
    PSNRs = get_PSNR_linespace(r'E:\Py_Projects\player\evaluation\baseline-images/',
                               r'E:\Py_Projects\player\evaluation\view-images/',
                               900)
    PSNRs2 = get_PSNR_linespace(r'E:\Py_Projects\player\evaluation\baseline-images/',
                                r'E:\Py_Projects\player\evaluation\view-images-2/',
                                900)
    base30 = [30.0 for i in range(900)]
    base40 = [40.0 for i in range(900)]
    plt.plot(
        base30, label='Level of 30 dB', color='gray', linestyle='dashed'
    )
    plt.plot(
        base40, label='Level of 40 dB', color='black', linestyle='dashed'
    )
    plt.plot(
        PSNRs, label='Log formula (5)'
    )
    plt.plot(
        PSNRs2, label='Linear formula (6)'
    )
    plt.xlabel('Picture (frame)')
    plt.ylabel('PSNR (dB)')
    plt.legend()
    plt.show()

draw_PSNRs()
