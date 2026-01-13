# 🚀 Setup Guide - Research & Publishing Machine

## Hızlı Başlangıç (5 Dakika)

### 1. Gereksinimler

**Yazılım:**
- Python 3.11+ ([İndir](https://www.python.org/downloads/))
- LaTeX (TeX Live veya MiKTeX)
  - Windows: [MiKTeX](https://miktex.org/download)
  - macOS: `brew install --cask mactex`
  - Linux: `sudo apt-get install texlive-full`

**API Keys (Gerekli):**
- [Anthropic API Key](https://console.anthropic.com/) (Claude)
- [Google API Key](https://aistudio.google.com/app/apikey) (Gemini)
- [Tavily API Key](https://tavily.com/) (V2 mode için - opsiyonel)

### 2. Kurulum

```bash
# 1. Repo'yu klonla (veya ZIP indir)
cd research-project-llm

# 2. Virtual environment oluştur
python -m venv venv

# Windows:
venv\Scripts\activate

# macOS/Linux:
source venv/bin/activate

# 3. Dependencies yükle
pip install -r requirements.txt

# 4. .env dosyası oluştur
cp .env.example .env
```

### 3. API Keys Yapılandırması

`.env` dosyasını düzenle:

```bash
# .env dosyasını not defteri ile aç ve API key'leri yapıştır:

ANTHROPIC_API_KEY=sk-ant-api03-xxxxx...
GOOGLE_API_KEY=AIzaSyxxxxx...
TAVILY_API_KEY=tvly-xxxxx...  # Opsiyonel (V2 mode için)
```

**NOT:**
- V1 (offline) mode için sadece ANTHROPIC_API_KEY ve GOOGLE_API_KEY yeterli
- V2 (internet) mode için TAVILY_API_KEY de gerekli

### 4. Test Et

```bash
# Hızlı test (offline mode)
python test_simple.py
```

Eğer hata almazsan ✅ kurulum tamam!

### 5. Uygulamayı Başlat

```bash
streamlit run app.py
```

Tarayıcında aç: http://localhost:8501

---

## 🐛 Yaygın Sorunlar ve Çözümleri

### Problem: "pdflatex not found"

**Çözüm:** LaTeX kurulu değil.

**Windows:**
```bash
# MiKTeX indir ve kur: https://miktex.org/download
# Kurulumdan sonra terminal'i yeniden başlat
```

**macOS:**
```bash
brew install --cask mactex
```

**Linux:**
```bash
sudo apt-get install texlive-full
```

### Problem: "poppler not found" (pdf2image hatası)

**Çözüm:** Poppler kurulu değil.

**Windows:**
1. [Poppler indir](https://github.com/oschwartz10612/poppler-windows/releases)
2. ZIP'i çıkar (örn: `C:\poppler`)
3. PATH'e ekle: `C:\poppler\Library\bin`

**macOS:**
```bash
brew install poppler
```

**Linux:**
```bash
sudo apt-get install poppler-utils
```

### Problem: "API key not configured"

**Çözüm:** `.env` dosyası yok veya yanlış formatlanmış.

1. `.env.example` dosyasını kopyala → `.env` olarak kaydet
2. API key'leri tırnak işareti OLMADAN yapıştır:
   ```
   DOĞRU: ANTHROPIC_API_KEY=sk-ant-xxx
   YANLIŞ: ANTHROPIC_API_KEY="sk-ant-xxx"
   ```

### Problem: Import errors

**Çözüm:** Virtual environment aktif değil veya dependencies kurulmamış.

```bash
# Virtual environment aktif et
venv\Scripts\activate  # Windows
source venv/bin/activate  # macOS/Linux

# Dependencies yeniden kur
pip install -r requirements.txt
```

---

## 📋 Sistem Gereksinimleri

### Minimum
- CPU: 2 çekirdek
- RAM: 4 GB
- Disk: 2 GB boş alan (LaTeX kurulumu için)
- İnternet: API çağrıları için

### Önerilen
- CPU: 4+ çekirdek
- RAM: 8+ GB
- SSD disk
- İnternet: Stabil bağlantı (V2 mode için)

---

## 🔧 Gelişmiş Yapılandırma

### Config Ayarları (.env)

```bash
# Model seçimi
CLAUDE_MODEL=claude-sonnet-4-5-20250929
GEMINI_MODEL=gemini-1.5-pro-latest

# Debate parametreleri
MAX_ROUNDS=3                    # Maksimum tur sayısı (1-5)
CONVERGENCE_THRESHOLD=0.95      # Mutabakat eşiği (0.85-0.99)

# QA ayarları
QA_THRESHOLD=75                 # PDF onay puanı (60-95)
MAX_PDF_REGENERATIONS=2         # Max regeneration sayısı

# LaTeX ayarları
LATEX_TIMEOUT=30                # Compile timeout (saniye)
MAX_LATEX_RETRIES=3             # Max retry sayısı

# Varsayılan mod
DEFAULT_RESEARCH_MODE=auto      # auto/internet/offline
```

### Logging

Log dosyaları: `./output/logs/`

Detaylı logging için:
```python
from src.workflow import setup_logging
setup_logging(log_file="./output/logs/debug.log")
```

---

## 🐳 Docker ile Çalıştırma

### Build ve Run

```bash
# Build image
docker-compose build

# Start container
docker-compose up -d

# Logları izle
docker-compose logs -f
```

### Erişim

- UI: http://localhost:8501
- PDF'ler: `./output/pdfs/`
- Loglar: `./output/logs/`

### Stop

```bash
docker-compose down
```

---

## 🧪 Test Senaryoları

### Test 1: Offline Mode (Hızlı)

```bash
python test_simple.py
```

Beklenen süre: ~2 dakika

### Test 2: Internet Mode (Tavily)

```python
from src import run_research

final_state = run_research(
    topic="Latest AI news in 2024",
    research_mode="internet",
    max_rounds=2
)

print(f"PDF: {final_state.pdf_path}")
```

Beklenen süre: ~3-4 dakika

### Test 3: Streamlit UI

```bash
streamlit run app.py
```

1. Soruyu gir: "What is quantum computing?"
2. Mode seç: "offline"
3. "Araştır" butonuna tıkla
4. PDF'i indir

---

## 📊 Performans İpuçları

### Hızlandırma

1. **Offline mode kullan**: V2'den 30% daha hızlı
2. **Max rounds azalt**: 1-2 tur yeterli basit sorular için
3. **Threshold düşür**: 0.90'a çek (95 yerine)

### Maliyet Azaltma

1. **V1 mode tercih et**: Tavily ücretsiz tier'ı hızlı biter
2. **Max rounds sınırla**: Her tur ek API çağrısı
3. **QA threshold yükselt**: Daha az regeneration

### Kalite Artırma

1. **Max rounds artır**: 4-5'e çıkar
2. **Threshold yükselt**: 0.97'ye çık
3. **V2 mode kullan**: Güncel kaynaklarla ground et

---

## 🆘 Destek

### Hata Raporlama

GitHub Issues: [Yeni Issue Oluştur]

Lütfen ekleyin:
- Hata mesajı
- Python versiyonu (`python --version`)
- İşletim sistemi
- `.env` dosyası (API key'ler silinmiş olarak)

### Debug Modu

```python
import logging
logging.basicConfig(level=logging.DEBUG)

from src import run_research
# ... kodunuz
```

---

## ✅ Kurulum Checklist

- [ ] Python 3.11+ kurulu
- [ ] LaTeX kurulu (`pdflatex --version` çalışıyor)
- [ ] Poppler kurulu (Windows için)
- [ ] Virtual environment oluşturuldu
- [ ] Dependencies yüklendi (`pip install -r requirements.txt`)
- [ ] `.env` dosyası oluşturuldu
- [ ] API key'ler yapılandırıldı
- [ ] `test_simple.py` başarıyla çalıştı
- [ ] Streamlit UI açılıyor

Hepsi ✅ ise **SİSTEM HAZIR!** 🎉

---

**Başarılı kurulum dilekleriyle!**

*Truth = A ∩ B*
