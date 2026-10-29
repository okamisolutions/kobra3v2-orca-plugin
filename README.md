# Kobra 3 V2 — plugins de compatibilidade Anycubic para o OrcaSlicer

> **English summary.** Three independent OrcaSlicer Python plugins for the Anycubic Kobra 3 V2 with ACE Pro: Anycubic metadata for the touchscreen, a nozzle purge after the ACE load, and a wait for the first-layer bed temperature. Install only the ones you need. Beta: in development and not yet proven.

**Aviso:** projeto beta, em desenvolvimento e ainda não comprovado. Use por sua conta e risco.

Desenvolvido por Raul Ponce Quaresma com assistência de ferramentas de IA.

## Três plugins, cada um instalado à parte

| Plugin | Arquivo | O que faz |
|---|---|---|
| Metadados Anycubic | `kobra3v2_metadados_anycubic.py` | Faz a tela da Kobra aceitar o G-code do Orca |
| Purga depois da carga do ACE | `kobra3v2_purga_pos_ace.py` | Limpa o bico e faz a linha de purga *depois* que o ACE carrega o filamento |
| Esperar a mesa da primeira camada | `kobra3v2_mesa_1a_camada.py` | Espera a temperatura de mesa da primeira camada logo depois do nivelamento |

Nenhum depende dos outros, e todos rodam na etapa de pós-processamento do G-code (`psGCodePostProcess`), tanto ao exportar o arquivo quanto ao enviar pela rede.

### Metadados Anycubic

- Depois de `; HEADER_BLOCK_END`, escreve os blocos que o Anycubic Slicer Next escreve: `exclude_object`, `model_instances`, `source_info`, `paint_info` (material e cor RGB de cada filamento), `project_info` (matriz de purga) e `flush_multiplier_calculate_by_acnext`.
- Marca a miniatura de 512×512 como `top`.
- Põe `; EXECUTABLE_BLOCK_HEAD` e `M75` antes do primeiro `; filament start gcode`.
- Os blocos de metadados são refeitos a cada passagem, mas o `M75` se repete se o mesmo arquivo passar duas vezes pelo plugin.

### Purga depois da carga do ACE

O `G9111` da Kobra nivela e faz a linha de purga *antes* da carga do filamento. Por isso, o bico chegava à primeira camada com plástico acumulado. Depois da carga (logo após o `M75`, se o plugin de metadados estiver instalado), este plugin:

1. aquece o bico (`M109`);
2. limpa o bico (`WIPE_NOZZLE`);
3. faz uma linha de purga na frente da mesa;
4. sobe a Z80 para viajar sem bater em peças deixadas na mesa.

Só age se houver carga do ACE (`T0`–`T3`) e um `G9111` com a temperatura do bico. Ele deixa uma marca no arquivo e não se repete.

### Esperar a mesa da primeira camada

O `G9111` deixa a mesa na temperatura do nivelamento (60 °C), e a temperatura pedida pelo fatiador só chega na segunda camada. Este plugin insere `M190 S<temperatura>` logo depois do `G9111`. Também deixa uma marca e não se repete.

## Descoberta importante: o bloco de configuração

A tela da Kobra 3 V2 **não usa o `paint_info` do cabeçalho**. Ela lê os filamentos e as cores só no bloco de configuração no fim do G-code (`; CONFIG_BLOCK_START`). Se o perfil da impressora no Orca estiver com **"Skip G-code config block"** ligado, a seleção de filamento na tela trava.

Deixe essa opção desligada.

## Instalação

- Requer um OrcaSlicer com plugins em Python. Foi usado o 2.5.0-dev (nightly).
- Copie os arquivos que quiser para a pasta `orca_plugins` da configuração do Orca. No Windows, ela fica em `%APPDATA%\OrcaSlicer\orca_plugins\`.

## Equivalência com a versão de arquivo único

Antes, as três funções estavam num plugin só (v0.3). Os três plugins separados geram **exatamente o mesmo G-code** que a v0.3, em qualquer ordem de execução.

Isso foi conferido byte a byte em 11 G-codes reais, nas 6 ordens possíveis (66 combinações), incluindo:
- arquivos com e sem carga do ACE;
- arquivos sem `G9111`;
- impressão por objeto.

Se você usa a versão de arquivo único, remova-a antes de instalar estes.

## Estado

| Parte | Estado |
|---|---|
| Metadados, miniatura e `M75` | Funcionou em impressões enviadas pelo Orca |
| Purga depois da carga e espera da mesa | Em uso desde 27/10/2026, na versão de arquivo único, sem teste formal |
| Os três como plugins separados no Orca | Mesmo G-code da versão de arquivo único; ainda não rodados separados dentro do Orca |

Testado numa Kobra 3 V2 com ACE Pro e o firmware customizado Rinkhals instalado.

## Licença

MIT. Veja [LICENSE](LICENSE).

Projeto independente, sem ligação com a Anycubic. "Anycubic", "Kobra" e "ACE Pro" são marcas dos seus donos.
