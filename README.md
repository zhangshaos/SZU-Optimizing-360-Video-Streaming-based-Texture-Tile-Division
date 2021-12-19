---
记录一些网络使用的术语和概念  
作者：章星明  
时间：2021//12//23  
---


- [项目：**360 Video Adaptive Streaming**](#项目360-video-adaptive-streaming)
- [会议进度](#会议进度)
- [术语概念（网络）](#术语概念网络)
  - [波特率（Baud, symbol/s）](#波特率baud-symbols)
  - [比特率（bit rate）](#比特率bit-rate)
  - [带宽（bandwidth）](#带宽bandwidth)
  - [码率/码流（data rate）](#码率码流data-rate)
- [术语概念（音视频）](#术语概念音视频)
  - [DASH](#dash)
- [系统实现](#系统实现)
  - [服务器切片](#服务器切片)
  - [网络传输](#网络传输)
  - [客户端渲染](#客户端渲染)

# 项目：**360 Video Adaptive Streaming**

# 会议进度

- 2021/11/18 中午：  
  - [x] 确定选题「全景视频的传输」  
  - [ ] 确定算法
- 2021/11/22 和老师交流：
  - [x] 确定实验如何设计：  
      QoE（Quality of Experience）使用**选区内平均分辨率、视频清晰度抖动、重新缓存时间**作为对比指标；  
      对比对象选择那些在全传输上做一丢丢优化的方法（类似我们方法的消融实验）。  
      ~~（也可以选择已有开源算法实现做对比）~~
- 2021/11/24 晚上：
  - [x] 任务分配：  
      1. 实验验证系统（先做这个）  
         搭建整个测试系统（不包括算法，但是需要给算法预留接口）。   
         具体来说：准备视频服务器（**如何搭建模拟网络的环境？** 参考Pensieve的设置），准备视频内容，创建一个视频播放器（给算法预留接口）  
      2. 算法验证（需要等系统搭建完成再开始实验）  
         边做实验边修改思路  
         先讨论一下想法！
      > 1. 不再需要 eye tracker
      > 2. 方法思路：
      > - 预测人的行为难度大（眼球不动，则表示用户着重某一处；眼球快速移动，则表示用户随机「搜索」）
      > - 预测每个块的纹理复杂度难度不大（对纹理复杂的块，传输高分辨率）
      > - 调整块切割方法，可以降低调用「分辨率选择算法」的次数，每一帧的块越少，次数越小。  
      例如，根据360全景视频不同地方的挤压变形程度不同，而区分不同的块边界。
      3. PPT和论文（**让一个人来写！**）  
         这部分暂时由我自己负责  
      > 注意：任务的分配需要通力合作，而不是各自只做自己的那部分。
  - [x] 边做实验边修改思路
  - [x] 考虑15周，12/13开始演讲，因此分配工作：  
    1. 佳生：DASH全景视频播放器
    2. 宇东：视频服务器后端
    3. 我：虚拟环境
- 2021/12/2 晚上：  
  **TODO……**

- 服务器端：  
  - 编码低分辨率（$L_1$）的 chunk 块（10s）
  - 编码不同分辨率（$L2、L3、L4、L5$）的 tiles 块（1s，将一个chunk拆分为 $X\times X$）  
    对每个 tile，标记他的纹理复杂度$C$，  
    将所有相邻并且$纹理复杂度C>C_0$的 tile 标记到一个集合$S_i=\{tile_1...tile_j\}$，  
    对每个 tile，标记它属于的集合$S_i$（纹理复杂度不够，或者没有相邻的复杂tile的，不作此标记）

- 播放器端：
  - 每隔10s，请求整个全景视频的 chunk 块（质量为 $L_1$）  
    （这个请求的请求时间和下面这个请求时间分开）
  - 每隔1s，将视口内所有 tile 加入到集合 $Ts=\{t_i\}$，  
    并将 $ti$ 对应的 $S_i$ 中的 tile 也加入 $Ts$ 中  
    根据设置的带宽限制 $B_{0}$ ，设置每个 tile 的比特率 $B_{tile}=B_0 \times C_{tile}$，根据此比特率选择分辨率 $L_{tile}$ 

分工（2021//12//14）

- 宇东：
  编码、切片、复杂度检测、合并MPD  
  ddl：周四晚上

- 我：
  解析 MPD，请求视频块  
  ddl：周四晚上

- 佳生：
  渲染视频  
  ddl：周四晚上

# 术语概念（网络）

## 波特率（Baud, symbol/s）

调制解调信号的速度，表示码元传输速度。

## 比特率（bit rate）

实时计算出来。

## 带宽（bandwidth）

带宽，又叫频宽，是数据的传输能力，指单位时间内能够传输的比特数。  
数字设备中带宽用 bps（b/s）表示，即每秒最高可以传输的位数。  
模拟设备中带宽用 Hz 表示，即每秒传送的信号周期数。

这个通常取决于你的网络环境。

> 带宽和比特率经常混为一谈，实际上带宽应该理解为容量，比特率理解为实时的速度

## 码率/码流（data rate）

视频文件在单位时间内使用的数据流量，可以理解为视频文件大小除以视频时长。


# 术语概念（音视频）

> 参考文章：https://zhuanlan.zhihu.com/p/69184805

## DASH

Dynamic Adaptive Streaming over HTTP 的缩写。


# 系统实现

## 服务器切片


## 网络传输

1. 请求，并解析 manifest.json 文件，取得服务器切片配置
2. <img src='https://tva4.sinaimg.cn/large/006VDfrXgy1gxj4tl7rv1j319p0xs1a2.jpg'>  
3. 如上图所示，系统产生 1 + tile-num 个视频文件下载/解码器：  
   一个 whole chunk decoder 和 tile-num 个 tile chunk decoder  
   每个 decoder 含有一个帧缓存，用来保存那些已经解码完成的图片（纹理）


## 客户端渲染

