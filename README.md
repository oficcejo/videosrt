# 视频自动字幕生成工具与填充词过滤

这是一个用Python开发的视频处理工具，可以自动去除视频中的"嗯"、"啊"等无用填充词，并生成干净的中文字幕。

## 功能特点

- 自动提取视频中的音频
- 使用语音识别技术将音频转换为文本
- 智能过滤"嗯"、"啊"、"呃"等填充词
- 支持多种字幕格式导出（SRT、ASS、TXT）
- 视频预览功能
- 简洁直观的图形用户界面

## 支持的字幕格式

- **SRT格式**：适用于Adobe Premiere Pro、Vegas Pro等专业视频编辑软件
- **ASS格式**：适用于剪映等视频编辑软件
- **TXT格式**：适用于必剪等视频编辑软件

## 使用方法

1. 启动应用程序
2. 点击"浏览"按钮选择输入视频文件
3. 程序会自动设置输出视频路径，您也可以自定义
4. 点击"开始处理"按钮开始处理视频
5. 处理完成后，可以点击"预览"按钮查看处理结果
6. 选择所需的字幕格式，点击"导出字幕"按钮导出字幕文件

## 安装步骤

### 环境要求
- Python 3.8或更高版本
- FFmpeg（已包含在项目中）

### 安装依赖

1. 新建激活虚拟环境：
   ```
   python -m venv venv
   venv\Scripts\activate
   ```

2. 安装所需依赖：
   ```
   pip install -r requirements.txt
   ```

   或手动安装：
   ```
   pip install pillow opencv-python ffmpeg-python pydub speechrecognition jieba numpy matplotlib
   ```
3. 安装ffmpeg
4. ```
   powershell -Command $ProgressPreference = 'SilentlyContinue'; Invoke-WebRequest -Uri 'https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip' -OutFile 'ffmpeg.zip'; Expand-Archive -Path 'ffmpeg.zip' -DestinationPath '.\' -Force; Move-Item -Path '.\ffmpeg-master-latest-win64-gpl\bin\*' -Destination '.\' -Force; Remove-Item -Path 'ffmpeg.zip' -Force; Remove-Item -Path '.\ffmpeg-master-latest-win64-gpl' -Recurse -Force
   ```
## 运行程序

激活虚拟环境后，运行以下命令启动程序：

```
python main.py
```

## 注意事项

- 首次运行语音识别功能时，可能需要下载相关模型，请确保网络连接正常
- 处理大型视频文件可能需要较长时间，请耐心等待
- 语音识别准确率受原始音频质量影响
- 使用google语音识别服务，中国大陆使用可能受到影响
