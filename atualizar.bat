@echo off
rem Atualizacao do Almanaque LSB: competicoes novas, jogos novos e paginas com dados.
rem Agendada no Windows para toda terca-feira as 8h (tarefa "Almanaque LSB - atualizacao semanal").
rem Uso manual: dois cliques neste arquivo. O resultado fica em atualizacao.log.
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
set PY=%LOCALAPPDATA%\Programs\Python\Python312\python.exe
if not exist "%PY%" set PY=py

echo ===== %date% %time% ===== >> atualizacao.log
"%PY%" lsb_api.py competicoes --producao --liga 256 >> atualizacao.log 2>&1 || goto erro
"%PY%" lsb_api.py coletar --producao --liga 256 >> atualizacao.log 2>&1 || goto erro
"%PY%" publicar.py >> atualizacao.log 2>&1 || goto erro
echo OK >> atualizacao.log
exit /b 0

:erro
echo FALHOU (veja as linhas acima) >> atualizacao.log
exit /b 1
