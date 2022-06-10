
[toc]
- [**Optimizing 360-Degree Video Streaming based Texture Tile Division**](#optimizing-360-degree-video-streaming-based-texture-tile-division)
  - [项目结构](#项目结构)
  - [联系方式](#联系方式)

# **Optimizing 360-Degree Video Streaming based Texture Tile Division**


## 项目结构

- **Presentation.pptx**  
  项目介绍。
- "Optimizing 360-Degree Video Streaming based Texture Tile Division".pdf
  论文。
- README.md  
  此文件。
- manifest.json  
  manifest 例子，请参考这个文件理解网络传输过程。
- decoders.py  
  解码器，下载视频并解码。通常不需要直接使用此文件。
- video_request.py  
  下载器和解码器和包装，直接使用此文件就好。
- evaluation/
  - baseline.py  
    Baseline 系统
  - demo.py  
    论文系统（main.py）
  - calculate_metrics.py  
    统计数据，并作图，写论文用
  - generate_path.py  
    生成一条随机路径
- renderer/
  - main.py  
    渲染器入口函数

## 联系方式

章星明 xingmingzhangssr@gmail
