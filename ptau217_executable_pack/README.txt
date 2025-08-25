How to use:
1) Download both files:
   - run_ptau217_app.py
   - build_ptau217_exe.ps1

2) (Optional) Just run with Python (no install needed):
   powershell -ExecutionPolicy Bypass -Command "python .\run_ptau217_app.py"
   Then open http://127.0.0.1:5173 (it also auto-opens).

3) Build a single Windows EXE:
   powershell -ExecutionPolicy Bypass -File .\build_ptau217_exe.ps1
   The EXE will appear in .\dist\pTau217App.exe

The EXE writes assets to %USERPROFILE%\.pTau217App and serves them locally.
Press Ctrl+C in the console to quit.
