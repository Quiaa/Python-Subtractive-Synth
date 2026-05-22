import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import numpy as np
from scipy.signal import sawtooth, square, butter, lfilter, filtfilt
import sounddevice as sd
import time
from scipy.io import wavfile
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from scipy.signal import lfilter_zi

fs = 44100
playhead_line1 = None; playhead_line2 = None
start_time = 0; is_playing = False; last_generated_wave = None

KEY_MAPPING = {'a': 261.63, 'w': 277.18, 's': 293.66, 'e': 311.13, 'd': 329.63, 'f': 349.23, 't': 369.99, 'g': 392.00, 'y': 415.30, 'h': 440.00, 'u': 466.16, 'j': 493.88, 'k': 523.25}
NOTES = {"C3 (Do Bas)": 130.81, "E3 (Mi Bas)": 164.81, "A3 (La Bas)": 220.00, "C4 (Do)": 261.63, "D4 (Re)": 293.66, "E4 (Mi)": 329.63, "F4 (Fa)": 349.23, "G4 (Sol)": 392.00, "A4 (La)": 440.00, "B4 (Si)": 493.88, "C5 (Do İnce)": 523.25}
pressed_keys = set()

est_duration, est_freq, est_wave, est_cutoff, closest_note_name = 1.0, 440.0, "Sinüs (Sine)", 1000, "A4 (La)"

class RealTimeSynth:
    def __init__(self, fs=44100, max_voices=6):
        self.fs = fs
        self.max_voices = max_voices
        
        self.voices = [{'freq': 0.0, 'phase': 0.0, 'env_val': 0.0, 'state': 'IDLE'} for _ in range(max_voices)]
        
        self.b, self.a = butter(2, 1000/(fs/2), btype='low')
        self.zi = np.zeros(max(len(self.b), len(self.a)) - 1)
        
        self.attack, self.decay, self.sustain, self.release = 0.1, 0.1, 0.5, 0.1
        self.wave_type = "Sinüs (Sine)"
        
        self.stream = sd.OutputStream(samplerate=self.fs, channels=1, callback=self.audio_callback, blocksize=512)
        self.stream.start()

    def update_params(self, a, d, s, r, cutoff, wave_type):
        self.attack, self.decay, self.sustain, self.release = max(0.001, a), max(0.001, d), s, max(0.001, r)
        self.wave_type = wave_type
        self.b, self.a = butter(2, max(100, cutoff)/(self.fs/2), btype='low')

    def note_on(self, freq):
        for v in self.voices:
            if v['state'] == 'IDLE':
                v['freq'] = freq
                v['state'] = 'ATTACK'
                v['phase'] = 0.0
                return
                
        for v in self.voices:
            if v['state'] == 'RELEASE':
                v['freq'] = freq
                v['state'] = 'ATTACK'
                v['phase'] = 0.0
                return

    def note_off(self, freq):
        for v in self.voices:
            if v['freq'] == freq and v['state'] != 'IDLE':
                v['state'] = 'RELEASE'

    def audio_callback(self, outdata, frames, time_info, status):
        t = np.arange(frames) / self.fs
        mixed_sig = np.zeros(frames)
        
        for v in self.voices:
            if v['state'] == 'IDLE':
                continue
                
            phase_arr = 2 * np.pi * v['freq'] * t + v['phase']
            v['phase'] = (phase_arr[-1] + 2 * np.pi * v['freq'] / self.fs) % (2 * np.pi)

            if self.wave_type == "Testere Dişi (Sawtooth)": wave = sawtooth(phase_arr)
            elif self.wave_type == "Kare (Square)": wave = square(phase_arr)
            else: wave = np.sin(phase_arr)

            env = np.zeros(frames)
            for i in range(frames):
                if v['state'] == 'ATTACK':
                    v['env_val'] += 1.0 / (self.attack * self.fs)
                    if v['env_val'] >= 1.0:
                        v['env_val'] = 1.0
                        v['state'] = 'DECAY'
                elif v['state'] == 'DECAY':
                    v['env_val'] -= (1.0 - self.sustain) / (self.decay * self.fs)
                    if v['env_val'] <= self.sustain:
                        v['env_val'] = self.sustain
                        v['state'] = 'SUSTAIN'
                elif v['state'] == 'SUSTAIN':
                    pass 
                elif v['state'] == 'RELEASE':
                    v['env_val'] -= self.sustain / (self.release * self.fs)
                    if v['env_val'] <= 0.0:
                        v['env_val'] = 0.0
                        v['state'] = 'IDLE'
                env[i] = v['env_val']

            mixed_sig += wave * env

        sig_filt, self.zi = lfilter(self.b, self.a, mixed_sig, zi=self.zi)
        
        outdata[:] = (sig_filt * 0.3).reshape(-1, 1)

live_synth = RealTimeSynth(fs)

def generate_wave(freq, duration, a, d, s, r, cutoff, wave_type):
    t = np.linspace(0, duration, int(fs * duration), endpoint=False)
    if (a + d + r) >= duration: return np.zeros_like(t), np.zeros_like(t), t 
        
    if wave_type == "Testere Dişi (Sawtooth)": wave = sawtooth(2 * np.pi * freq * t)
    elif wave_type == "Kare (Square)": wave = square(2 * np.pi * freq * t)
    else: wave = np.sin(2 * np.pi * freq * t)
    
    a_samps, d_samps, r_samps = int(a * fs), int(d * fs), int(r * fs)
    env_a = np.linspace(0, 1, a_samps)
    env_d = np.linspace(1, s, d_samps)
    env_s = np.full(len(t) - (a_samps + d_samps + r_samps), s)
    env_r = np.linspace(s, 0, r_samps)
    envelope = np.concatenate([env_a, env_d, env_s, env_r])
    
    nyq = 0.5 * fs
    b, a_filt = butter(4, cutoff / nyq, btype='low', analog=False)
    return lfilter(b, a_filt, wave * envelope), envelope, t

def apply_preset(preset_type):
    if preset_type == "Retro":
        wave_combo.set("Kare (Square)"); note_combo.set("C4 (Do)"); duration_slider.set(1.0); attack_slider.set(0.01); decay_slider.set(0.1); sustain_slider.set(0.6); release_slider.set(0.1); cutoff_slider.set(5000)
    elif preset_type == "Flüt":
        wave_combo.set("Sinüs (Sine)"); note_combo.set("A4 (La)"); duration_slider.set(2.0); attack_slider.set(0.2); decay_slider.set(0.1); sustain_slider.set(0.8); release_slider.set(0.4); cutoff_slider.set(1200)
    elif preset_type == "Bas":
        wave_combo.set("Testere Dişi (Sawtooth)"); note_combo.set("A3 (La Bas)"); duration_slider.set(1.5); attack_slider.set(0.05); decay_slider.set(0.4); sustain_slider.set(0.2); release_slider.set(0.3); cutoff_slider.set(600)
    elif preset_type == "Piyano":
        wave_combo.set("Testere Dişi (Sawtooth)"); note_combo.set("C4 (Do)"); duration_slider.set(2.5); attack_slider.set(0.02); decay_slider.set(0.5); sustain_slider.set(0.2); release_slider.set(0.8); cutoff_slider.set(1000)
    elif preset_type == "Keman":
        wave_combo.set("Testere Dişi (Sawtooth)"); note_combo.set("G4 (Sol)"); duration_slider.set(3.0); attack_slider.set(0.4); decay_slider.set(0.1); sustain_slider.set(0.9); release_slider.set(0.5); cutoff_slider.set(2500)
    
    update_graph()

def update_graph(*args):
    duration, a, d, s, r = duration_slider.get(), attack_slider.get(), decay_slider.get(), sustain_slider.get(), release_slider.get()
    cutoff, wave_type, freq = cutoff_slider.get(), wave_combo.get(), NOTES[note_combo.get()]
    
    if (a + d + r) >= duration:
        ax1.clear(); ax2.clear(); canvas.draw(); return
        
    final_wave, envelope, t = generate_wave(freq, duration, a, d, s, r, cutoff, wave_type)
    fft_out, fft_freqs = np.abs(np.fft.rfft(final_wave)), np.fft.rfftfreq(len(final_wave), 1/fs)
    
    ax1.clear(); ax1.plot(t, final_wave, color='gray', alpha=0.8, linewidth=0.5); ax1.plot(t, envelope, color='red', linewidth=1.5); ax1.plot(t, -envelope, color='red', linewidth=1.5, alpha=0.5) 
    ax1.set_ylim(-1.1, 1.1); ax1.set_xlim(0, duration); ax1.set_title(f"Zaman Alanı: {wave_type}", fontsize=10); ax1.set_ylabel("Genlik"); ax1.grid(True)
    ax2.clear(); ax2.plot(fft_freqs, fft_out, color='purple', linewidth=1); ax2.set_xlim(0, 5000); ax2.set_title("Frekans Alanı (FFT)", fontsize=10); ax2.set_xlabel("Frekans (Hz)"); ax2.set_ylabel("Şiddet"); ax2.grid(True)
    
    global playhead_line1; playhead_line1 = ax1.axvline(x=0, color='blue', linewidth=2, linestyle='--'); playhead_line1.set_visible(False)
    fig.tight_layout(); canvas.draw()

def play_synth():
    global start_time, is_playing, last_generated_wave
    duration, a, d, s, r, cutoff = duration_slider.get(), attack_slider.get(), decay_slider.get(), sustain_slider.get(), release_slider.get(), cutoff_slider.get()
    wave_type, freq = wave_combo.get(), NOTES[note_combo.get()]
    final_wave, _, _ = generate_wave(freq, duration, a, d, s, r, cutoff, wave_type)
    last_generated_wave = final_wave 
    sd.play(final_wave, fs); start_time = time.time(); is_playing = True; playhead_line1.set_visible(True)
    animate_playhead(duration)

def animate_playhead(duration):
    global is_playing
    if not is_playing: return
    elapsed_time = time.time() - start_time
    if elapsed_time <= duration:
        playhead_line1.set_xdata([elapsed_time, elapsed_time]); canvas.draw_idle(); root.after(30, lambda: animate_playhead(duration))
    else: is_playing = False; playhead_line1.set_visible(False); canvas.draw_idle()

def save_audio():
    if last_generated_wave is None: return
    file_path = filedialog.asksaveasfilename(defaultextension=".wav", filetypes=[("WAV files", "*.wav")])
    if file_path: wavfile.write(file_path, fs, np.int16((last_generated_wave / np.max(np.abs(last_generated_wave))) * 32767))

def on_key_press(event):
    key = event.keysym.lower()
    if key in KEY_MAPPING and key not in pressed_keys and notebook.index(notebook.select()) == 1:
        pressed_keys.add(key)
        
        live_synth.update_params(
            attack_slider.get(), decay_slider.get(), sustain_slider.get(), release_slider.get(),
            cutoff_slider.get(), wave_combo.get()
        )
        
        live_synth.note_on(KEY_MAPPING[key])
        
        if key in key_labels: key_labels[key].config(bg="green", fg="white")

def on_key_release(event):
    key = event.keysym.lower()
    if key in pressed_keys:
        pressed_keys.remove(key)
        
        live_synth.note_off(KEY_MAPPING[key])
        
        if key in key_labels: 
            is_black = key in ['w','e','t','y','u']
            key_labels[key].config(bg="black" if is_black else "white", fg="white" if is_black else "black")

def load_and_analyze_wav():
    global est_a, est_d, est_s, est_r, est_duration, est_freq, est_wave, est_cutoff, closest_note_name
    file_path = filedialog.askopenfilename(filetypes=[("WAV files", "*.wav")], title="Analiz İçin WAV Seç")
    if not file_path: return
    
    fs_wav, audio = wavfile.read(file_path)
    if len(audio.shape) > 1: audio = audio.mean(axis=1) 
    audio = audio / np.max(np.abs(audio)) 
    t_wav = np.arange(len(audio)) / fs_wav
    
    est_duration = len(audio) / fs_wav
    
    nyq = 0.5 * fs_wav
    b, a_filt = butter(2, 25.0 / nyq, btype='low') 
    envelope = filtfilt(b, a_filt, np.abs(audio))
    envelope = np.clip(envelope / np.max(envelope), 0, 1)
    
    threshold_env = 0.02
    active_indices = np.where(envelope > threshold_env)[0]
    start_idx = active_indices[0] if len(active_indices) > 0 else 0
    end_idx = active_indices[-1] if len(active_indices) > 0 else len(envelope)-1
    
    peak_idx = np.argmax(envelope)
    est_a = (peak_idx - start_idx) / fs_wav
    
    post_peak_env = envelope[peak_idx:end_idx]
    pp_len = len(post_peak_env)
    
    if pp_len > 0:
        sustain_region = post_peak_env[int(pp_len * 0.3):int(pp_len * 0.7)]
        est_s = np.mean(sustain_region) if len(sustain_region) > 0 else 0.0
    else:
        est_s = 0.0

    decay_threshold = est_s + 0.05
    decay_points = np.where(post_peak_env <= decay_threshold)[0]
    
    if len(decay_points) > 0:
        decay_end_idx_relative = decay_points[0]
        est_d = decay_end_idx_relative / fs_wav
        sustain_start_idx = peak_idx + decay_end_idx_relative
    else:
        est_d = 0.1 
        sustain_start_idx = peak_idx
        

    release_threshold = max(threshold_env, est_s * 0.8)
    sustain_points = np.where(envelope[:end_idx] > release_threshold)[0]
    
    if len(sustain_points) > 0:
        release_start_idx = sustain_points[-1]
    else:
        release_start_idx = sustain_start_idx
        
    release_start_idx = max(sustain_start_idx, release_start_idx)
    
    est_r = (end_idx - release_start_idx) / fs_wav
    est_r = max(0.01, est_r) # Eksi veya sıfır olmasını engelle
    
    window = np.hanning(len(audio))
    fft_out = np.abs(np.fft.rfft(audio * window))
    fft_freqs = np.fft.rfftfreq(len(audio), 1/fs_wav)
    
    peak_freq_idx = np.argmax(fft_out)
    est_freq = fft_freqs[peak_freq_idx]
    closest_note_name = min(NOTES.keys(), key=lambda k: abs(NOTES[k] - est_freq))
    
    mag_1f0 = fft_out[peak_freq_idx]
    idx_2f0 = np.argmin(np.abs(fft_freqs - 2*est_freq))
    idx_3f0 = np.argmin(np.abs(fft_freqs - 3*est_freq))
    mag_2f0 = fft_out[idx_2f0] if idx_2f0 < len(fft_out) else 0
    mag_3f0 = fft_out[idx_3f0] if idx_3f0 < len(fft_out) else 0
    
    peaks = fft_freqs[fft_out > (np.max(fft_out) * 0.1)]
    if len(peaks) <= 2: est_wave = "Sinüs (Sine)"
    elif mag_2f0 < (mag_1f0 * 0.05) and mag_3f0 > (mag_1f0 * 0.05): est_wave = "Kare (Square)"
    else: est_wave = "Testere Dişi (Sawtooth)"
        
    threshold_fft = mag_1f0 * 0.02
    active_freqs = fft_freqs[fft_out > threshold_fft]
    detected_cutoff = np.max(active_freqs) * 1.25 if len(active_freqs) > 0 else 1000
    est_cutoff = min(5000, max(100, detected_cutoff))
    
    info_text = (
        f"Tahmin Edilen Kaynak: {est_wave} | Nota: {closest_note_name} ({est_freq:.1f} Hz)\n"
        f"Süre: {est_duration:.2f} sn | Filtre Cutoff: ~{est_cutoff:.0f} Hz\n"
        f"ADSR: Attack {est_a:.2f}s | Decay {est_d:.2f}s | Sustain %{est_s*100:.0f} | Release {est_r:.2f}s"
    )
    adsr_results_lbl.config(text=info_text)
    
    ax3.clear()
    ax3.plot(t_wav, audio, color='gray', alpha=0.5, label="Orijinal Ses")
    ax3.plot(t_wav, envelope, color='red', linewidth=2, label="Çıkarılan Zarf (Envelope)")
    
    ax3.axvline(x=start_idx/fs_wav, color='black', linestyle='--', alpha=0.5)
    ax3.axvline(x=peak_idx/fs_wav, color='blue', linestyle='--', alpha=0.5, label="Zirve (Attack Bitişi)")
    ax3.axvline(x=sustain_start_idx/fs_wav, color='green', linestyle='--', alpha=0.5, label="Decay Bitişi")
    ax3.axvline(x=release_start_idx/fs_wav, color='orange', linestyle='--', alpha=0.5, label="Release Başlangıcı")
    
    ax3.set_title("WAV Tersine Mühendislik Analizi", fontsize=12)
    ax3.set_xlabel("Zaman (sn)"); ax3.set_ylabel("Genlik")
    ax3.legend(loc="upper right", fontsize=8); ax3.grid(True)
    canvas3.draw()

def apply_extracted_adsr():
    attack_slider.set(round(est_a, 2))
    decay_slider.set(round(est_d, 2))
    sustain_slider.set(round(est_s, 2))
    release_slider.set(round(est_r, 2))
    
    duration_slider.set(round(est_duration, 1))
    cutoff_slider.set(int(est_cutoff))
    wave_combo.set(est_wave)
    note_combo.set(closest_note_name)
    
    messagebox.showinfo("Başarılı", "Tüm analiz değerleri sentezleyiciye aktarıldı!\nSekme 1'e dönüp birebir aynı sesi çalabilirsiniz.")
    update_graph()

# --- ARAYÜZ (GUI) TASARIMI ---
root = tk.Tk()
root.title("Gelişmiş Sayısal Sentezleyici Projesi")
root.geometry("1000x750")

root.bind('<KeyPress>', on_key_press)
root.bind('<KeyRelease>', on_key_release)

notebook = ttk.Notebook(root)
notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

tab1 = ttk.Frame(notebook); tab2 = ttk.Frame(notebook); tab3 = ttk.Frame(notebook)
notebook.add(tab1, text="1. Analiz ve Tasarım Modu")
notebook.add(tab2, text="2. Canlı Çalma (Klavye)")
notebook.add(tab3, text="3. WAV Zarf Analizi (Tersine Mühendislik)")

# ====== SEKME 1: ANALİZ MODU ======
left_frame = tk.Frame(tab1); left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=10)
tk.Label(left_frame, text="HAZIR SESLER", font=("Helvetica", 10, "bold")).pack(pady=(0,5))
preset_frame = tk.Frame(left_frame); preset_frame.pack(pady=5)
# İlk Satır Butonlar
tk.Button(preset_frame, text="Retro", command=lambda: apply_preset("Retro"), width=6).grid(row=0, column=0, padx=2, pady=2)
tk.Button(preset_frame, text="Flüt", command=lambda: apply_preset("Flüt"), width=6).grid(row=0, column=1, padx=2, pady=2)
tk.Button(preset_frame, text="Bas", command=lambda: apply_preset("Bas"), width=6).grid(row=0, column=2, padx=2, pady=2)
# İkinci Satır Butonlar (YENİ)
tk.Button(preset_frame, text="Piyano", command=lambda: apply_preset("Piyano"), width=6).grid(row=1, column=0, padx=2, pady=2)
tk.Button(preset_frame, text="Keman", command=lambda: apply_preset("Keman"), width=6).grid(row=1, column=1, padx=2, pady=2)

tk.Label(left_frame, text="OSİLATÖR VE NOTA", font=("Helvetica", 10, "bold")).pack(pady=(10,5))
wave_combo = ttk.Combobox(left_frame, values=["Testere Dişi (Sawtooth)", "Kare (Square)", "Sinüs (Sine)"], state="readonly")
wave_combo.current(0); wave_combo.bind("<<ComboboxSelected>>", update_graph); wave_combo.pack()
note_combo = ttk.Combobox(left_frame, values=list(NOTES.keys()), state="readonly")
note_combo.set("A4 (La)"); note_combo.bind("<<ComboboxSelected>>", update_graph); note_combo.pack(pady=5)
duration_slider = tk.Scale(left_frame, from_=0.2, to=3.0, resolution=0.1, orient="horizontal", label="Süre (sn)", command=update_graph); duration_slider.set(1.0); duration_slider.pack()

tk.Label(left_frame, text="ZARF VE FİLTRE", font=("Helvetica", 10, "bold")).pack(pady=(10,5))
attack_slider = tk.Scale(left_frame, from_=0.01, to=1.0, resolution=0.01, orient="horizontal", label="Attack", command=update_graph); attack_slider.set(0.05); attack_slider.pack()
decay_slider = tk.Scale(left_frame, from_=0.01, to=1.0, resolution=0.01, orient="horizontal", label="Decay", command=update_graph); decay_slider.set(0.2); decay_slider.pack()
sustain_slider = tk.Scale(left_frame, from_=0.0, to=1.0, resolution=0.01, orient="horizontal", label="Sustain", command=update_graph); sustain_slider.set(0.5); sustain_slider.pack()
release_slider = tk.Scale(left_frame, from_=0.01, to=1.0, resolution=0.01, orient="horizontal", label="Release", command=update_graph); release_slider.set(0.3); release_slider.pack()
cutoff_slider = tk.Scale(left_frame, from_=100, to=5000, resolution=50, orient="horizontal", label="Filtre (Hz)", command=update_graph); cutoff_slider.set(2000); cutoff_slider.pack(pady=(0, 15))

btn_frame = tk.Frame(left_frame); btn_frame.pack(pady=10)
tk.Button(btn_frame, text="SESİ ÇAL", command=play_synth, bg="green", fg="white", font=("Helvetica", 10, "bold")).grid(row=0, column=0, padx=5)
tk.Button(btn_frame, text="KAYDET", command=save_audio, bg="blue", fg="white", font=("Helvetica", 10, "bold")).grid(row=0, column=1, padx=5)

right_frame = tk.Frame(tab1); right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
fig = Figure(figsize=(6, 6), dpi=100); ax1 = fig.add_subplot(211); ax2 = fig.add_subplot(212)
canvas = FigureCanvasTkAgg(fig, master=right_frame); canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

# ====== SEKME 2: CANLI ÇALMA MODU ======
tk.Label(tab2, text="🎹 KLAVYE İLE CANLI PERFORMANS 🎹", font=("Helvetica", 16, "bold"), pady=30).pack()
tk.Label(tab2, text="(Canlı çalarken hatalı tetiklenmeleri önlemek için klavyeniz sadece bu sekme açıkken çalışır)", font=("Helvetica", 11)).pack(pady=10)
keyboard_frame = tk.Frame(tab2); keyboard_frame.pack(pady=40)
keys_layout = [("W (C#)", "w"), ("E (D#)", "e"), ("T (F#)", "t"), ("Y (G#)", "y"), ("U (A#)", "u"), ("A (Do)", "a"), ("S (Re)", "s"), ("D (Mi)", "d"), ("F (Fa)", "f"), ("G (Sol)", "g"), ("H (La)", "h"), ("J (Si)", "j"), ("K (Do)", "k")]
key_labels = {}
for text, key_code in keys_layout:
    lbl = tk.Label(keyboard_frame, text=text, width=8, height=4, relief="raised", bg="white", font=("Helvetica", 10, "bold"))
    if key_code in ['w', 'e', 't', 'y', 'u']:
        lbl.config(bg="black", fg="white", height=3); lbl.pack(side=tk.LEFT, padx=2, pady=(0, 20))
    else: lbl.pack(side=tk.LEFT, padx=2)
    key_labels[key_code] = lbl

# ====== SEKME 3: WAV ANALİZ (TERSİNE MÜHENDİSLİK) ======
top_frame_tab3 = tk.Frame(tab3); top_frame_tab3.pack(fill=tk.X, pady=10, padx=20)
tk.Label(top_frame_tab3, text="WAV dosyasını yükleyin. Sistem, zarf takipçisi (Envelope Follower) algoritması ile sesin ADSR parametrelerini çıkaracaktır.", font=("Helvetica", 11)).pack(pady=5)
tk.Button(top_frame_tab3, text="WAV DOSYASI YÜKLE VE ANALİZ ET", command=load_and_analyze_wav, bg="orange", font=("Helvetica", 11, "bold"), pady=5).pack(pady=10)

adsr_results_lbl = tk.Label(top_frame_tab3, text="Bekleniyor... Lütfen bir dosya yükleyin.", font=("Helvetica", 12, "bold"), fg="darkblue")
adsr_results_lbl.pack(pady=10)

tk.Button(top_frame_tab3, text="↓ DEĞERLERİ SENTEZLEYİCİYE AKTAR ↓", command=apply_extracted_adsr, bg="lightblue", font=("Helvetica", 10, "bold")).pack(pady=5)

graph_frame_tab3 = tk.Frame(tab3); graph_frame_tab3.pack(fill=tk.BOTH, expand=True)
fig3 = Figure(figsize=(8, 4), dpi=100); ax3 = fig3.add_subplot(111)
canvas3 = FigureCanvasTkAgg(fig3, master=graph_frame_tab3); canvas3.get_tk_widget().pack(fill=tk.BOTH, expand=True)

update_graph()
root.mainloop()