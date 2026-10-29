# /// script
# requires-python = ">=3.10"
#
# [tool.orcaslicer.plugin]
# name = "Kobra 3 V2 Purge After ACE Load"
# description = "Cleans the nozzle and draws a purge line after the ACE Pro loads the filament, then travels high (Kobra 3 V2)."
# author = "Raul Ponce Quaresma"
# version = "0.4.0"
# ///

# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Raul Ponce Quaresma. Desenvolvido com assistência de ferramentas de IA.

import re
import orca

# Na Kobra 3 V2 o G9111 nivela e faz a linha de purga (UNDERLINE) ANTES da carga do ACE (T0-T3): a linha sai
# em seco e o bico chega à 1ª camada com o bolo da purga. Depois da carga (junto do M75) o bico é limpo na
# borracha, faz uma linha de purga na frente da mesa e sobe a Z80 para viajar (protege peças deixadas na mesa).
# (Uma macro M75 na impressora travou o GoKlipper em 27/10/2026, por isso fica no G-code.)
MARCA = "purga depois da carga"
M75 = "M75 ; The first extruder is ready."


def _first_match(text, pattern, default=""):
    m = re.search(pattern, text, flags=re.MULTILINE)
    return m.group(1).strip() if m else default


def _purga(bico):
    return [
        "; purga depois da carga (plugin kobra3v2 0.3): limpa o bico, linha na frente da mesa, viagem alta\n",
        f"M109 S{bico}\n",
        "WIPE_NOZZLE\n",
        "G90\n",
        "G1 Z5 F900\n",
        "M83\n",
        "G1 X20 Y5 F6000\n",
        "G1 Z0.3 F600\n",
        "G1 X120 E15 F600\n",
        "G1 X125 F3000\n",
        "G1 E-1 F1800\n",
        "G1 Z80 F1200\n",
        "M106 S0\n",
    ]


def _process(filename, ctx):
    with open(filename, "r", encoding="utf-8", errors="replace") as f:
        text = f.read()

    bico = _first_match(text, r"^G9111\b.*\bextruderTemp=(\d+)", "")
    tem_carga = re.search(r"^T\d\b", text, flags=re.MULTILINE) is not None
    if not bico or not tem_carga or MARCA in text:
        return

    lines = text.splitlines(keepends=True)
    out = []
    feito = False
    i = 0
    while i < len(lines):
        out.append(lines[i])
        if not feito and lines[i].startswith("; filament start gcode"):
            # Com o plugin de metadados, o M75 vem logo depois deste comentário; a purga entra depois dele.
            if i + 1 < len(lines) and lines[i + 1].startswith(M75):
                i += 1
                out.append(lines[i])
            out.extend(_purga(bico))
            feito = True
        i += 1

    with open(filename, "w", encoding="utf-8", newline="\n") as f:
        f.writelines(out)


class Kobra3V2PurgePipeline(orca.slicing.SlicingPipelineCapabilityBase):
    def get_name(self):
        return "Kobra 3 V2 Purge After ACE Load"

    def execute(self, ctx):
        if ctx.step != orca.slicing.Step.psGCodePostProcess:
            return orca.ExecutionResult.success()

        try:
            _process(ctx.gcode_path, ctx)
            return orca.ExecutionResult.success("Kobra 3 V2 purge after ACE load applied")
        except Exception as exc:
            return orca.ExecutionResult.failure(
                orca.PluginResult.RecoverableError,
                f"Kobra 3 V2 purge failed: {exc}",
            )


@orca.plugin
class Kobra3V2PurgePlugin(orca.base):
    def register_capabilities(self):
        orca.register_capability(Kobra3V2PurgePipeline)
