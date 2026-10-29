# /// script
# requires-python = ">=3.10"
#
# [tool.orcaslicer.plugin]
# name = "Kobra 3 V2 Wait First Layer Bed"
# description = "Waits for the first-layer bed temperature right after the G9111 leveling of the Kobra 3 V2."
# author = "Raul Ponce Quaresma"
# version = "0.4.0"
# ///

# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Raul Ponce Quaresma. Desenvolvido com assistência de ferramentas de IA.

import re
import orca

# O G9111 deixa a mesa na temperatura do nivelamento (60 °C) e a temperatura pedida pelo fatiador só chega na
# 2ª camada: espera a da 1ª camada logo depois do G9111.
MARCA = "esperar a mesa da 1a camada"


def _first_match(text, pattern, default=""):
    m = re.search(pattern, text, flags=re.MULTILINE)
    return m.group(1).strip() if m else default


def _process(filename, ctx):
    with open(filename, "r", encoding="utf-8", errors="replace") as f:
        text = f.read()

    mesa = _first_match(text, r"^G9111\b.*\bbedTemp=(\d+)", "")
    if not mesa or MARCA in text:
        return

    out = []
    for line in text.splitlines(keepends=True):
        out.append(line)
        if line.startswith("G9111"):
            out.append(f"M190 S{mesa} ; esperar a mesa da 1a camada (plugin kobra3v2 0.3)\n")

    with open(filename, "w", encoding="utf-8", newline="\n") as f:
        f.writelines(out)


class Kobra3V2BedWaitPipeline(orca.slicing.SlicingPipelineCapabilityBase):
    def get_name(self):
        return "Kobra 3 V2 Wait First Layer Bed"

    def execute(self, ctx):
        if ctx.step != orca.slicing.Step.psGCodePostProcess:
            return orca.ExecutionResult.success()

        try:
            _process(ctx.gcode_path, ctx)
            return orca.ExecutionResult.success("Kobra 3 V2 first layer bed wait applied")
        except Exception as exc:
            return orca.ExecutionResult.failure(
                orca.PluginResult.RecoverableError,
                f"Kobra 3 V2 bed wait failed: {exc}",
            )


@orca.plugin
class Kobra3V2BedWaitPlugin(orca.base):
    def register_capabilities(self):
        orca.register_capability(Kobra3V2BedWaitPipeline)
