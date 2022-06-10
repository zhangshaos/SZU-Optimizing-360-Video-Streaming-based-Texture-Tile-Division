from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GLUT import *
import glutils
import numpy as np

strVS = """
#version 330 core
layout (location = 0) in vec3 position;
layout (location = 1) in vec2 inTexcoord;
out vec2 outTexcoord;

void main(){
    gl_Position = vec4(position, 1.0f);
    outTexcoord = inTexcoord;
}
"""

strFS = """
#version 330 core
out vec4 FragColor;
in vec2 outTexcoord;
uniform sampler2D texture1;

void main(){
    vec2 fixedTexcoord = vec2(outTexcoord.x, 1-outTexcoord.y);
    FragColor = texture(texture1, fixedTexcoord);
    // FragColor = FragColor * 0.5 + vec4(fixedTexcoord, 1.0, 1.0) * 0.5;
    // FragColor = vec4(fixedTexcoord, 1.0, 1.0);
}
"""


class Texture:
    def __init__(self, id):
        self.id = id

    def get_id(self):
        return self.id


class TexturePlane:
    def __init__(self):
        # # load shaders
        # self.vertexShader = glCreateShader(GL_VERTEX_SHADER)
        # glShaderSource(self.vertexShader, 1, strFS, None)
        # glCompileShader(self.vertexShader)
        #
        # self.fragmentShader = glCreateShader(GL_FRAGMENT_SHADER)
        # glShaderSource(self.fragmentShader, 1, strFS, None)
        # glCompileShader(self.fragmentShader)
        #
        # shaderProgram = glCreateProgram()
        # self.program = glAttachShader(shaderProgram, self.vertexShader)
        # self.program = glAttachShader(shaderProgram, self.fragmentShader)
        # glUseProgram(self.program)  # 在glUseProgram函数调用之后，每个着色器调用和渲染调用都会使用这个程序对象（也就是之前写的着色器)了
        # # attributes
        # self.vertIndex = glGetAttribLocation(self.program, b"position")
        # self.texIndex = glGetAttribLocation(self.program, b"inTexcoord")
        # load shaders
        self.program = glutils.loadShaders(strVS, strFS)
        glUseProgram(self.program)
        # attributes
        self.vertIndex = glGetAttribLocation(self.program, b"position")
        self.texIndex = glGetAttribLocation(self.program, b"inTexcoord")
        glUseProgram(0)

        vertices = [
            -1.0, -1.0, 0,
            1.0, -1.0, 0,
            1.0, 1.0, 0,
            -1.0, 1.0, 0
        ]
        vertices = [
            -1.0, -1.0, 0,
            1.0, -1.0, 0,
            1.0, 1.0, 0,
            -1.0, 1.0, 0,
        ]
        # texture coords
        quadT = [
            0.0, 1.0,
            1.0, 1.0,
            1.0, 0.0,
            0.0, 0.0,
        ]
        # set up vertex array object (VAO)
        self.vao = glGenVertexArrays(1)
        glBindVertexArray(self.vao)
        # set up VBOs
        vertexData = np.array(vertices, np.float32)
        self.vertexBuffer = glGenBuffers(1)
        glBindBuffer(GL_ARRAY_BUFFER, self.vertexBuffer)
        glBufferData(GL_ARRAY_BUFFER, 4 * len(vertexData), vertexData, GL_STATIC_DRAW)

        tcData = np.array(quadT, np.float32)
        self.tcBuffer = glGenBuffers(1)
        glBindBuffer(GL_ARRAY_BUFFER, self.tcBuffer)
        glBufferData(GL_ARRAY_BUFFER, 4 * len(tcData), tcData, GL_STATIC_DRAW)

        # enable arrays
        glEnableVertexAttribArray(self.vertIndex)
        glEnableVertexAttribArray(self.texIndex)

        # Position attribute
        glBindBuffer(GL_ARRAY_BUFFER, self.vertexBuffer)
        glVertexAttribPointer(self.vertIndex, 3, GL_FLOAT, GL_FALSE, 0, None)

        # TexCoord attribute
        glBindBuffer(GL_ARRAY_BUFFER, self.tcBuffer)
        glVertexAttribPointer(self.texIndex, 2, GL_FLOAT, GL_FALSE, 0, None)

        # unbind VAO
        glBindVertexArray(0)
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, 0)
        glBindBuffer(GL_ARRAY_BUFFER, 0)

    def render(self, tex_id):
        self.tex_id = tex_id
        # enable texture
        glActiveTexture(GL_TEXTURE0)
        glBindTexture(GL_TEXTURE_2D, self.tex_id)
        # use shader
        glUseProgram(self.program)

        # bind VAO
        glBindVertexArray(self.vao)
        # draw
        glDrawArrays(GL_TRIANGLE_FAN, 0, 4)
        # unbind VAO
        glBindVertexArray(0)
        glUseProgram(0)