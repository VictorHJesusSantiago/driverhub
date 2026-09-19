# AGENTS.md

Diretrizes para agentes que trabalham neste repositório.

## Verificação obrigatória antes de concluir tarefa

Rode nesta ordem:

```powershell
python -m compileall -q driverhub            # sintaxe de todos os pacotes
python -m unittest discover -s tests -v      # suíte de testes
python -m driverhub --version                # smoke: CLI raiz
python -m driverhub scan --json              # smoke: varredura real (segura)
python -m driverhub check --json             # smoke: health check
```

Nunca assuma que passou: execute de fato e corrija o que quebrar.

## Regras de código

- Python 3.10+; todo arquivo começa com `from __future__ import annotations`.
- **Somente stdlib**. Dependências opcionais (`rich`, `psutil`, `qrcode`,
  `requests`) são detectadas em runtime e nunca obrigatórias.
- `driverhub/tools/*` e `driverhub/core/*` não se importam em nível de módulo;
  imports entre eles são feitos **dentro de funções** (lazy) para evitar ciclos.
- Coletores/engines: expõem `collect(...)`/métodos que **nunca** lançam
  exceção; retornam lista de `dict`/`RunResult`.
- Mensagens de usuário em português; identificadores/código em inglês.
- Testes apenas com `unittest` (sem pytest).
- Não commitar: `*.pyc`, `__pycache__/`, `build/`, `dist/`, `*.egg-info`,
  `node_modules/`, `.venv/`, bancos/backups locais.
- `python -m compileall -q driverhub` precisa terminar sem erros antes de
  qualquer commit.

## Estrutura de pastas

- `driverhub/core/` — lógica principal (plataforma, banco, catálogo, ações).
  - `core/devices/*` — coletores por categoria de hardware.
  - `core/engines/` — motores por SO: `windows/`, `linux/`, `macos/`.
  - `core/cataloging/` — catálogo: correspondência, recomendação, verificação.
  - `core/probes/` — sondas de baixo nível (pnputil, sysfs, udevadm, WMI...).
  - `core/plan/` — políticas, agendamento, manutenção, upgrade.
  - `core/health/` — verificações de saúde por SO.
  - `core/workflows/` — sequências multi-etapa.
- `driverhub/tools/` — utilitários genéricos (sem dependência de core).
- `driverhub/i18n/` — idiomas; `driverhub/styles/` — temas.
- `driverhub/web/` — servidor HTTP, API, middleware e frontend estático.
- `driverhub/plugins/` — plugins (extensões OEM).
- `tests/` — suíte `unittest`.

## Git

- Mensagens de commit em português com prefixo de área
  (ex.: `core: ...`, `web: ...`, `tests: ...`).
- Não commitar segredos nem o banco `driverhub.db`.
