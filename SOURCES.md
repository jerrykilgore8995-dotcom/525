# Source starting points (verified links or discovery leads)
- Official 525 2020 Rev B manual, pp. 1–2: https://apiaudio.com/docs/manuals/525_user_2020-12-15.pdf — primary controls and specs: 15 us attack; release 0.1/0.5/2/2.5 s; 2:1/20:1; 25 dB GR; 60k balanced in, 75 ohm transformer out; +/-0.5 dB 20 Hz–40 kHz; +27/+28 dBu max input/output, 112 dB SNR. Verify conditions and rail differences. Official manual does not give full THD curves.
- Vintage 525C schematic: https://www.sowter.co.uk/schematics/API%20525C.pdf — visually inspected; shows FET, multiple 2520 blocks, output and sidechain transformers, ceiling resistor ladders, detector and release network. Historical schematic is NOT proof of modern reissue connectivity.
- Historical API literature: https://www.steampoweredradio.com/pdf/api/manuals/api%201972%20schematics.pdf and https://www.steampoweredradio.com/pdf/api/api%201972%20catalog.pdf — historical 2520 specifications and 525 distortion ceiling; distinguish revision and test conditions.
- John Hardy 990 technical material: https://www.johnhardyco.com/pdf/990.pdf ; https://www.fullcompass.com/common/files/20190-990CTechnicalinformationsheet.pdf — full schematic variants and supply-dependent components. Original Jensen engineering paper: https://www.technicalaudio.com/pdf/Jensen_Transformers/Jensen_OpAmps_990_and_related/Jensen_JE-990_opamp_JAES_reprint_1980.pdf .
- 2520 schematic discovery lead: https://groupdiy.com/threads/api.44738/page-2 — compare corrected drawings, physical revisions and dates; not an authenticated factory netlist. Do not trust arbitrary downloaded SPICE or clone models without audits. Find 2510 internal schematic/model and verify independently; missing exact 2510 evidence is potential blocker.
- 525A distinction: https://apiaudio.com/product/525a-fet-compressor/ — later model, not target.
- Obtain physical measurements or service documentation where sources lack modern circuit details, FET identity/parameters, transformers, pot laws, detector time definitions or THD curves. Do not conflate contradictory historical release labels. Use authorized source copies; include URLs, page references, access dates, hashes for local supporting files, and license information. This handoff does not include third-party PDFs or unverified models.

## Inspected sources and revision evidence

Inspection date 2026-11-17 (America/New_York). Third-party documents remain at their source URLs. Repository CSVs are working transcriptions.

| Source | Page or figure | Local copy SHA-256 or status |
| --- | --- | --- |
| Official API 525 guide | Rev B pages 1–2 | `d73e86232d68dce96a40a08e2d80ed7ce38d0a7a9b2d1cbe7d7b657786cf09d8` |
| Sowter-hosted 525C drawing | Single sheet | `219000196d5f2d5d43f0388e3dfaae951b8c260f00374097253e04a3af7004e0` |
| Full Compass copy of the Hardy technical sheet | Page 3, common circuit and 990/990A/990C differences | `9b98e58856750243b8308c4631e4f0fc411bc1b39aeaba18c4028fe3967f8753` |
| Jensen 1980 JAES paper | Fig. 6 and parts list on printed p. 29, test conditions on pp. 32–34 | Indexed text was readable. Direct PDF retrieval returned HTTP 404. |
| [Original reissue product photograph](https://retrogearshop.com/cdn/shop/products/1.-API-525-Front.jpg?width=760) | Frontal photo, normalized using faceplate edges x=280–460, y=65–700 in the 760 px image | See SHA-256 below. Perimeter/pointer bounds are approximate from the photographed assembly. |
| [525 Setup Sheet](https://cdn.shopify.com/s/files/1/0024/2352/1341/files/API_525_Setup_Sheet.pdf) | Front control illustrations | Confirms external switch labels and timing legends. No circuit diagram. |
| [CAPI CA-0252 Rev A build guide](https://capi-gear.com/catalog/Build_CA-0252-DIY_Rev_A.php) | BOM, overlay, and schematic section | Manufacturer withholds its clone circuit drawing. Suitable for comparison only. |
| [Historical repair index](https://furballaudio.com/vintageaudio.php) and [GroupDIY schematic lead](https://groupdiy.com/threads/api-525-compressor.93118/) | Vintage factory test and install material | Public index or discussion visible. Direct retrieval returned HTTP 503 and 403, respectively. |
| [VCR2N datasheet index](https://www.alldatasheet.com/datasheet-pdf/pdf/84903/VISHAY/VCR2N.html) | Vishay/Siliconix product sheet | Vintage Q1 identifier matches the scan. Device limits do not determine the precise reissue FET or its distortion behavior. |

Front photograph SHA-256 at the URL above `3b66f7ccb81c43d62d59b27c8f2825fff4a0bceb84fcf517b265f381d787b0c2`.

## Vintage SPICE additions

- [Circulated 2520 redraw](https://www.scribd.com/document/334300673/API-2520-schematic-pdf), page image SHA-256 `761a2e5391c2deb27a0655d4e85e8dbf03d74f39302a202a07d32e2283c5ef49`. Preserve the pictured version separately from any rewire candidate.
- [2520 drawing variants discussion](https://groupdiy.com/threads/origin-of-2520-schematic.62035/) documents the D2/Q9 disagreement. [2520BC parts and build reports](https://groupdiy.com/threads/ours-sound-like-the-2-5-2-0.4796/page-6) document the alternate parts set. Neither validates the Q9 analysis on the real device.
- [Motorola rectifier and reference diode handbook](https://www.bitsavers.org/components/motorola/_dataBooks/1988_Motorola_Rectifiers_and_Zener_Diodes_Data.pdf), MZ2360/MZ2361 forward reference specifications.
- [Transistor model library](https://github.com/mpkopec/ltspice-lib/blob/master/cmp/standard.bjt), examined file SHA-256 `c3a3d6978b7a29b8b39e41b67860dc597fd4f470541f82fa138af42bb7268c16`. Fairchild-labelled 2N5087 and 2N5210 entries.
- [API 550L circuit sheets](https://www.scribd.com/document/791521152/API-550L) expose a 2510 module pin map and circuit instances. The module is shown as a block.
