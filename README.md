# DriverHub — The Universal Driver Manager

> Gerencie, atualize e remova drivers de qualquer dispositivo, em qualquer
> sistema operacional, com fonte oficial sempre. Tudo em um só lugar.

DriverHub é um gerenciador de drivers completo e multiplataforma, com:

- **Interface gráfica web moderna e responsiva** — funciona no computador e no
  celular (basta abrir o endereço local no navegador).
- **Interface de terminal (CLI)** — para uso em qualquer SO, inclusive via SSH.
- **Suporte a Windows, Linux e macOS** (detecção automática).
- **Inventário completo** de dispositivos (CPU, GPU, rede, áudio, etc.).
- **Catálogo de drivers oficiais** (Intel, AMD, NVIDIA, Realtek, Microsoft,
  fabricantes de notebooks/placas-mãe etc.), atualizável a partir de fontes
  oficiais.
- **Operações sobre drivers instalados**: listar, instalar, atualizar, excluir,
  com trilha de histórico/auditoria.
- **Zero dependências obrigatórias** — roda 100% com a biblioteca padrão do
  Python (recursos extras ativam `rich` e `psutil` automaticamente quando
  disponíveis).

## Requisitos

- Python 3.9+ (testado com 3.14)
- Windows / Linux / macOS
- Privilégios de administrador (root) para instalar/excluir drivers

## Instalação

```bash
# Opção A — direto do checkout (sem instalar)
cd driverhub
python -m driverhub --help

# Opção B — instalar como pacote (gera o comando global `driverhub`)
python -m pip install -e .            # modo desenvolvimento
# ou
python -m pip install .               # instalação normal

# Recursos extras (opcionais: telas bonitas e métricas)
python -m pip install -r requirements.txt
```

## Uso rápido

```bash
# Terminal: ver help completo
driverhub --help            # ou: python -m driverhub --help

# Terminal: escanear dispositivos e driveres do sistema
driverhub scan

# Terminal: listar drivers instalados
driverhub drivers list

# Terminal: verificar saúde (dispositivos com problema + sugestões oficiais)
driverhub check

# Terminal: atualizar o catálogo a partir das fontes oficiais
driverhub catalog update

# Terminal: reiniciar com privilégios de administrador (UAC/pkexec/sudo)
driverhub admin             # ou: driverhub.cmd --elevate no Windows

# Interface gráfica web (abra no navegador do PC ou do celular)
driverhub web
```

## Comandos principais (CLI)

| Comando | Descrição |
| --- | --- |
| `scan` | Detecta SO, inventário de hardware e drivers instalados |
| `check` | Verificação de saúde: dispositivos com problema + sugestões oficiais |
| `drivers list` | Lista drivers instalados (com detalhes) |
| `drivers info <id>` | Detalhes de um driver |
| `drivers install <arquivo.inf/.run/módulo>` | Instala um driver (requer admin) |
| `drivers update <id> [--inf novo]` | Atualiza/recarrega um driver |
| `drivers remove <id> [--force]` | Remove um driver (requer admin) |
| `modules [--install/--remove]` | Módulos do kernel (Linux) |
| `catalog update` | Busca a lista de fontes oficiais mais recente |
| `catalog search <termo>` | Procura drivers oficiais no catálogo |
| `catalog show [categoria]` | Lista entradas do catálogo |
| `history [--term]` | Histórico/auditoria de operações |
| `backup [destino]` | Backup completo (banco + inventário) |
| `restore <origem>` | Restaura o banco (requer admin) |
| `doctor` | Diagnóstico do ambiente e permissões |
| `admin` | Reexecuta elevado (UAC / pkexec / sudo) |
| `upgrade` | Auto-atualização via git (checkout) |
| `export [arquivo.json]` | Exporta relatório JSON do sistema |
| `--json` | Qualquer comando pode emitir JSON (`driverhub scan --json`) |
| `web` | Sobe a interface gráfica local |

## Interface web

A interface web é servida localmente (`http://localhost:8000`) e respondida em
qualquer dispositivo da rede. No celular, basta acessar o endereço `http://<IP
da máquina>:8000` (um QR Code é impresso no terminal quando o pacote `qrcode`
está instalado). Funciona em qualquer navegador — Android, iOS, Windows,
Linux, macOS. Painéis: visão geral (com alertas de dispositivos com problema),
dispositivos, drivers (instalar/atualizar/remover), catálogo oficial,
hardware, histórico.

## Nota de segurança

- DriverHub **nunca** baixa drivers automaticamente sem confirmação.
- Links de download apontam sempre para fontes oficiais (fabricantes).
- Operações destrutivas (remover driver) exigem confirmação explícita e são
  registradas no histórico.

## Estrutura

```
driverhub/
├── driverhub/            # pacote principal
│   ├── __main__.py       # entrypoint (python -m driverhub)
│   ├── cli.py            # interface de terminal
│   ├── core/             # motor: plataforma, banco, catálogo, ações
│   │   ├── platform.py   # detecção de SO/hardware
│   │   ├── windows.py    # motores nativos do Windows
│   │   ├── linux.py      # motores do Linux
│   │   ├── macos.py      # motores do macOS
│   │   ├── catalog.py    # catálogo de fontes oficiais
│   │   ├── database.py   # SQLite (catálogo, inventário, histórico)
│   │   └── actions.py    # operações de alto nível
│   └── web/              # interface gráfica web
│       ├── server.py     # servidor http (stdlib)
│       └── static/       # frontend (HTML/CSS/JS responsivo)
└── README.md
```