# CrownLedger

Projeto Python com dois runtimes no mesmo repo:

- bot Discord em `bot/`
- app local desktop em `desktop/`

A logica de negocio partilhada vive em `app/` e `domain/`.

## Runtime Desktop

### Correr em source

Instalar dependencias:

```powershell
python -m pip install -r requirements-desktop.txt
```

Arrancar a app:

```powershell
python -m desktop.main
```

Tambem funciona:

```powershell
python desktop\main.py
```

### O que ja existe

- `Clan Health`
- `War Rank`
- `Scout`
- `Settings`
- deteccao de updates
- updater separado para builds empacotados

### Configuracao

As settings locais ficam em:

- Windows: `%APPDATA%\CrownLedger\settings.json`

O minimo para usar a app e configurar:

- `Clash API token`

Opcionalmente:

- `GitHub repo`
- `Release channel`
- `Default clan tag`
- `Last player tag`

## Runtime Discord

Instalar dependencias:

```powershell
python -m pip install -r requirements-discord.txt
```

Arrancar:

```powershell
python bot\main.py
```

## Testes

```powershell
pytest tests\domain tests\app -q -s
```

## Build Desktop

Gerar build local + zip de release:

```powershell
powershell -ExecutionPolicy Bypass -File tools\build_local_app.ps1 -Clean
```

Validar testes + compile check + build + updater smoke test:

```powershell
powershell -ExecutionPolicy Bypass -File tools\verify_desktop_release.ps1 -Clean
```

Artefactos principais:

- pasta app: `dist\CrownLedgerLocal\`
- zip para testers: `dist\release\CrownLedgerLocal-<version>-windows-x64.zip`

## Release Desktop

Documentacao operacional:

- tester guide: [docs/user/desktop-app.md](/c:/Projects/crownledger-bot/docs/user/desktop-app.md)
- release guide: [docs/release/desktop-release.md](/c:/Projects/crownledger-bot/docs/release/desktop-release.md)

Validacao automatica no GitHub:

- [desktop-verify.yml](/c:/Projects/crownledger-bot/.github/workflows/desktop-verify.yml)
- [desktop-release.yml](/c:/Projects/crownledger-bot/.github/workflows/desktop-release.yml)

Script para criar a tag correta da release desktop:

```powershell
powershell -ExecutionPolicy Bypass -File tools\create_desktop_release_tag.ps1
```
