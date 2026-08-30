# Upstream repositories and primary publications

This artifact builds on MTSA and adapts examples associated with prior DUCS
and OTF-DCS work.  Please cite the relevant primary sources when using these
materials.

## MTSA

- Official project site: <https://mtsa.dc.uba.ar/>
- Official source repository: <https://git.exactas.uba.ar/lafhis/mtsa>
- Pinned artifact source: MTSA `v1.1.0`, commit
  `da18ad2e50f6946795b3d49703ae4192528a9291`
- Nicolás D'Ippolito, Dario Fischbein, Marsha Chechik, and Sebastián Uchitel.
  “MTSA: The Modal Transition System Analyser.” *23rd IEEE/ACM International
  Conference on Automated Software Engineering (ASE 2008)*, pp. 475–476,
  2008. <https://doi.org/10.1109/ASE.2008.78>

## Dynamic update of discrete-event controllers (DUCS)

- Official artifact page: <https://mtsa.dc.uba.ar/updateControllers/2017-tse.html>
- Leandro Nahabedian, Víctor A. Braberman, Nicolás D'Ippolito, Shinichi
  Honiden, Jeff Kramer, Kenji Tei, and Sebastián Uchitel. “Dynamic Update of
  Discrete Event Controllers.” *IEEE Transactions on Software Engineering*,
  46(11):1220–1240, 2020. <https://doi.org/10.1109/TSE.2018.2876843>
- Leandro Nahabedian, Víctor A. Braberman, Nicolás D'Ippolito, Shinichi
  Honiden, Jeff Kramer, Kenji Tei, and Sebastián Uchitel. “Assured and Correct
  Dynamic Update of Controllers.” *Proceedings of the 11th International
  Symposium on Software Engineering for Adaptive and Self-Managing Systems
  (SEAMS 2016)*, pp. 96–107, 2016.
  <https://doi.org/10.1145/2897053.2897056>

The eight DUCS parent LTS files and nine fixed FG-DUCS adaptations are bound by
path, byte count, SHA-256, and parent-to-adaptation mapping in
`Implementation/Experiment/Models/MODEL_PROVENANCE.json`.

## On-the-fly dynamic update controller synthesis (O-DUCS)

- Takanori Hirano, Takuto Yamauchi, Kenji Tei, and Shinichi Honiden.
  "Dynamic Update Controller Synthesis using on-the-fly Exploration."
  *IEICE Technical Report*, 123(443), KBSE2023-78, pp. 76-78, 2024.
  Three-page, non-peer-reviewed technical report in Japanese.
  <https://ken.ieice.org/ken/paper/20240314Vccd/>

The legacy `on_the_fly` tool route is inherited; it is separate from the
current `revised_on_the_fly` route. See `source-rebuild/README.md` for the
static dispatch boundary. Inclusion of this code does not establish byte
identity with the implementation used for the 2024 report or a new rerun.

## On-the-fly directed controller synthesis (OTF-DCS)

- Daniel Ciolek, Matias Duran, Florencia Zanollo, Nicolas Pazos, Julián
  Braier, Víctor A. Braberman, Nicolás D'Ippolito, and Sebastián Uchitel.
  “On-the-fly Informed Search of Non-blocking Directed Controllers.”
  *Automatica*, 147:110731, 2023.
  <https://doi.org/10.1016/j.automatica.2022.110731>

The three canonical MTSA resources used only to generate the adapted OTF-DCS
families are not copied into this artifact.  Their official URLs, pinned ref,
byte counts, and SHA-256 values are recorded in
`provenance/UPSTREAM_RESOURCES.json`.

## Permission and endorsement boundary

The unmodified DUCS parents and three canonical OTF-DCS resources are cited and
hash-bound but omitted. Citations identify intellectual provenance; they do
not themselves grant a license. `RIGHTS_REVIEW.md` separates author-attested
permission to modify/publish the MTSA/DUCS-based tool from the remaining
file-class checks for generated and source-anchored inputs. See `NOTICE` for
the distribution boundary. No endorsement by MTSA or the cited authors is
implied.
