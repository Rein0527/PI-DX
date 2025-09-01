rmdir /s /q build
rmdir /s /q dist

pyinstaller --noconfirm --clean ^
  --name "PI-DX" ^
  --onefile ^
  --windowed ^
  --icon static\img\icon\icon.ico ^
  --collect-all pygame ^
  --add-data "static;static" ^
  --paths . ^
  --hidden-import config ^
  main.py
