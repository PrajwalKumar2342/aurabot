@echo off
echo =========================================
echo Mem0 Server (LM Studio Edition)
echo =========================================
echo.
echo Requirements:
echo   - LM Studio running with local server started
echo   - An embedding model loaded (e.g., nomic-embed-text)
echo     (This creates the memory embeddings)
echo   - Go app handles screenshot analysis separately
echo.
echo LM Studio URL: http://localhost:1234/v1
echo Mem0 Server:   http://localhost:8000
echo.
echo =========================================
python mem0_server.py
