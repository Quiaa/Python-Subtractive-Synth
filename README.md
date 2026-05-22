# 🎹 Python Polifonik Eksiltici Sentezleyici ve Sinyal Analiz Laboratuvarı

Sayısal Ses Dersi dönem projesi kapsamında Python ile sıfırdan geliştirilmiş; gerçek zamanlı (real-time) eksiltici (subtractive) sentezleyici, 6-sesli polifonik canlı performans motoru ve WAV tabanlı tersine mühendislik (ADSR/Frekans analizi) aracıdır.

Hazır bir ses motoru (audio engine) kullanılmamış, tüm sentezleme ve analiz işlemleri temel sinyal işleme (DSP) matematiği ile geliştirilmiştir.

## ✨ Temel Özellikler

Uygulama 3 ana modülden (sekmeden) oluşmaktadır:

### 1. Analiz ve Tasarım Modu (Sentezleyici Çekirdeği)
* **Osilatörler:** Harmonik açıdan zengin Testere Dişi (Sawtooth), Kare (Square) ve saf Sinüs (Sine) dalga üretimi.
* **ADSR Zarfı:** Sesin zaman içindeki şiddetini kontrol eden Attack, Decay, Sustain ve Release evrelerinin milisaniyelik hesabı.
* **Filtreleme:** İstenmeyen yüksek frekansları tıraşlayan Butterworth Alçak Geçiren Filtre (Low-Pass Filter).
* **Gerçek Zamanlı Görselleştirme:** Parametre değişimlerinin sese olan etkisini anlık gösteren Zaman Alanı (Dalga Formu) ve Frekans Alanı (FFT Spektrumu) grafikleri.
* **Fiziksel Modelleme Önayarları:** Akustik özelliklerine göre modellenmiş Keman, Piyano, Flüt, Bas ve Retro 8-bit hazır ses profilleri.

### 2. Canlı Performans Modu (Polifonik Akış)
* **Durum Makinesi (State Machine):** Ses paketlerini statik üretmek yerine, kesintisiz bir ses akışı (Audio Stream) üzerinde çalışan dinamik motor.
* **6-Ses Polifoni (Polyphony):** Aynı anda 6 farklı notayı (akoru) birbirini kesmeden çalabilme ve "Note Stealing" algoritması.
* **Klavye Entegrasyonu:** Bilgisayar klavyesini düşük gecikmeli (low-latency) bir MIDI kontrolcüye dönüştürme.

### 3. WAV Zarf Analizi (Tersine Mühendislik)
* **Envelope Follower (Zarf Takipçisi):** Dışarıdan yüklenen herhangi bir sesin mutlak değerini alıp 25 Hz kesimli filtreden geçirerek sesin genlik silüetini (ADSR) saniye cinsinden deşifre etme.
* **Spektral Analiz:** FFT dönüşümü ile sesin temel frekansını (F0), notasını ve osilatör tipini (harmonik yapıya bakarak) otomatik tespit etme.
* **Klonlama:** Analiz edilen sesi doğrudan sentezleyiciye aktararak birebir klonlama imkanı.

## 🛠️ Kullanılan Teknolojiler
* **Python 3.x**
* **NumPy:** Vektörel işlemler ve matris hesaplamaları.
* **SciPy:** Sinyal üretimi, FFT analizleri ve Butterworth filtre tasarımı.
* **Sounddevice:** Düşük gecikmeli, asenkron ses akışı (Audio Stream).
* **Matplotlib & Tkinter:** Veri görselleştirme ve modüler kullanıcı arayüzü (GUI).

## 🚀 Kurulum ve Çalıştırma

Projeyi bilgisayarınızda çalıştırmak için gerekli Python kütüphanelerini kurmanız yeterlidir:

```bash
# Gerekli kütüphaneleri yükleyin
pip install numpy scipy matplotlib sounddevice

# Uygulamayı başlatın
python subtractive_synth_gui.py
```
## 🎞️ Ekran Görüntüleri

Aşağıda uygulamanın 3 temel modülüne ait arayüz ve analiz çıktıları yer almaktadır:

### 🎛️ 1. Analiz ve Tasarım Modu (Sentezleyici Çekirdeği)
<p align="center">
  <img width="900" alt="Analiz ve Tasarım Modu" src="https://github.com/user-attachments/assets/e0007185-cc55-46d8-9cac-547ee167a5f9" />
</p>
<br>

### 🎹 2. Canlı Performans Modu (Polifonik Akış)
<p align="center">
  <img width="900" alt="Canlı Performans Modu" src="https://github.com/user-attachments/assets/34cc5ea2-d6f1-440a-b076-585a6b71678e" />
</p>
<br>

### 🔬 3. WAV Zarf Analizi (Tersine Mühendislik)
<p align="center">
  <img width="900" alt="WAV Zarf Analizi" src="https://github.com/user-attachments/assets/6754b927-bdde-4d3b-afbf-a5ba927e5413" />
</p>



---
<p align="center">
  <small><i>Bu proje, Sayısal Ses Sinyali İşleme prensiplerini uygulamalı olarak göstermek amacıyla hazırlanmıştır.</i></small>
</p>
