import os
import sys
import time
import threading
import tkinter as tk
from tkinter import filedialog, ttk, messagebox
from PIL import Image, ImageTk
import cv2
import numpy as np
import speech_recognition as sr
import jieba
import ffmpeg
from pydub import AudioSegment
import re

class VideoProcessor:
    def __init__(self):
        self.filler_words = ['嗯', '啊', '呃', '额', '那个', '这个', '就是', '然后', '所以', '其实', '你知道', '我觉得']
        self.recognizer = sr.Recognizer()
        
    def extract_audio(self, video_path, output_audio_path):
        """
        从视频中提取音频
        """
        try:
            (ffmpeg
             .input(video_path)
             .output(output_audio_path, acodec='pcm_s16le', ac=1, ar='16k')
             .run(capture_stdout=True, capture_stderr=True, overwrite_output=True))
            return True
        except ffmpeg.Error as e:
            print(f"提取音频时出错: {e.stderr.decode()}")
            return False
    
    def split_audio(self, audio_path, chunk_length_ms=10000):
        """
        将音频分割成小块以便处理
        """
        audio = AudioSegment.from_wav(audio_path)
        chunks = []
        
        for i in range(0, len(audio), chunk_length_ms):
            chunk = audio[i:i + chunk_length_ms]
            chunk_path = f"{audio_path.replace('.wav', '')}_chunk_{i//chunk_length_ms}.wav"
            chunk.export(chunk_path, format="wav")
            chunks.append(chunk_path)
            
        return chunks
    
    def recognize_speech(self, audio_path):
        """
        使用语音识别将音频转换为文本
        """
        with sr.AudioFile(audio_path) as source:
            audio_data = self.recognizer.record(source)
            try:
                text = self.recognizer.recognize_google(audio_data, language='zh-CN')
                return text
            except sr.UnknownValueError:
                return ""
            except sr.RequestError as e:
                print(f"无法从Google Speech Recognition服务获取结果; {e}")
                return ""
    
    def filter_filler_words(self, text):
        """
        过滤掉填充词
        """
        for word in self.filler_words:
            text = re.sub(f"\\b{word}\\b", "", text)
            text = text.replace(word, "")
        
        # 移除多余的空格
        text = re.sub(r'\s+', ' ', text).strip()
        return text
    
    def format_time(self, milliseconds):
        """
        将毫秒转换为SRT时间格式 (HH:MM:SS,mmm)
        """
        seconds, milliseconds = divmod(milliseconds, 1000)
        minutes, seconds = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"
    
    def format_time_ass(self, milliseconds):
        """
        将毫秒转换为ASS时间格式 (H:MM:SS.cc)
        """
        centiseconds = int(milliseconds / 10)
        seconds, centiseconds = divmod(centiseconds, 100)
        minutes, seconds = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)
        return f"{hours}:{minutes:02d}:{seconds:02d}.{centiseconds:02d}"
        
    def export_subtitle_srt(self, chunks_transcriptions, output_path):
        """
        导出SRT格式字幕文件 (适用于PR、Vegas等)
        """
        with open(output_path, 'w', encoding='utf-8') as f:
            subtitle_index = 1
            current_time = 0
            
            for i, text in enumerate(chunks_transcriptions):
                if text.strip():
                    start_time = self.format_time(current_time)
                    end_time = self.format_time(current_time + 10000)  # 假设每个块10秒
                    
                    f.write(f"{subtitle_index}\n")
                    f.write(f"{start_time} --> {end_time}\n")
                    f.write(f"{text}\n\n")
                    
                    subtitle_index += 1
                current_time += 10000
        return True
    
    def export_subtitle_ass(self, chunks_transcriptions, output_path):
        """
        导出ASS格式字幕文件 (适用于剪映等)
        """
        with open(output_path, 'w', encoding='utf-8') as f:
            # 写入ASS文件头
            f.write("[Script Info]\n")
            f.write("Title: 自动生成的字幕\n")
            f.write("ScriptType: v4.00+\n")
            f.write("Collisions: Normal\n")
            f.write("PlayResX: 1920\n")
            f.write("PlayResY: 1080\n\n")
            
            # 写入样式
            f.write("[V4+ Styles]\n")
            f.write("Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n")
            f.write("Style: Default,微软雅黑,54,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,2,0,2,10,10,10,1\n\n")
            
            # 写入事件
            f.write("[Events]\n")
            f.write("Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n")
            
            current_time = 0
            for i, text in enumerate(chunks_transcriptions):
                if text.strip():
                    start_time = self.format_time_ass(current_time)
                    end_time = self.format_time_ass(current_time + 10000)  # 假设每个块10秒
                    
                    f.write(f"Dialogue: 0,{start_time},{end_time},Default,,0,0,0,,{text}\n")
                
                current_time += 10000
        return True
    
    def export_subtitle_txt(self, chunks_transcriptions, output_path):
        """
        导出TXT格式字幕文件 (适用于必剪等)
        """
        with open(output_path, 'w', encoding='utf-8') as f:
            current_time = 0
            for i, text in enumerate(chunks_transcriptions):
                if text.strip():
                    start_seconds = current_time / 1000
                    end_seconds = (current_time + 10000) / 1000  # 假设每个块10秒
                    
                    # 格式: [开始时间(秒)] [结束时间(秒)] 文本内容
                    f.write(f"{start_seconds:.2f} {end_seconds:.2f} {text}\n")
                
                current_time += 10000
        return True
        
    def generate_subtitles(self, chunks_transcriptions, output_srt_path):
        """
        生成SRT格式的字幕文件
        """
        return self.export_subtitle_srt(chunks_transcriptions, output_srt_path)
    
    def embed_subtitles(self, video_path, subtitle_path, output_path):
        """
        将字幕嵌入到视频中
        """
        try:
            # 对路径进行处理，确保路径格式正确
            subtitle_path_escaped = subtitle_path.replace('\\', '\\\\').replace(':', '\\:')
            
            # 使用单引号包裹字幕路径，并确保路径格式正确
            (ffmpeg
             .input(video_path)
             .output(output_path, vf=f"subtitles='{subtitle_path_escaped}'")
             .run(capture_stdout=True, capture_stderr=True, overwrite_output=True))
            return True
        except ffmpeg.Error as e:
            print(f"嵌入字幕时出错: {e.stderr.decode()}")
            return False
    
    def process_video(self, video_path, output_path, progress_callback=None):
        """
        处理视频的主函数
        """
        # 创建临时目录 - 确保临时目录与输出视频在同一驱动器上
        output_dir = os.path.dirname(output_path)
        temp_dir = os.path.join(output_dir, "temp")
        os.makedirs(temp_dir, exist_ok=True)
        
        # 提取音频
        if progress_callback:
            progress_callback(10, "正在提取音频...")
        
        audio_path = os.path.join(temp_dir, "audio.wav")
        if not self.extract_audio(video_path, audio_path):
            return False
        
        # 分割音频
        if progress_callback:
            progress_callback(20, "正在分割音频...")
        
        audio_chunks = self.split_audio(audio_path)
        
        # 语音识别
        if progress_callback:
            progress_callback(30, "正在进行语音识别...")
        
        transcriptions = []
        total_chunks = len(audio_chunks)
        
        for i, chunk_path in enumerate(audio_chunks):
            text = self.recognize_speech(chunk_path)
            transcriptions.append(text)
            if progress_callback:
                progress = 30 + (i / total_chunks) * 30
                progress_callback(progress, f"正在识别第 {i+1}/{total_chunks} 段音频...")
        
        # 过滤填充词
        if progress_callback:
            progress_callback(60, "正在过滤填充词...")
        
        filtered_transcriptions = [self.filter_filler_words(text) for text in transcriptions]
        
        # 生成字幕文件
        if progress_callback:
            progress_callback(70, "正在生成字幕文件...")
        
        subtitle_path = os.path.join(temp_dir, "subtitles.srt")
        self.generate_subtitles(filtered_transcriptions, subtitle_path)
        
        # 嵌入字幕
        if progress_callback:
            progress_callback(80, "正在嵌入字幕到视频...")
        
        if not self.embed_subtitles(video_path, subtitle_path, output_path):
            return False
        
        # 清理临时文件
        if progress_callback:
            progress_callback(90, "正在清理临时文件...")
        
        for chunk_path in audio_chunks:
            try:
                os.remove(chunk_path)
            except:
                pass
        
        try:
            os.remove(audio_path)
            os.remove(subtitle_path)
            os.rmdir(temp_dir)
        except:
            pass
        
        if progress_callback:
            progress_callback(100, "处理完成!")
        
        return True

class VideoProcessorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("视频填充词过滤与字幕生成工具")
        self.root.geometry("800x600")
        self.root.resizable(True, True)
        
        self.processor = VideoProcessor()
        self.video_path = ""
        self.output_path = ""
        self.processing_thread = None
        self.preview_thread = None
        self.preview_running = False
        
        self.setup_ui()
    
    def setup_ui(self):
        # 创建主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 文件选择区域
        file_frame = ttk.LabelFrame(main_frame, text="文件选择", padding="10")
        file_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(file_frame, text="输入视频:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.input_entry = ttk.Entry(file_frame, width=50)
        self.input_entry.grid(row=0, column=1, padx=5, pady=5)
        ttk.Button(file_frame, text="浏览", command=self.browse_input).grid(row=0, column=2, padx=5, pady=5)
        
        ttk.Label(file_frame, text="输出视频:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.output_entry = ttk.Entry(file_frame, width=50)
        self.output_entry.grid(row=1, column=1, padx=5, pady=5)
        ttk.Button(file_frame, text="浏览", command=self.browse_output).grid(row=1, column=2, padx=5, pady=5)
        
        # 字幕导出区域
        subtitle_frame = ttk.LabelFrame(main_frame, text="字幕导出", padding="10")
        subtitle_frame.pack(fill=tk.X, pady=5)
        
        # 字幕格式选择
        ttk.Label(subtitle_frame, text="字幕格式:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.subtitle_format = tk.StringVar(value="srt")
        format_frame = ttk.Frame(subtitle_frame)
        format_frame.grid(row=0, column=1, sticky=tk.W, pady=5)
        
        ttk.Radiobutton(format_frame, text="SRT (PR、Vegas)", variable=self.subtitle_format, value="srt").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(format_frame, text="ASS (剪映)", variable=self.subtitle_format, value="ass").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(format_frame, text="TXT (必剪)", variable=self.subtitle_format, value="txt").pack(side=tk.LEFT, padx=5)
        
        # 导出按钮
        self.export_button = ttk.Button(subtitle_frame, text="导出字幕", command=self.export_subtitle)
        self.export_button.grid(row=0, column=2, padx=5, pady=5)
        self.export_button.config(state=tk.DISABLED)
        
        # 预览区域
        preview_frame = ttk.LabelFrame(main_frame, text="视频预览", padding="10")
        preview_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.preview_canvas = tk.Canvas(preview_frame, bg="black")
        self.preview_canvas.pack(fill=tk.BOTH, expand=True)
        
        # 进度条区域
        progress_frame = ttk.Frame(main_frame, padding="10")
        progress_frame.pack(fill=tk.X, pady=5)
        
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var, length=100, mode='determinate')
        self.progress_bar.pack(fill=tk.X, pady=5)
        
        self.status_label = ttk.Label(progress_frame, text="就绪")
        self.status_label.pack(pady=5)
        
        # 按钮区域
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=10)
        
        self.process_button = ttk.Button(button_frame, text="开始处理", command=self.start_processing)
        self.process_button.pack(side=tk.RIGHT, padx=5)
        
        self.preview_button = ttk.Button(button_frame, text="预览", command=self.toggle_preview, state=tk.DISABLED)
        self.preview_button.pack(side=tk.RIGHT, padx=5)
        
        # 版权信息区域
        copyright_frame = ttk.Frame(main_frame)
        copyright_frame.pack(fill=tk.X, pady=5)
        
        copyright_label = ttk.Label(copyright_frame, text="CGZ作品 www.zhongdu.net", font=("Arial", 9), foreground="#666666")
        copyright_label.pack(side=tk.RIGHT, padx=5)
    
    def browse_input(self):
        filetypes = [("视频文件", "*.mp4 *.avi *.mkv *.mov"), ("所有文件", "*.*")]
        filepath = filedialog.askopenfilename(filetypes=filetypes)
        if filepath:
            self.video_path = filepath
            self.input_entry.delete(0, tk.END)
            self.input_entry.insert(0, filepath)
            
            # 自动设置输出路径
            filename = os.path.basename(filepath)
            name, ext = os.path.splitext(filename)
            output_path = os.path.join(os.path.dirname(filepath), f"{name}_processed{ext}")
            self.output_path = output_path
            self.output_entry.delete(0, tk.END)
            self.output_entry.insert(0, output_path)
            
            # 启用预览按钮和导出按钮
            self.preview_button.config(state=tk.NORMAL)
            self.export_button.config(state=tk.NORMAL)
            
    def browse_output(self):
        filetypes = [("视频文件", "*.mp4 *.avi *.mkv *.mov"), ("所有文件", "*.*")]
        filepath = filedialog.asksaveasfilename(filetypes=filetypes, defaultextension=".mp4")
        if filepath:
            self.output_path = filepath
            self.output_entry.delete(0, tk.END)
            self.output_entry.insert(0, filepath)
            
    def export_subtitle(self):
        if not self.video_path or not os.path.exists(self.video_path):
            messagebox.showerror("错误", "请选择有效的输入视频文件")
            return
        
        # 获取选择的字幕格式
        subtitle_format = self.subtitle_format.get()
        
        # 设置默认的文件扩展名和文件类型
        if subtitle_format == "srt":
            default_ext = ".srt"
            filetypes = [("SRT字幕文件", "*.srt"), ("所有文件", "*.*")]
            title = "导出SRT字幕文件"
        elif subtitle_format == "ass":
            default_ext = ".ass"
            filetypes = [("ASS字幕文件", "*.ass"), ("所有文件", "*.*")]
            title = "导出ASS字幕文件"
        else:  # txt
            default_ext = ".txt"
            filetypes = [("TXT字幕文件", "*.txt"), ("所有文件", "*.*")]
            title = "导出TXT字幕文件"
        
        # 获取输入视频的文件名（不含扩展名）
        filename = os.path.basename(self.video_path)
        name, _ = os.path.splitext(filename)
        default_filename = f"{name}_subtitle{default_ext}"
        
        # 打开文件保存对话框
        subtitle_path = filedialog.asksaveasfilename(
            title=title,
            filetypes=filetypes,
            defaultextension=default_ext,
            initialfile=default_filename,
            initialdir=os.path.dirname(self.video_path)
        )
        
        if not subtitle_path:
            return
        
        # 禁用导出按钮
        self.export_button.config(state=tk.DISABLED)
        
        # 更新状态
        self.status_label.config(text="正在导出字幕...")
        self.progress_var.set(0)
        
        # 在新线程中导出字幕
        threading.Thread(target=self.export_subtitle_thread, args=(subtitle_path, subtitle_format), daemon=True).start()
    
    def export_subtitle_thread(self, subtitle_path, subtitle_format):
        try:
            # 创建临时目录
            temp_dir = os.path.join(os.path.dirname(subtitle_path), "temp_subtitle")
            os.makedirs(temp_dir, exist_ok=True)
            
            # 提取音频
            self.root.after(0, lambda: self.update_progress(10, "正在提取音频..."))
            audio_path = os.path.join(temp_dir, "audio.wav")
            if not self.processor.extract_audio(self.video_path, audio_path):
                raise Exception("音频提取失败")
            
            # 分割音频
            self.root.after(0, lambda: self.update_progress(20, "正在分割音频..."))
            audio_chunks = self.processor.split_audio(audio_path)
            
            # 语音识别
            self.root.after(0, lambda: self.update_progress(30, "正在进行语音识别..."))
            transcriptions = []
            total_chunks = len(audio_chunks)
            
            for i, chunk_path in enumerate(audio_chunks):
                text = self.processor.recognize_speech(chunk_path)
                transcriptions.append(text)
                progress = 30 + (i / total_chunks) * 30
                self.root.after(0, lambda p=progress, idx=i: self.update_progress(p, f"正在识别第 {idx+1}/{total_chunks} 段音频..."))
            
            # 过滤填充词
            self.root.after(0, lambda: self.update_progress(60, "正在过滤填充词..."))
            filtered_transcriptions = [self.processor.filter_filler_words(text) for text in transcriptions]
            
            # 导出字幕
            self.root.after(0, lambda: self.update_progress(80, "正在导出字幕文件..."))
            
            success = False
            if subtitle_format == "srt":
                success = self.processor.export_subtitle_srt(filtered_transcriptions, subtitle_path)
            elif subtitle_format == "ass":
                success = self.processor.export_subtitle_ass(filtered_transcriptions, subtitle_path)
            elif subtitle_format == "txt":
                success = self.processor.export_subtitle_txt(filtered_transcriptions, subtitle_path)
            
            # 清理临时文件
            self.root.after(0, lambda: self.update_progress(90, "正在清理临时文件..."))
            for chunk_path in audio_chunks:
                try:
                    os.remove(chunk_path)
                except:
                    pass
            
            try:
                os.remove(audio_path)
                os.rmdir(temp_dir)
            except:
                pass
            
            if success:
                self.root.after(0, lambda: self.update_progress(100, "字幕导出完成!"))
                self.root.after(0, lambda: messagebox.showinfo("成功", f"字幕已成功导出到: {subtitle_path}"))
            else:
                raise Exception("字幕导出失败")
                
        except Exception as e:
            error_message = str(e)
            self.root.after(0, lambda error=error_message: messagebox.showerror("错误", f"字幕导出过程中出错: {error}"))
            self.root.after(0, lambda: self.update_progress(0, "导出失败"))
        finally:
            self.root.after(0, lambda: self.export_button.config(state=tk.NORMAL))
    
    def process_video_thread(self):
        try:
            success = self.processor.process_video(
                self.video_path, 
                self.output_path,
                progress_callback=lambda value, message: self.root.after(0, self.update_progress, value, message)
            )
            
            if success:
                self.root.after(0, lambda: messagebox.showinfo("成功", "视频处理完成!"))
                self.root.after(0, lambda: self.preview_button.config(state=tk.NORMAL))
                self.root.after(0, lambda: self.export_button.config(state=tk.NORMAL))
            else:
                self.root.after(0, lambda: messagebox.showerror("错误", "视频处理失败"))
        except Exception as e:
            error_message = str(e)
            self.root.after(0, lambda error=error_message: messagebox.showerror("错误", f"处理过程中出错: {error}"))
        finally:
            self.root.after(0, lambda: self.process_button.config(state=tk.NORMAL))
    
    def toggle_preview(self):
        if self.preview_running:
            self.stop_preview()
            self.preview_button.config(text="预览")
        else:
            self.start_preview()
            self.preview_button.config(text="停止预览")
    
    def start_preview(self):
        if self.preview_thread and self.preview_thread.is_alive():
            return
        
        self.preview_running = True
        self.preview_thread = threading.Thread(target=self.preview_video)
        self.preview_thread.daemon = True
        self.preview_thread.start()
    
    def stop_preview(self):
        self.preview_running = False
        if self.preview_thread and self.preview_thread.is_alive():
            self.preview_thread.join(timeout=1.0)
    
    def preview_video(self):
        video_path = self.output_path if os.path.exists(self.output_path) else self.video_path
        if not os.path.exists(video_path):
            return
        
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return
        
        while self.preview_running:
            ret, frame = cap.read()
            if not ret:
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)  # 循环播放
                continue
            
            # 调整帧大小以适应画布
            canvas_width = self.preview_canvas.winfo_width()
            canvas_height = self.preview_canvas.winfo_height()
            
            if canvas_width > 1 and canvas_height > 1:  # 确保画布已经渲染
                frame_height, frame_width = frame.shape[:2]
                
                # 计算缩放比例
                scale = min(canvas_width / frame_width, canvas_height / frame_height)
                new_width = int(frame_width * scale)
                new_height = int(frame_height * scale)
                
                # 调整帧大小
                frame = cv2.resize(frame, (new_width, new_height))
                
                # 转换为RGB（从BGR）
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                
                # 转换为PhotoImage
                image = Image.fromarray(frame_rgb)
                photo = ImageTk.PhotoImage(image=image)
                
                # 在画布上显示
                self.preview_canvas.config(width=new_width, height=new_height)
                self.preview_canvas.create_image(new_width//2, new_height//2, image=photo)
                self.preview_canvas.image = photo  # 保持引用
            
            # 控制帧率
            time.sleep(0.03)  # 约30 FPS
        
        cap.release()

    def update_progress(self, value, message):
        self.progress_var.set(value)
        self.status_label.config(text=message)
    
    def start_processing(self):
        # 验证输入和输出路径
        if not self.video_path or not os.path.exists(self.video_path):
            messagebox.showerror("错误", "请选择有效的输入视频文件")
            return
        
        if not self.output_path:
            messagebox.showerror("错误", "请指定输出视频路径")
            return
        
        # 禁用处理按钮
        self.process_button.config(state=tk.DISABLED)
        
        # 更新状态
        self.status_label.config(text="准备处理...")
        self.progress_var.set(0)
        
        # 在新线程中处理视频
        self.processing_thread = threading.Thread(target=self.process_video_thread, daemon=True)
        self.processing_thread.start()
        
    def process_video_thread(self):
        try:
            success = self.processor.process_video(
                self.video_path, 
                self.output_path,
                progress_callback=lambda value, message: self.root.after(0, self.update_progress, value, message)
            )
            
            if success:
                self.root.after(0, lambda: messagebox.showinfo("成功", "视频处理完成!"))
                self.root.after(0, lambda: self.preview_button.config(state=tk.NORMAL))
                self.root.after(0, lambda: self.export_button.config(state=tk.NORMAL))
            else:
                self.root.after(0, lambda: messagebox.showerror("错误", "视频处理失败"))
        except Exception as e:
            error_message = str(e)
            self.root.after(0, lambda error=error_message: messagebox.showerror("错误", f"处理过程中出错: {error}"))
        finally:
            self.root.after(0, lambda: self.process_button.config(state=tk.NORMAL))
    
    def toggle_preview(self):
        if self.preview_running:
            self.stop_preview()
            self.preview_button.config(text="预览")
        else:
            self.start_preview()
            self.preview_button.config(text="停止预览")
    
    def start_preview(self):
        if self.preview_thread and self.preview_thread.is_alive():
            return
        
        self.preview_running = True
        self.preview_thread = threading.Thread(target=self.preview_video)
        self.preview_thread.daemon = True
        self.preview_thread.start()
    
    def stop_preview(self):
        self.preview_running = False
        if self.preview_thread and self.preview_thread.is_alive():
            self.preview_thread.join(timeout=1.0)
    
    def preview_video(self):
        video_path = self.output_path if os.path.exists(self.output_path) else self.video_path
        if not os.path.exists(video_path):
            return
        
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return
        
        while self.preview_running:
            ret, frame = cap.read()
            if not ret:
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)  # 循环播放
                continue
            
            # 调整帧大小以适应画布
            canvas_width = self.preview_canvas.winfo_width()
            canvas_height = self.preview_canvas.winfo_height()
            
            if canvas_width > 1 and canvas_height > 1:  # 确保画布已经渲染
                frame_height, frame_width = frame.shape[:2]
                
                # 计算缩放比例
                scale = min(canvas_width / frame_width, canvas_height / frame_height)
                new_width = int(frame_width * scale)
                new_height = int(frame_height * scale)
                
                # 调整帧大小
                frame = cv2.resize(frame, (new_width, new_height))
                
                # 转换为RGB（从BGR）
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                
                # 转换为PhotoImage
                image = Image.fromarray(frame_rgb)
                photo = ImageTk.PhotoImage(image=image)
                
                # 在画布上显示
                self.preview_canvas.config(width=new_width, height=new_height)
                self.preview_canvas.create_image(new_width//2, new_height//2, image=photo)
                self.preview_canvas.image = photo  # 保持引用
            
            # 控制帧率
            time.sleep(0.03)  # 约30 FPS
        
        cap.release()

if __name__ == "__main__":
    root = tk.Tk()
    app = VideoProcessorApp(root)
    root.mainloop()