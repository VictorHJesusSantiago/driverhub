# -*- coding: utf-8 -*-
"""Linha de comando do DriverHub."""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from typing import Any, Dict, List, Optional

from . import __version__, ui
from .core import actions, catalog as catalog_mod, linux, platform
from .core.database import Database


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="driverhub",
        description="DriverHub — gerenciador universal de drivers "
                    "(fontes oficiais, terminal + interface web).",
        epilog="Exemplos:\n"
               "  driverhub scan\n"
               "  driverhub drivers list\n"
               "  driverhub drivers install C:\\drv\\oem.inf\n"
               "  driverhub drivers remove oem10.inf\n"
               "  driverhub catalog update\n"
               "  driverhub web [--port 8000]\n"
               "  driverhub doctor\n"
               "  driverhub check\n"
               "  driverhub backup\n"
               "  driverhub admin\n",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    p.add_argument("--version", action="version", version=f"DriverHub {__version__}")

    def add_globals(sp: argparse.ArgumentParser, suppress: bool = False) -> None:
        # SUPPRESS (subparsers): não sobrescreve o valor já definido na raiz.
        sp.add_argument("--db",
                        default=argparse.SUPPRESS if suppress else None,
                        help="Caminho opcional do banco de dados SQLite.")
        sp.add_argument("--json", action="store_true",
                        default=argparse.SUPPRESS if suppress else False,
                        help="Saída em JSON (para scripts/automação).")

    add_globals(p, suppress=False)
    sub = p.add_subparsers(dest="command", title="comandos")

    def mk(name: str, help_: str, **kw) -> argparse.ArgumentParser:
        sp = sub.add_parser(name, help=help_, **kw)
        add_globals(sp, suppress=True)
        return sp

    sp_scan = mk("scan", "Escaneia SO, hardware e drivers instalados.")
    sp_doctor = mk("doctor", "Diagnóstico de ambiente e permissões.")
    sp_info = mk("info", "Informações do SO/hardware em detalhe.")

    drv = mk("drivers", "Gerenciar drivers instalados.")
    drv_sub = drv.add_subparsers(dest="drv_command", title="ações")
    mk_d = lambda nm, h: drv_sub.add_parser(nm, help=h,
                                            formatter_class=argparse.RawDescriptionHelpFormatter)
    d0 = mk_d("list", "Listar drivers instalados.")
    add_globals(d0)
    di = mk_d("info", "Detalhes de um driver.")
    di.add_argument("id")
    add_globals(di)
    ds = mk_d("system", "Listar drivers do sistema (Windows).")
    add_globals(ds)
    ins = mk_d("install", "Instalar driver (.inf/.run/módulo).")
    ins.add_argument("target", help="Arquivo .inf (Win) / .run (Linux) / nome do módulo")
    ins.add_argument("--permanent", action="store_true", help="Persistir módulo (Linux).")
    add_globals(ins)
    upd = mk_d("update", "Atualizar/recarregar driver.")
    upd.add_argument("id")
    upd.add_argument("--inf", default=None, help="Novo .inf para reinstalar.")
    add_globals(upd)
    rem = mk_d("remove", "Remover driver (requer admin).")
    rem.add_argument("id")
    rem.add_argument("--force", action="store_true", help="Forçar remoção (/force no pnputil).")
    add_globals(rem)

    mods = mk("modules", "Módulos do kernel (Linux).")
    mods.add_argument("--install", help="Carregar módulo")
    mods.add_argument("--remove", help="Descarregar módulo")
    mods.add_argument("--permanent", action="store_true")

    cat = mk("catalog", "Catálogo de drivers (fontes oficiais).")
    cat_sub = cat.add_subparsers(dest="cat_command", title="ações")
    mk_c = lambda nm, h: cat_sub.add_parser(nm, help=h)
    c0 = mk_c("update", "Atualizar catálogo a partir das fontes oficiais.")
    add_globals(c0)
    cs = mk_c("search", "Procurar no catálogo.")
    cs.add_argument("term")
    cs.add_argument("--os", default="", help="Filtrar por SO (ex.: Windows, Linux)")
    add_globals(cs)
    cshow = mk_c("show", "Listar catálogo.")
    cshow.add_argument("category", nargs="?", default="")
    cshow.add_argument("--manifest", default=catalog_mod.DEFAULT_MANIFEST,
                       help="URL de manifesto remoto.")
    add_globals(cshow)
    c4 = mk_c("categories", "Listar categorias.")
    add_globals(c4)

    hist = mk("history", "Histórico de operações.")
    hist.add_argument("--limit", type=int, default=50)
    hist.add_argument("--term", default="")

    stats = mk("stats", "Estatísticas do banco.")

    dev = mk("devices", "Inventário de dispositivos (PNP/PCI/USB).")
    dev.add_argument("--kind", default="", help="Filtrar por tipo (gpu, audio, ...)")

    web = mk("web", "Iniciar interface gráfica web (PC ou celular).")
    web.add_argument("--port", type=int, default=8000)
    web.add_argument("--host", default="0.0.0.0")
    web.add_argument("--no-browser", action="store_true",
                     help="Não abrir o navegador automaticamente.")

    export = mk("export", "Exportar relatório JSON do sistema.")
    export.add_argument("output", nargs="?", default=None)

    _ = mk("admin", "Reinicia com privilégios de administrador (UAC/pkexec/sudo).")

    _ = mk("check", "Verificação de saúde: dispositivos com problema + sugestões.")

    backup = mk("backup", "Cria um backup completo (banco + inventário).")
    backup.add_argument("dest", nargs="?", default=None)

    restore = mk("restore", "Restaura o banco a partir de um backup.")
    restore.add_argument("source")

    _ = mk("upgrade", "Auto-atualização via git (checkout).")
    return p


def _emit(args: argparse.Namespace, data: Any) -> None:
    if args.json:
        print(json.dumps(data, ensure_ascii=False, default=str, indent=2))


def _get_local_ips() -> List[str]:
    ips: List[str] = []
    try:
        import socket
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            ip = info[4][0]
            if ip not in ips and not ip.startswith("127."):
                ips.append(ip)
    except Exception:
        pass
    return ips


def run(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    db = Database(args.db)

    if not args.command:
        banner()
        parser.print_help()
        db.close()
        return 0

    try:
        if args.command == "scan":
            _cmd_scan(args, db)
        elif args.command == "info":
            _cmd_info(args)
        elif args.command == "doctor":
            _cmd_doctor(args, db)
        elif args.command == "drivers":
            return _cmd_drivers(args, db)
        elif args.command == "modules":
            return _cmd_modules(args)
        elif args.command == "catalog":
            return _cmd_catalog(args, db)
        elif args.command == "history":
            rows = db.history(limit=args.limit, term=args.term)
            _emit(args, rows)
            if not args.json:
                ui.table("Histórico", ["Quando", "Ação", "Alvo", "Resultado"],
                         [[r["ts"], r["action"], r["target"],
                           "ok" if r["ok"] else "falha"] for r in rows])
        elif args.command == "stats":
            st = db.stats()
            _emit(args, st)
            if not args.json:
                ui.kv("Estatísticas", {k.title(): f"{v} registro(s)" for k, v in st.items()})
        elif args.command == "devices":
            rows = db.list_devices()
            if args.kind:
                rows = [r for r in rows if r.get("kind") == args.kind.lower()]
            _emit(args, rows)
            if not args.json:
                ui.table("Dispositivos", ["Tipo", "Nome", "Fabricante", "Status"],
                         [[r.get("kind", ""), r.get("name", ""), r.get("vendor", ""),
                           r.get("status", "")] for r in rows])
        elif args.command == "web":
            return _cmd_web(args, db)
        elif args.command == "export":
            data = actions.run_scan(db)
            path = args.output or f"driverhub-{time.strftime('%Y%m%d-%H%M%S')}.json"
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2, default=str)
            ui.ok(f"Relatório exportado: {os.path.abspath(path)}")
        elif args.command == "admin":
            _cmd_admin(args)
        elif args.command == "check":
            _cmd_check(args, db)
        elif args.command == "backup":
            _cmd_backup(args, db)
        elif args.command == "restore":
            _cmd_restore(args, db)
        elif args.command == "upgrade":
            _cmd_upgrade(args, db)
        else:
            parser.print_help()
    finally:
        db.close()
    return 0


def _cmd_scan(args: argparse.Namespace, db: Database) -> None:
    if not args.json:
        ui.out(f"[bold cyan]{ui._ARROW} Escaneando sistema...[/bold cyan]" if ui._RICH
               else f"{ui._ARROW} Escaneando sistema...")
    t0 = time.time()
    data = actions.run_scan(db)
    if args.json:
        _emit(args, data)
        return
    info = data["os"]
    ui.out(f"Concluído em {time.time() - t0:.1f}s.")
    ui.kv("Sistema", {
        "SO": f"{info['name']} ({info['release']})",
        "Arquitetura": info["arch"],
        "Host": info["hostname"],
        "Admin": "Sim (root/administrador)" if info["admin"] else "Não",
        "Dispositivos": data.get("devices_count", 0),
        "Drivers gerenciáveis": data.get("drivers_count", 0),
        "Catálogo de fontes": data.get("catalog", 0),
    })
    devs = data.get("devices", [])
    if devs:
        ui.table("Dispositivos", ["Tipo", "Nome", "Fabricante", "Status"],
                 [[d.get("kind", ""), d.get("name", "")[:60], d.get("vendor", "")[:30],
                   d.get("status", "")] for d in devs[:60]])
    if not info["admin"]:
        ui.warn("Sem privilégios de administrador: instalação/remoção ficam bloqueadas.")


def _cmd_info(args: argparse.Namespace) -> None:
    data = platform.detect_all()
    if args.json:
        _emit(args, data)
        return
    osd = data["os"]
    ui.kv("Sistema Operacional",
          {"Nome": osd["name"], "Versão": osd.get("version", ""),
           "Kernel": osd.get("kernel", ""), "Arquitetura": osd["arch"],
           "Hostname": osd["hostname"], "Classe": data.get("device_class", "")})
    ui.kv("CPU", {"Nome": data["cpu"].get("name", ""),
                  "Núcleos": data["cpu"].get("cores", 0),
                  "Threads": data["cpu"].get("threads", 0)})
    total = data["ram"].get("total", 0) / (1024 ** 3)
    used = data["ram"].get("used", 0) / (1024 ** 3)
    ui.kv("Memória", {"Total (GB)": f"{total:.1f}", "Em uso (GB)": f"{used:.1f}"})
    gpus = data.get("gpu", [])
    if gpus:
        ui.table("Placas de vídeo", ["Nome", "Fabricante", "Driver"],
                 [[g.get("name", "")[:50], g.get("vendor", ""), g.get("driver_version", "")]
                  for g in gpus])
    nics = data.get("network", [])
    if nics:
        ui.table("Interfaces de rede", ["Nome", "IP", "Estado", "Velocidade (Mbps)"],
                 [[n.get("name", ""), n.get("ip", ""), "up" if n.get("up") else "down",
                   n.get("speed_mbps", 0)] for n in nics[:30]])
    if data.get("sensors"):
        ui.kv("Sensores", data["sensors"])


def _cmd_doctor(args: argparse.Namespace, db: Database) -> None:
    rep = actions.doctor(db)
    if args.json:
        _emit(args, rep)
        return
    ui.kv("Ambiente", {
        "SO": rep["os"]["name"], "Kernel": rep["os"].get("kernel", ""),
        "Python": rep["os"].get("python", ""),
        "Admin": "Sim" if rep["admin"]["admin"] else "Não",
        "Dispositivo": rep["os"].get("is_mobile", False),
        "Entradas no catálogo": rep["catalog"],
    })
    ui.table("Ferramentas", ["Ferramenta", "Status"],
             [[k, "OK" if v == "ok" else "Ausente"] for k, v in rep.get("tools", {}).items()])
    if not rep["admin"]["admin"]:
        ui.warn(rep["admin"]["hint"])


def _cmd_drivers(args: argparse.Namespace, db: Database) -> int:
    if not args.drv_command:
        rows = db.list_drivers()
        _emit(args, rows)
        if not args.json:
            ui.table("Drivers gerenciáveis", ["ID", "Nome", "Provedor", "Versão", "Classe"],
                     [[r.get("id", "")[:30], r.get("name", "")[:40], r.get("provider", "")[:20],
                       r.get("version", "")[:20], r.get("class", "")[:15]] for r in rows])
        return 0
    if args.drv_command == "list":
        rows = db.list_drivers()
        _emit(args, rows)
        if not args.json:
            ui.table("Drivers gerenciáveis", ["ID", "Nome", "Provedor", "Versão", "Classe", "Status"],
                     [[r.get("id", "")[:30], r.get("name", "")[:40], r.get("provider", "")[:20],
                       r.get("version", "")[:20], r.get("class", "")[:15],
                       r.get("status", "")] for r in rows])
    elif args.drv_command == "info":
        row = db.get_driver(args.id)
        if row is None and platform.detect_os()["system"] == "windows":
            row = actions.engine().driver_details(args.id)
        if row:
            _emit(args, row)
            if not args.json:
                clean = {k.replace("_", " ").title(): v for k, v in row.items() if v}
                ui.kv("Driver", clean)
        else:
            ui.fail(f"Driver '{args.id}' não encontrado.")
    elif args.drv_command == "system":
        if platform.detect_os()["system"] != "windows":
            ui.warn("'drivers system' só se aplica ao Windows.")
            return 0
        rows = actions.engine().drivers_system()
        _emit(args, rows)
        if not args.json:
            ui.table("Drivers do sistema", ["Módulo", "Nome", "Estado", "Tipo"],
                     [[r.get("Module Name", ""), r.get("Display Name", "")[:50],
                       r.get("State", ""), r.get("Type", "")] for r in rows])
    elif args.drv_command == "install":
        res = actions.run_install(db, args.target, force_package=args.permanent)
        _emit(args, res)
        if res.get("ok"):
            ui.ok(res.get("detail", "Driver instalado."))
            return 0
        ui.fail(res.get("detail", "Falha ao instalar."))
        return 1
    elif args.drv_command == "update":
        res = actions.run_update(db, args.id, args.inf)
        _emit(args, res)
        if res.get("ok"):
            ui.ok(res.get("detail", "Atualizado."))
            return 0
        ui.fail(res.get("detail", "Falha na atualização."))
        return 1
    elif args.drv_command == "remove":
        if not _confirm(f"Remover o driver '{args.id}' definitivamente?"):
            ui.warn("Cancelado.")
            return 1
        res = actions.run_remove(db, args.id, force=args.force)
        _emit(args, res)
        if res.get("ok"):
            ui.ok(res.get("detail", "Driver removido."))
            return 0
        ui.fail(res.get("detail", "Falha ao remover."))
        return 1
    return 0


def _cmd_modules(args: argparse.Namespace) -> int:
    if platform.detect_os()["system"] != "linux":
        ui.warn("'modules' só se aplica ao Linux.")
        return 0
    res = None
    if args.install:
        res = linux.install_module(args.install, permanent=args.permanent)
    elif args.remove:
        res = linux.unload_module(args.remove, persistent=args.permanent)
    else:
        rows = linux.kernel_modules()
        _emit(args, rows)
        if not args.json:
            ui.table("Módulos do kernel", ["Módulo", "Autor", "Versão", "Descrição"],
                     [[r.get("name", ""), r.get("author", "")[:25], r.get("version", "")[:15],
                       r.get("description", "")[:45]] for r in rows[:60]])
        return 0
    if res.get("ok"):
        ui.ok(res.get("detail", "OK."))
        return 0
    ui.fail(res.get("detail", "Falha."))
    return 1


def _cmd_catalog(args: argparse.Namespace, db: Database) -> int:
    if not args.cat_command:
        rows = db.catalog_search()
        _emit(args, rows)
        if not args.json:
            ui.table("Catálogo (fontes oficiais)",
                     ["Fabricante", "Categoria", "Dispositivo", "SO", "URL"],
                     [[r["vendor"], r["category"], r["device"], r["os"], r["url"]]
                      for r in rows[:100]])
        return 0
    if args.cat_command == "update":
        if not args.json:
            ui.out("Atualizando catálogo a partir das fontes oficiais...")
        res = actions.catalog_sync(db, args.manifest)
        _emit(args, res)
        if res.get("status") == "ok":
            ui.ok(res["message"])
        else:
            ui.warn(res["message"])
    elif args.cat_command == "search":
        rows = db.catalog_search(term=args.term)
        if args.os:
            rows = [r for r in rows if args.os.lower() in r.get("os", "").lower()]
        _emit(args, rows)
        if not args.json:
            ui.table(f'Resultados para "{args.term}"',
                     ["Fabricante", "Categoria", "Dispositivo", "SO", "URL"],
                     [[r["vendor"], r["category"], r["device"], r["os"], r["url"]]
                      for r in rows])
    elif args.cat_command == "show":
        rows = db.catalog_search(category=args.category)
        _emit(args, rows)
        if not args.json:
            title = f"Catálogo{(' — ' + args.category) if args.category else ''}"
            ui.table(title, ["Fabricante", "Categoria", "Dispositivo", "SO", "URL"],
                     [[r["vendor"], r["category"], r["device"], r["os"], r["url"]] for r in rows])
    elif args.cat_command == "categories":
        cats = db.catalog_categories()
        _emit(args, cats)
        if not args.json:
            joined = ", ".join(cats)
            ui.out(joined)
    return 0


def _cmd_web(args: argparse.Namespace, db: Database) -> int:
    from .web.server import start_server
    try:
        start_server(db=db, host=args.host, port=args.port,
                     open_browser=not args.no_browser)
    except KeyboardInterrupt:
        pass
    return 0


def _cmd_admin(args: argparse.Namespace) -> int:
    info = platform.detect_os()
    if info["admin"]:
        ui.ok("Já está em modo administrador/root.")
        return 0
    res = actions.relaunch_admin()
    _emit(args, res)
    if res.get("ok"):
        ui.ok(res.get("detail", "Elevação solicitada."))
        return 0
    ui.fail(res.get("detail", "Não foi possível elevar privilégios."))
    return 1


def _cmd_check(args: argparse.Namespace, db: Database) -> int:
    if not args.json:
        ui.out(f"[bold cyan]{ui._ARROW} Verificando saúde do sistema...[/bold cyan]" if ui._RICH
               else f"{ui._ARROW} Verificando saúde do sistema...")
    report = actions.run_check(db)
    _emit(args, report)
    if args.json:
        return 0
    ui.kv("Verificação de saúde", {
        "Sistema": f"{report['os']['name']} ({report['os']['release']})",
        "Admin": "Sim" if report["admin"]["admin"] else "Não",
        "Dispositivos": report["devices"],
        "Drivers gerenciáveis": report["drivers"],
        "Problemas encontrados": report["problems_count"],
        "Sugestões do catálogo": report["suggestions_count"],
    })
    if report["problems"]:
        ui.table("Dispositivos com problema", ["Tipo", "Dispositivo", "Fabricante"],
                 [[p.get("kind", ""), p.get("name", "")[:50], p.get("vendor", "")[:30]]
                  for p in report["problems"][:50]])
    if report["suggestions"]:
        ui.table("Sugestões de drivers oficiais", ["Dispositivo", "Fabricante", "Download"],
                 [[s["device"][:40], s["catalog"]["vendor"], s["catalog"]["url"]]
                  for s in report["suggestions"][:20]])
    if not report["problems"]:
        ui.ok("Nenhum dispositivo com problema detectado.")
        return 0
    ui.warn("Verifique os dispositivos com problema e instale os drivers oficiais indicados.")
    return 1


def _cmd_backup(args: argparse.Namespace, db: Database) -> int:
    if not args.json:
        ui.out("Criando backup...")
    res = actions.run_backup(db, args.dest)
    _emit(args, res)
    if res.get("ok"):
        ui.ok(res.get("detail", "Backup criado."))
        return 0
    ui.fail(res.get("detail", "Falha no backup."))
    return 1


def _cmd_restore(args: argparse.Namespace, db: Database) -> int:
    if not _confirm(f"Restaurar o banco a partir de '{args.source}'? Isso substituirá o atual."):
        ui.warn("Cancelado.")
        return 1
    res = actions.run_restore(db, args.source)
    _emit(args, res)
    if res.get("ok"):
        ui.ok(res.get("detail", "Restaurado."))
        return 0
    ui.fail(res.get("detail", "Falha na restauração."))
    return 1


def _cmd_upgrade(args: argparse.Namespace, db: Database) -> int:
    if not args.json:
        ui.out("Verificando atualizações (git pull)...")
    res = actions.run_upgrade()
    _emit(args, res)
    if res.get("ok"):
        ui.ok(res.get("detail", "Pronto."))
        return 0
    ui.warn(res.get("detail", ""))
    return 1


def _confirm(prompt: str) -> bool:
    if os.isatty(0):
        try:
            ans = input(f"{prompt} [s/N] ").strip().lower()
            return ans in ("s", "sim", "y", "yes")
        except EOFError:
            return False
    return False


def banner() -> None:
    if ui._RICH:
        ui.out("[bold magenta]   DriverHub[/bold magenta] "
               f"[bold white]v{__version__}[/bold white]")
        ui.out("[cyan]   Gerenciador universal de drivers[/cyan] "
               "[grey]— fontes oficiais · terminal + web · multiplataforma[/grey]")
    else:
        print(f"DriverHub v{__version__} — gerenciador universal de drivers")


if __name__ == "__main__":
    sys.exit(run())
