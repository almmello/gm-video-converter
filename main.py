# main.py

import os
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import subprocess
import datetime
import imageio_ffmpeg as ffmpeg
from threading import Thread

# Pasta de saída
OUTPUT_DIR = "output"

class VideoConverterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("GM Video Converter")

        self.video_info = {}
        self.input_file = None
        self.create_widgets()

    def create_widgets(self):
        frame = tk.Frame(self.root)
        frame.pack(pady=10, padx=10)

        self.select_file_button = tk.Button(frame, text="Selecionar Arquivo", command=self.select_file, bg="blue", fg="white")
        self.select_file_button.grid(row=0, column=0, columnspan=3, pady=5)

        self.resolution_label = tk.Label(frame, text="Resolução: -")
        self.resolution_label.grid(row=1, column=0, columnspan=3, sticky="w")

        self.bitrate_label = tk.Label(frame, text="Bitrate: -")
        self.bitrate_label.grid(row=2, column=0, columnspan=3, sticky="w")

        self.duration_label = tk.Label(frame, text="Duração: -")
        self.duration_label.grid(row=3, column=0, columnspan=3, sticky="w")

        self.size_label = tk.Label(frame, text="Tamanho Atual: -")
        self.size_label.grid(row=4, column=0, columnspan=3, sticky="w")

        self.target_size_label = tk.Label(frame, text="Tamanho Estimado: -")
        self.target_size_label.grid(row=5, column=0, columnspan=3, sticky="w")

        tk.Label(frame, text="Resolução:").grid(row=6, column=0, sticky="w")
        self.resolution_slider = ttk.Scale(frame, from_=480, to=1920, orient="horizontal", command=self.update_target_size)
        self.resolution_slider.grid(row=6, column=1, padx=5)
        self.resolution_value = tk.Label(frame, text="-")
        self.resolution_value.grid(row=6, column=2, sticky="w")

        tk.Label(frame, text="CRF:").grid(row=7, column=0, sticky="w")
        self.crf_combobox = ttk.Combobox(frame, values=["Não usar", 18, 20, 23, 26, 28], state="readonly")
        self.crf_combobox.grid(row=7, column=1, padx=5)
        self.crf_combobox.bind("<<ComboboxSelected>>", self.update_crf_behavior)
        self.crf_combobox.set("Não usar")

        tk.Label(frame, text="Bitrate (kbps):").grid(row=8, column=0, sticky="w")
        self.bitrate_slider = ttk.Scale(frame, from_=500, to=5000, orient="horizontal", command=self.update_target_size)
        self.bitrate_slider.grid(row=8, column=1, padx=5)
        self.bitrate_value = tk.Label(frame, text="-")
        self.bitrate_value.grid(row=8, column=2, sticky="w")

        self.progress = ttk.Progressbar(self.root, orient="horizontal", mode="determinate", length=300)
        self.progress.pack(pady=10)

        self.convert_button = tk.Button(self.root, text="Converter", command=self.start_conversion_thread, bg="green", fg="white", state="disabled")
        self.convert_button.pack(pady=10)

    def select_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("Arquivos de Vídeo", "*.mp4;*.mov;*.mkv;*.avi")])
        if file_path:
            self.input_file = file_path
            self.load_file()

    def load_file(self):
        if not self.input_file or not os.path.exists(self.input_file):
            messagebox.showerror("Erro", f"Arquivo '{self.input_file}' não encontrado.")
            return
        
        try:
            self.video_info = self.get_video_info(self.input_file)
            if self.video_info:
                self.resolution_label.config(text=f"Resolução: {self.video_info['resolution']}")
                self.bitrate_label.config(text=f"Bitrate: {self.video_info['bitrate']} kbps")
                self.duration_label.config(text=f"Duração: {self.video_info['duration']} segundos")
                self.size_label.config(text=f"Tamanho Atual: {self.video_info['size']} MB")

                self.resolution_slider.set(int(self.video_info['resolution'].split('x')[1]))
                self.bitrate_slider.set(self.video_info['bitrate'])

                self.enable_conversion_controls()
                self.update_target_size()
        except Exception as e:
            self.log_error(e)

    def get_video_info(self, file_path):
        file_path = os.path.abspath(file_path)
        ffmpeg_path = ffmpeg.get_ffmpeg_exe()
        command = [ffmpeg_path, "-i", file_path]
        result = subprocess.run(command, stderr=subprocess.PIPE, stdout=subprocess.DEVNULL, universal_newlines=True)
        if result.returncode != 0 and "At least one output file must be specified" not in result.stderr:
            raise FileNotFoundError(f"Erro ao executar o FFmpeg: {result.stderr}")

        resolution = "Unknown"
        bitrate = 0
        duration = 0
        for line in result.stderr.split("\n"):
            if "Video:" in line:
                resolution = line.split(",")[2].strip().split(" ")[0]
            if "bitrate:" in line:
                bitrate = int(line.split("bitrate:")[1].strip().split(" ")[0])
            if "Duration:" in line:
                duration_data = line.split(",")[0].split("Duration:")[1].strip()
                hours, minutes, seconds = map(float, duration_data.split(":"))
                duration = int(hours * 3600 + minutes * 60 + seconds)
        size = os.path.getsize(file_path) / (1024 * 1024)  # Tamanho em MB
        return {"resolution": resolution, "bitrate": bitrate, "duration": duration, "size": round(size, 2)}

    def enable_conversion_controls(self):
        self.resolution_slider.config(state="normal")
        self.crf_combobox.config(state="readonly")
        self.bitrate_slider.config(state="normal")
        self.convert_button.config(state="normal")

    def update_target_size(self, *args):
        self.resolution_value.config(text=str(int(self.resolution_slider.get())))
        self.bitrate_value.config(text=str(int(self.bitrate_slider.get())))

        resolution_factor = self.resolution_slider.get() / int(self.video_info['resolution'].split('x')[1])
        bitrate = self.bitrate_slider.get()
        duration = self.video_info['duration']

        crf = self.crf_combobox.get()
        if crf != "Não usar":
            estimated_size = ((23 - int(crf)) * duration * resolution_factor) / 50
        else:
            estimated_size = (bitrate * 1000 * duration) / (8 * 1024 * 1024) * resolution_factor

        self.target_size_label.config(text=f"Tamanho Estimado: {round(estimated_size, 2)} MB")

    def update_crf_behavior(self, event):
        crf = self.crf_combobox.get()
        if crf != "Não usar":
            self.bitrate_slider.config(state="disabled")
        else:
            self.bitrate_slider.config(state="normal")

        self.update_target_size()

    def start_conversion_thread(self):
        thread = Thread(target=self.convert_video)
        thread.start()

    def convert_video(self):
        resolution = int(self.resolution_slider.get())
        crf = self.crf_combobox.get()
        bitrate = int(self.bitrate_slider.get()) if crf == "Não usar" else None

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = os.path.join(OUTPUT_DIR, f"{os.path.splitext(os.path.basename(self.input_file))[0]}_res-{resolution}_crf-{crf if crf != 'Não usar' else bitrate}k_{timestamp}.mp4")
        os.makedirs(OUTPUT_DIR, exist_ok=True)

        ffmpeg_path = ffmpeg.get_ffmpeg_exe()
        scale_resolution = f"scale=-2:{(resolution // 2) * 2}"  # Garantir múltiplo de 2
        command = [
            ffmpeg_path,
            "-i", os.path.abspath(self.input_file),
            "-vf", scale_resolution,
            "-c:v", "libx264",
        ]

        if crf != "Não usar":
            command.extend(["-crf", str(crf)])
        else:
            command.extend(["-b:v", f"{bitrate}k"])

        command.extend(["-y", output_file])

        process = subprocess.Popen(command, stderr=subprocess.PIPE, stdout=subprocess.PIPE, text=True, universal_newlines=True)

        total_duration = self.video_info['duration']
        for line in process.stderr:
            if "time=" in line:
                time_str = line.split("time=")[1].split(" ")[0]
                hours, minutes, seconds = map(float, time_str.split(":"))
                elapsed_time = int(hours * 3600 + minutes * 60 + seconds)
                progress = (elapsed_time / total_duration) * 100
                self.progress['value'] = progress
                self.root.update_idletasks()

        process.wait()
        if process.returncode != 0:
            self.log_error(process.stderr.read())
            messagebox.showerror("Erro", "Erro na conversão! Verifique o log de erros.")
        else:
            messagebox.showinfo("Sucesso", f"Vídeo convertido e salvo em: {output_file}")

    def log_error(self, error):
        with open("error_log.txt", "a", encoding="utf-8") as log_file:
            log_file.write(f"[{datetime.datetime.now()}] {error}\n")
        messagebox.showerror("Erro", f"Um erro ocorreu. Detalhes salvos em 'error_log.txt'.")

if __name__ == "__main__":
    root = tk.Tk()
    app = VideoConverterApp(root)
    root.mainloop()
