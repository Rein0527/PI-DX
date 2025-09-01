# PI-DX

🎹 **PI-DX** 是一個互動式音樂遊戲/工具，支援讀取 MIDI 檔案，並提供播放、速度調整、以及可視化功能。  

---

## ✨ 功能特色
- 支援載入 MIDI 檔案
- 以 **音符掉落視覺化** 呈現
- 可調整播放速度 (50% / 75% / 100% / 125% / 150%)

---

## 📦 安裝方式

### 使用原始碼執行
1. 確保電腦已安裝 [Python 3.9+](https://www.python.org/)
2. Clone 專案：
   ```bash
   git clone https://github.com/Rein0527/PI-DX.git
   cd PI-DX
   ```
3. 安裝依賴：
   ```bash
   pip install -r requirements.txt
   ```
4. 執行：
   ```bash
   python main.py
   ```

---

## ⚙️ 打包 EXE
如果需要自行打包：
```bash
pip install pyinstaller
pyinstaller --onefile --windowed --icon=icon.ico main.py
```

打包後會生成 `dist/PI-DX.exe`。

---

## 🕹 使用方法
1. 開啟程式後，選擇要播放的 MIDI 檔案
2. 可透過選單調整播放速度
3. 鍵盤/滑鼠操作：
   - `Space`：開始 / 暫停
   - `Enter`：Auto Sound
   - `+/-`：Scroll Speed

---

## 📜 授權
MIT License © 2025 [Rein0527]
