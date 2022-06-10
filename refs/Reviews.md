---
介绍：三篇文章「全景视频自适应传输技术研究与系统实现」、「基于DASH的全景视频传输技术研究」、「基于Tile的全景视频自适应传输技术研究」的 Review！  
时间：2021/12/3  
作者：章星明  
---

[toc]
- [基于DASH的全景视频传输技术研究 - 北京邮电大学 2019 硕士学位论文](#基于dash的全景视频传输技术研究---北京邮电大学-2019-硕士学位论文)
  - [投影方案](#投影方案)
    - [等角投影(Equirectangular Projection, ERP)](#等角投影equirectangular-projection-erp)
    - [立方体投影(Cube Map Projection, CMP)](#立方体投影cube-map-projection-cmp)
    - [截断方形金字塔投影(Truncated Square Pyramid Projection, TSP)](#截断方形金字塔投影truncated-square-pyramid-projection-tsp)
  - [传输方案](#传输方案)
    - [VIS(Viewport-independent Streaming)](#visviewport-independent-streaming)
    - [VDS(Viewport-dependent Streaming)](#vdsviewport-dependent-streaming)
    - [TBS(Tile-based Streaming)](#tbstile-based-streaming)
      - [DASH标准扩展-SRD(Spatial Relationship Description)](#dash标准扩展-srdspatial-relationship-description)
- [基于Tile的全景视频自适应传输技术研究 - 西安电子科技大学 2019 硕士论文](#基于tile的全景视频自适应传输技术研究---西安电子科技大学-2019-硕士论文)
- [全景视频自适应传输技术研究与系统实现 - 上海交通大学 2019 硕士论文](#全景视频自适应传输技术研究与系统实现---上海交通大学-2019-硕士论文)

# 基于DASH的全景视频传输技术研究 - 北京邮电大学 2019 硕士学位论文

```
球形全景视频 >-平面投影-> 平面矩形视频 >-压缩编码、传输-> >-解码、逆变换-> 球形全景视频
```

## 投影方案
投影变换是为了将球形的全景视频映射到矩形平面上。

- 矩形平面上的像素数量 > 球面像素数量，导致过采样。  
  即产生了冗余的像素，像素采样密度过大。
- 矩形平面上的像素数量 < 球面像素数量，导致欠采样。  
  即产生了像素的丢失，像素采样密度过小。

### 等角投影(Equirectangular Projection, ERP)
类似地图的展开，按照经纬线展开，将球面投影到外接圆柱体的侧面，然后展开为矩形

### 立方体投影(Cube Map Projection, CMP)
将球面按照径向投影到外接立方体的六个面上，然后展开并组合为一个平面

### 截断方形金字塔投影(Truncated Square Pyramid Projection, TSP)
**视点相关**，类似CMP，不过将外接立方体变成一个四棱台，然后将四棱台的六个面展开并组合为一个平面。  
先使用CMP算法展开为一个立方体，然后将立方体压缩为一个四棱台，就是TSP！

## 传输方案

### VIS(Viewport-independent Streaming)
一般采用 ERP 编码，然后和一般视频相同地编码、传输。

**特点：**  
1. 带宽要求高，在有限的带宽资源下，需要长时间的缓冲才能观看。
2. 同时只播放一部分，因此带宽利用率很低。

### VDS(Viewport-dependent Streaming)
同一个视频根据多个预设视点，创造多个视频文件，每个视频文件在视点附近使用高画质（其他区域使用低画质）。  
当用户在观看过程视点发生变化后，客户端随之切换视频文件。

**特点：**
1. 相比VIS方案，带宽降低了 80%。
2. 相比VIS文案，视频文件存储增加了 6倍。

### TBS(Tile-based Streaming)
将全景视频划分为若干个矩形的Tile，每个Tile对应画面特定区域。  
根据视点选择一部分Tile进行传输。

#### DASH标准扩展-SRD(Spatial Relationship Description)

**特点：**
1. 不同Tile的码率分配不同，所有的Tile都可以进行独立传输

# 基于Tile的全景视频自适应传输技术研究 - 西安电子科技大学 2019 硕士论文

<img src='https://tva4.sinaimg.cn/large/006VDfrXly1gxj3mvho2jj314w0d6dls.jpg' width='720px'/>

系统同时下载两个版本的视频：
- 低分辨率的整个视频
- 高分辨率的视口对应的分片

将两个版本的视频进行融合，作为全景视频内容！

# 全景视频自适应传输技术研究与系统实现 - 上海交通大学 2019 硕士论文


