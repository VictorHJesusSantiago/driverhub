# -*- coding: utf-8 -*-
"""Messages in English (US). Falls back to pt-BR for missing keys."""
MSGS: dict = {
    "app.title": "Universal driver manager",
    "app.tagline": "official sources · terminal + web · cross-platform",
    "app.unsupported_os": "Unsupported OS for this operation.",

    "action.scan": "Scanning system...",
    "action.scan_done": "Scan finished in {seconds:.1f}s.",
    "action.check": "Checking system health...",
    "action.catalog_update": "Updating catalog from official sources...",
    "action.backup": "Creating backup...",
    "action.restore_confirm": "Restore the database from '{source}'? This will replace the current one.",
    "action.remove_confirm": "Remove the driver '{driver}' permanently?",
    "action.cancelled": "Cancelled.",

    "result.ok": "OK",
    "result.fail": "Failed",
    "result.none": "No records found.",
    "result.admin_hint": "Install/remove operations require administrator privileges (Windows: run as Administrator; Linux/macOS: use sudo).",

    "stat.catalog": "Official sources in catalog",
    "stat.devices": "Devices",
    "stat.drivers": "Manageable drivers",
    "stat.history": "Logged operations",

    "driver.installed": "Driver installed.",
    "driver.removed": "Driver removed.",
    "driver.updated": "Driver updated.",
    "driver.not_found": "Driver '{driver}' not found.",
    "driver.install_failed": "Install failed.",
    "driver.remove_failed": "Remove failed.",
    "driver.update_failed": "Update failed.",

    "state.admin": "Administrator",
    "state.limited": "Limited access (no admin)",
    "state.ok": "ok",
    "state.problem": "problem",
    "state.loaded": "loaded",
    "state.outdated": "outdated",
    "state.installed": "installed",

    "view.dashboard": "Dashboard",
    "view.devices": "Devices",
    "view.drivers": "Drivers",
    "view.catalog": "Catalog",
    "view.hardware": "Hardware",
    "view.history": "History",
    "view.settings": "Settings",
    "view.about": "About",

    "device.problems": "{count} device(s) with problems",
    "catalog.official_only": "100% official sources.",
    "catalog.updated": "Catalog updated.",
}  # type: ignore[not-writable]