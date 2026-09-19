# -*- coding: utf-8 -*-
"""Mensagens em Português (Brasil), idioma padrão do DriverHub."""
MSGS: dict = {
    "app.title": "Gerenciador universal de drivers",
    "app.tagline": "fontes oficiais · terminal + web · multiplataforma",
    "app.unsupported_os": "SO não suportado para esta operação.",

    "action.scan": "Escaneando sistema...",
    "action.scan_done": "Varredura concluída em {seconds:.1f}s.",
    "action.check": "Verificando saúde do sistema...",
    "action.catalog_update": "Atualizando catálogo a partir das fontes oficiais...",
    "action.backup": "Criando backup...",
    "action.restore_confirm": "Restaurar o banco a partir de '{source}'? Isso substituirá o atual.",
    "action.remove_confirm": "Remover o driver '{driver}' definitivamente?",
    "action.cancelled": "Cancelado.",

    "result.ok": "OK",
    "result.fail": "Falha",
    "result.none": "Nenhum registro encontrado.",
    "result.admin_hint": "Operações de instalação/remoção exigem privilégios de administrador (Windows: executar como Administrador; Linux/macOS: usar sudo).",

    "stat.catalog": "Fontes oficiais no catálogo",
    "stat.devices": "Dispositivos",
    "stat.drivers": "Drivers gerenciáveis",
    "stat.history": "Operações registradas",

    "driver.installed": "Driver instalado.",
    "driver.removed": "Driver removido.",
    "driver.updated": "Driver atualizado.",
    "driver.not_found": "Driver '{driver}' não encontrado.",
    "driver.install_failed": "Falha ao instalar.",
    "driver.remove_failed": "Falha ao remover.",
    "driver.update_failed": "Falha na atualização.",

    "state.admin": "Administrador ✓",
    "state.limited": "Acesso limitado (sem admin)",
    "state.ok": "ok",
    "state.problem": "com problema",
    "state.loaded": "carregado",
    "state.outdated": "desatualizado",
    "state.installed": "instalado",

    "view.dashboard": "Painel",
    "view.devices": "Dispositivos",
    "view.drivers": "Drivers",
    "view.catalog": "Catálogo",
    "view.hardware": "Hardware",
    "view.history": "Histórico",
    "view.settings": "Configurações",
    "view.about": "Sobre",

    "device.problems": "{count} dispositivo(s) com problema",
    "catalog.official_only": "Fontes 100% oficiais.",
    "catalog.updated": "Catálogo atualizado.",
}  # type: ignore[not-writable]