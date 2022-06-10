from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GLUT import *
import cv2
import numpy as np
import glutils
from PIL import Image
from texture import Texture, TexturePlane

RADIUS = 1
VIEW = np.array([-0.5, 0.5, -0.5, 0.5, RADIUS, 100])  # 视景体的left/right/bottom/top/near/far六个面
SCALE_K = np.array([1.6, 1.6, 1.6])  # 模型缩放比例
EYE = np.array([0.0, 0.0, 0.02])  # 眼睛的位置（默认z轴的正方向）
LOOK_AT = np.array([0.0, 0.0, 0.0])  # 瞄准方向的参考点（默认在坐标原点）
EYE_UP = np.array([0.0, 1.0, 0.0])  # 定义对观察者而言的上方（默认y轴的正方向）
WIN_W, WIN_H = 1280, 720  # 保存窗口宽度和高度的变量
LEFT_IS_DOWNED = False  # 鼠标左键被按下
MOUSE_X, MOUSE_Y = 0, 0  # 考察鼠标位移量时保存的起始位置
# 视频参数
total_frame = 30
width = 7680
height = 3840
row = 4
col = 6
tile_width = int(width / col)
tile_height = int(height / row)
tile_4k_dir = "./Tokyo-images/4k/"
bg_dir = './Tokyo-images/bg/'
# 视频播放所需变量
frame_buffer_id = 0
texture_buffer_id = 0
render_buffer_id = 0
texture_plane = 0

frame_index = 1

tex_id_bg = 0
tile_dict = {}


def get_posture():
    global EYE, LOOK_AT

    dist = np.sqrt(np.power((EYE - LOOK_AT), 2).sum())
    if dist > 0:
        phi = np.arcsin((EYE[1] - LOOK_AT[1]) / dist)
        theta = np.arcsin((EYE[0] - LOOK_AT[0]) / (dist * np.cos(phi)))
    else:
        phi = 0.0
        theta = 0.0

    return dist, phi, theta


DIST, PHI, THETA = get_posture()  # 眼睛与观察目标之间的距离、仰角、方位角


def init():
    global width, height
    global frame_buffer_id, texture_buffer_id, render_buffer_id, texture_plane

    glClearColor(1.0, 1.0, 0.0, 1.0)  # 设置画布背景色。注意：这里必须是4个参数
    glEnable(GL_DEPTH_TEST)  # 开启深度测试，实现遮挡关系
    glDepthFunc(GL_LEQUAL)  # 设置深度测试函数（GL_LEQUAL只是选项之一）
    frame_buffer_id = glGenFramebuffers(1)
    glBindFramebuffer(GL_FRAMEBUFFER, frame_buffer_id)

    texture_buffer_id = glGenTextures(1)
    glBindTexture(GL_TEXTURE_2D, texture_buffer_id)
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, width, height, 0, GL_RGBA, GL_UNSIGNED_BYTE, None)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
    glFramebufferTexture2D(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, GL_TEXTURE_2D, texture_buffer_id, 0)

    render_buffer_id = glGenRenderbuffers(1)
    glBindRenderbuffer(GL_RENDERBUFFER, render_buffer_id)
    glRenderbufferStorage(GL_RENDERBUFFER, GL_DEPTH24_STENCIL8, width, height)
    glBindRenderbuffer(GL_RENDERBUFFER, 0)
    glFramebufferRenderbuffer(GL_FRAMEBUFFER, GL_DEPTH_STENCIL_ATTACHMENT, GL_RENDERBUFFER, render_buffer_id)

    if glCheckFramebufferStatus(GL_FRAMEBUFFER) != GL_FRAMEBUFFER_COMPLETE:
        print("ERROR::FRAMEBUFFER:: Framebuffer is not complete!")
    glBindFramebuffer(GL_FRAMEBUFFER, 0)

    texture_plane = TexturePlane()


def read_bg_texture():
    global bg_dir
    global tex_id_bg
    global frame_index, total_frame
    img = cv2.cvtColor(cv2.imread(bg_dir + str(frame_index % total_frame + 1) + ".bmp"), cv2.COLOR_BGR2RGB)
    print(bg_dir + str(frame_index) + ".bmp")
    img_data = img.tobytes()
    tex_id_bg = glGenTextures(1)  # 获取一个纹理索引
    glBindTexture(GL_TEXTURE_2D, tex_id_bg)  # 绑定纹理对象, 下面的操作都是针对text_id号纹理
    glPixelStorei(GL_UNPACK_ALIGNMENT, 1)  # 对齐像素字节
    glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT)
    glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT)
    glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)  # mipmap用的滤波
    glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
    glTexEnvf(GL_TEXTURE_ENV, GL_TEXTURE_ENV_MODE, GL_DECAL)  #
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, img.shape[1], img.shape[0], 0,
                 GL_RGB, GL_UNSIGNED_BYTE, img_data)


def read_tile_texture():
    global tile_width, tile_height
    global row, col
    global tile_4k_dir
    global tile_dict
    global frame_index, total_frame

    for r in range(2, row):
        for c in range(0, col):
            dir = tile_4k_dir + str(r * col + c)
            filename = dir + '/' + str(frame_index % total_frame + 1) + ".bmp"
            img = cv2.cvtColor(cv2.imread(filename), cv2.COLOR_BGR2RGB)

            tex_id = glGenTextures(1)  # 获取一个纹理索引
            glBindTexture(GL_TEXTURE_2D, tex_id)  # 绑定纹理对象, 下面的操作都是针对text_id号纹理
            glPixelStorei(GL_UNPACK_ALIGNMENT, 1)  # 对齐像素字节
            tile_dict[tex_id] = [r, c]

            img_data = img.tobytes()
            glBindTexture(GL_TEXTURE_2D, tex_id)
            glPixelStorei(GL_UNPACK_ALIGNMENT, 1)
            glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT)
            glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT)
            glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
            glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
            glTexEnvf(GL_TEXTURE_ENV, GL_TEXTURE_ENV_MODE, GL_DECAL)
            glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, tile_width, tile_height, 0,
                         GL_RGB, GL_UNSIGNED_BYTE, img_data)

    return tile_dict


def draw():
    global VIEW
    global EYE, LOOK_AT, EYE_UP
    global SCALE_K
    global WIN_W, WIN_H
    global frame_buffer_id, texture_buffer_id, texture_plane
    global width, height
    global tex_id_bg, tile_dict
    global frame_index

    # Textured thing
    read_bg_texture()
    read_tile_texture()

    glBindFramebuffer(GL_FRAMEBUFFER, frame_buffer_id)
    glViewport(0, 0, width, height)
    glClearColor(0.0, 0.0, 0.0, 1.0)
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glDisable(GL_DEPTH_TEST)
    # glEnable(GL_BLEND)
    # glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
    glViewport(0, 0, width, height)
    texture_plane.render(tex_id_bg)
    for tile_id, pos in tile_dict.items():
        glViewport(pos[1]*tile_width, pos[0]*tile_height, tile_width, tile_height)
        texture_plane.render(tile_id)
    # glDisable(GL_BLEND)
    glEnable(GL_DEPTH_TEST)
    glClearColor(1.0, 1.0, 0.0, 1.0)
    glBindFramebuffer(GL_FRAMEBUFFER, 0)

    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)  # 清除屏幕及深度缓存

    # 设置投影（透视投影）
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()

    if WIN_W > WIN_H:
        k = WIN_W / WIN_H
        glFrustum(VIEW[0] * k, VIEW[1] * k, VIEW[2], VIEW[3], VIEW[4], VIEW[5])
    else:
        k = WIN_H / WIN_W
        glFrustum(VIEW[0], VIEW[1], VIEW[2] * k, VIEW[3] * k, VIEW[4], VIEW[5])

    # 设置模型视图
    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()

    # 几何变换
    glScale(SCALE_K[0], SCALE_K[1], SCALE_K[2])

    # 设置视点
    gluLookAt(
        EYE[0], EYE[1], EYE[2],
        LOOK_AT[0], LOOK_AT[1], LOOK_AT[2],
        EYE_UP[0], EYE_UP[1], EYE_UP[2]
    )

    # 设置视口
    glViewport(0, 0, WIN_W, WIN_H)

    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    # texturePlane.render(texture_buffer_id)

    glPushMatrix()
    qobj = gluNewQuadric()  # 绘制球面
    gluQuadricTexture(qobj, GL_TRUE)
    glRotatef(90, 1.0, 0.0, 0.0)
    glEnable(GL_TEXTURE_2D)
    glBindTexture(GL_TEXTURE_2D, texture_buffer_id)
    # glBindTexture(GL_TEXTURE_2D, tex_id_bg)
    gluSphere(qobj, 1, 50, 50)  # quad, radius, 精细程度
    gluDeleteQuadric(qobj)
    glDisable(GL_TEXTURE_2D)
    glPopMatrix()

    glutSwapBuffers()  # 切换缓冲区，以显示绘制内容

    frame_index += 1


def reshape(w, h):
    """响应窗口变化"""
    global WIN_W, WIN_H

    WIN_W, WIN_H = w, h
    glutPostRedisplay()


def mouseclick(button, state, x, y):
    global SCALE_K
    global LEFT_IS_DOWNED
    global MOUSE_X, MOUSE_Y

    MOUSE_X, MOUSE_Y = x, y
    if button == GLUT_LEFT_BUTTON:
        LEFT_IS_DOWNED = state == GLUT_DOWN
    # elif button == 3:
    #     SCALE_K *= 1.05
    #     glutPostRedisplay()  # 响应刷新消息
    # elif button == 4:
    #     SCALE_K *= 0.95
    #     glutPostRedisplay()


def mouse_motion(x, y):
    global LEFT_IS_DOWNED
    global EYE, EYE_UP
    global MOUSE_X, MOUSE_Y
    global DIST, PHI, THETA
    global WIN_W, WIN_H

    if LEFT_IS_DOWNED:
        dx = MOUSE_X - x
        dy = y - MOUSE_Y
        MOUSE_X, MOUSE_Y = x, y

        PHI -= 2 * np.pi * dy / WIN_H
        PHI %= 2 * np.pi
        THETA -= 2 * np.pi * dx / WIN_W
        THETA %= 2 * np.pi
        r = DIST * np.cos(PHI)

        EYE[1] = DIST * np.sin(PHI)
        EYE[0] = r * np.sin(THETA)
        EYE[2] = r * np.cos(THETA)

        if 0.5 * np.pi < PHI < 1.5 * np.pi:
            EYE_UP[1] = -1.0
        else:
            EYE_UP[1] = 1.0

        glutPostRedisplay()


def keydown(key, x, y):
    global DIST, PHI, THETA
    global EYE, LOOK_AT, EYE_UP
    global VIEW

    if key in [b'x', b'X', b'y', b'Y', b'z', b'Z']:
        if key == b'x':  # 瞄准参考点 x 减小
            LOOK_AT[0] -= 0.01
        elif key == b'X':  # 瞄准参考 x 增大
            LOOK_AT[0] += 0.01
        elif key == b'y':  # 瞄准参考点 y 减小
            LOOK_AT[1] -= 0.01
        elif key == b'Y':  # 瞄准参考点 y 增大
            LOOK_AT[1] += 0.01
        elif key == b'z':  # 瞄准参考点 z 减小
            LOOK_AT[2] -= 0.01
        elif key == b'Z':  # 瞄准参考点 z 增大
            LOOK_AT[2] += 0.01

        DIST, PHI, THETA = get_posture()
        glutPostRedisplay()
    elif key == b'\r':  # 回车键，视点前进
        EYE = LOOK_AT + (EYE - LOOK_AT) * 0.9
        DIST, PHI, THETA = get_posture()
        glutPostRedisplay()
    elif key == b'\x08':  # 退格键，视点后退
        EYE = LOOK_AT + (EYE - LOOK_AT) * 1.1
        DIST, PHI, THETA = get_posture()
        glutPostRedisplay()


def timer(value):
    draw()
    glutTimerFunc(10, timer, 0)


if __name__ == "__main__":
    glutInit()
    displayMode = GLUT_DOUBLE | GLUT_ALPHA | GLUT_DEPTH
    glutInitDisplayMode(displayMode)

    glutInitWindowSize(WIN_W, WIN_H)
    glutInitWindowPosition(300, 200)
    glutCreateWindow('360 player')

    init()
    glutDisplayFunc(draw)
    glutReshapeFunc(reshape)
    glutMouseFunc(mouseclick)
    glutMotionFunc(mouse_motion)
    glutKeyboardFunc(keydown)

    glutTimerFunc(10, timer, 0)

    glutMainLoop()
