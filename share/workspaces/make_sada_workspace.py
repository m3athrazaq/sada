#!/usr/bin/env python3
"""Generate share/workspaces/Sada.mws, Sada's default workspace.

The workspace stores no dock layout for the project page, so the layout comes from
the defaults declared in src/appshell/qml/Audacity/AppShell/ProjectPage/ProjectPage.qml.
It sets the playback toolbar items and puts the playback meter in the full-width
"Levels" panel below the editor.

Usage:  python3 share/workspaces/make_sada_workspace.py   (from the repository root)
"""

import json
import os
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))

# Toolbar items to show/hide relative to the Modern workspace
SHOW = {
    "zoom-to-selection": 1,
    "zoom-to-fit-project": 1,
    "zoom-toggle": 0,
    "trim-audio-outside-selection": 1,
    "silence-audio-selection": 0,
    "split-cut": 0,
    "action://trackedit/cut": 0,
    "action://trackedit/copy": 0,
    "action://trackedit/paste-default": 0,
}

SETTINGS = {
    # 0 = top bar, 1 = side bar, 2 = bottom "Levels" panel (Sada)
    "playbackToolbar/playbackMeterPosition": "2",
}


def main():
    with zipfile.ZipFile(os.path.join(HERE, "Modern.mws")) as modern:
        container = modern.read("META-INF/container.xml").decode("utf-8")
        metadata = modern.read("META-INF/metadata.xml").decode("utf-8")
        toolconfigs = json.loads(modern.read("ui_toolconfigs").decode("utf-8"))

    items = []
    for item in toolconfigs["playbackToolBar"]["items"]:
        item = dict(item)
        if item["action"] in SHOW:
            item["show"] = SHOW[item["action"]]
        items.append(item)

    out = os.path.join(HERE, "Sada.mws")
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("META-INF/container.xml", container)
        z.writestr("META-INF/metadata.xml", metadata)
        z.writestr("ui_settings", json.dumps(SETTINGS, indent=4))
        z.writestr("ui_states", json.dumps({}))
        z.writestr("ui_toolconfigs", json.dumps({"playbackToolBar": {"items": items}}, indent=4))
    print("written", out)


if __name__ == "__main__":
    main()
