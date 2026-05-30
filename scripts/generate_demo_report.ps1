$ErrorActionPreference = "Stop"
$env:WEEKLY_REPORT_CONFIG = ".\config\example.yaml"
.\.venv\Scripts\python.exe -m src.cli.generate --config .\config\example.yaml --trigger manual

