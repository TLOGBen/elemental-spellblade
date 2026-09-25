# ElementsSpellblade native / Round 20 (slice N2)

Runtime: **Skyrim SE 1.5.97.0 + SKSE 2.0.20** only. No entry-51 fallback, hooks, trampolines or code patches.
Needs the VC++ 2015-2022 runtime >= 14.44 (`/MD`, built with toolset 14.44).

From the workspace root:

```powershell
python -B native/fetch_cmake.py   # once, only if native/deps/cmake-3.31.8-windows-x86_64 is missing
python -B native/build.py
python build_v03.py
```

`native/build.py` uses Visual Studio 2022 x64 MSVC and the pinned CMake 3.31.8 in `native/deps/` (the local VS install has no CMake component). It regenerates `include/ManifestData.h` and the test fixtures (`build/fix20-magnitude-table.json` from the reference model `build/fix20_reference.py`, `build/fix20-wiring.json` from the generator's records), builds the DLL and `hit_pipeline_test`, runs CTest, and writes `out/build-receipt.json` with what was actually used (cl version and path, SDK, cmake, CTest lines), failing on drift from `toolchain.lock.json`. `build_v03.py` rejects a missing or stale DLL **before** changing the release. Copying a DLL manually does not satisfy the receipt.

Dependencies (`native/deps/`, never packaged, never downloaded by the build): git clones of CommonLibSSE-NG, spdlog, rapidcsv and nlohmann/json at the commits in `dependencies.lock.json` (checked on every build), plus the extracted CMake 3.31.8. `fetch_cmake.py` downloads the official archive, checks the SHA-256 pinned in `toolchain.lock.json`, extracts it and deletes the archive. The Address Library file whose SHA-256 is compiled into the DLL is set by `address_library_bin` in `settings.json`.

What the DLL does on the player's weapon hit (round 20): it computes the proc magnitude at hit time
(random B, lightning best-of-N with N = 1 until N4, R from the hit flags, G(L), node percentages, blood curve,
environment, undead, exorcism, wind sneak, lightning crit) and casts it with `CastSpellImmediate`'s magnitude
override, one single-effect spell per value; on no-form hits it casts the baseline true damage, siphon, small
dispel / dispel, dispel mark and silence. The Papyrus difference patch (`ESSBController.ApplyProc`) only adds
target-side terms the DLL cannot read yet (until N3).

Layout:

- `include/HitPipeline.h` - stage 1, pure filter (a port of the Papyrus hit gates; no-form hits are element 0).
- `include/EngineFacts.h` - stage 2, pure mapping of engine answers to planner inputs: perk FormIDs and the 4-probe rank search, GLOB -> tuning field, hit flags -> attack, raw target facts.
- `include/HitMath.h` - stage 3, the pure planner: which spells, in which order, with which override.
- `include/Selection.h` - which spell record each planned cast uses.
- `include/NodeIds.h`, `include/ManifestData.h` (generated: FormIDs, node slots checked against the ESP, settings).
- `src/Plugin.cpp` - engine reads, the casts (effectiveness 1.0), log, on-screen notices (debug >= 2 shows the magnitude and 暴擊), SKSE/Papyrus glue. All mutable state is in one `State`.
- `tests/hit_pipeline_test.cpp` - groups A0 (hand-computed), A (reference table), B (wiring with a mocked engine), C (filter parity with Papyrus), D (distributions).

Generated release files:

- `package/Elements Spellblade/SKSE/Plugins/ElementsSpellblade.dll`
- `package/Elements Spellblade/SKSE/Plugins/ElementsSpellblade/manifest.json` (schema 2)

`ESSB_NativeWanted` persists the MCM preference. `ESSB_NativeHit` is the transient status (default 0, Constant flag); the DLL recomputes it on data load, game load, new game and MCM changes. Papyrus reads it as a GLOB on the hit path (never calls into the DLL there); the three `ESSBNative` functions are called only from the MCM. A fault latches native processing OFF for this process and shows a notice.

Read `../build/native-verification.md` before changing engine APIs. `../build/fix20-probes.md` is the player acceptance card. Game deployment and runtime acceptance have not been performed by this build.
