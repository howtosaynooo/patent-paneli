# Patent Paneli – Trendyol Kategori & Türk Patent Marka Kontrolü

Bu küçük web uygulaması ile:

- Trendyol kategori + gender kombinasyonlarını tarayıp, içinde ürün olanları bulursun.
- Bu kategorilerde görünen marka isimlerini toplayıp, Türk Patent sitesinde marka tescil kontrolü yaparsın.
- Sonuçları bir web panelinden takip eder, canlı logları izler ve `output.xlsx` olarak indirirsin.

## Bileşenler

- `panel.py`: Flask tabanlı kontrol paneli. Ayarları yönetir, işleri başlatır ve durum/log bilgisini gösterir.
- `category_finder.py`: Trendyol API’sini kullanarak (kategori, gender) çiftlerini tarar ve ürün bulunan çiftleri `cache/categories_with_products.txt` içine yazar.
- `patent_worker.py`: Bu kategori listesini okur, her kategori için markaları çeker, Türk Patent’te arama yapar ve sonucu `output.xlsx` dosyasına yazar.
- `templates/panel.html`: Koyu temalı, canlı progress bar ve log görüntüleyicili web arayüzü.

## Kurulum

1. Depoya gir:

```bash
cd /Users/emir/Documents/2parcaliprog
```

2. (İsteğe bağlı) sanal ortam oluştur ve aktif et:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

3. Python bağımlılıklarını kur:

```bash
pip install -r requirements.txt
```

4. Selenium için:

- Firefox yüklü olmalı.
- `geckodriver` PATH içinde olmalı.

macOS + Homebrew için örnek:

```bash
brew install firefox geckodriver
```

## Paneli Çalıştırma

```bash
cd /Users/emir/Documents/2parcaliprog
source .venv/bin/activate  # varsa
python3 panel.py
```

Ardından tarayıcıdan:

- `http://127.0.0.1:5000` adresine git.

## Panelden Kullanım Akışı

1. **Ayarları Yap**
   - `Kategori Aralığı`: Başlangıç / Bitiş kategori ID’lerini gir.
   - `Gender Değerleri`: Virgülle ayrılmış gender listesi (ör. `1,2,3,12`).
   - `Patent Worker Ayarları`:
     - Worker sayısı (kaç adet headless Firefox açılsın)
     - Excel kayıt aralığı (kaç marka sorgusunda bir `output.xlsx` güncellensin).
   - **Ayarları Kaydet** butonuna bas.

2. **Kategori Tarama (category_finder)**
   - `category_finder'ı Başlat` butonuna bas.
   - Panelde:
     - Çalışma durumu (`Çalışıyor / Beklemede`)
     - Kaç kategori tarandığı ve kaç (kategori, gender) çiftinin bulunduğu
     - Canlı log (son satırlar) gösterilir.

3. **Patent Kontrolü (patent_worker)**
   - `patent_worker'ı Başlat` butonuna bas.
   - Panelde:
     - İşlenen kategori çifti sayısı
     - Toplam işlenen marka sayısı
     - Canlı log (Türk Patent sonuçları, hatalar vs.) gösterilir.

4. **Sonuçları İndir**
   - `output.xlsx'i indir` butonuyla anlık üretilen Excel dosyasını indirebilirsin.

## Doğrudan Komut Satırından Çalıştırma

Paneli kullanmak istemezsen:

```bash
cd /Users/emir/Documents/2parcaliprog
source .venv/bin/activate  # varsa

python3 category_finder.py   # önce kategori cache'ini üretir/günceller
python3 patent_worker.py     # sonra marka/patent sorgularını yapar ve output.xlsx yazar
```

## Loglar ve Tanılama

- Loglar `logs/` klasörüne yazılır:
  - `logs/category_finder.log`
  - `logs/patent_worker.log`
- Panelde bu logların son satırlarını canlı olarak görebilirsin.
- Üst kısımda:
  - Firefox/geckodriver durumu
  - `output.xlsx` dosyasının mevcut olup olmadığı
  birer rozet olarak gösterilir.

