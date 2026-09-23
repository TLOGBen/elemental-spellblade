# ElementsSpellblade native / Round 19b

Runtime: **Skyrim SE 1.5.97.0 + SKSE 2.0.20** only. No entry-51 fallback, hooks, trampolines or code patches.
Needs the VC++ 2015-2022 runtime >= 14.44 (`/MD`, built with toolset 14.44).

From the workspace root:

```powershell
python -B native/fetch_cmake.py   # once, only if native/deps/cmake-3.31.8-windows-x86_64 is missing
python -B native/build.py
python build_v03.py
```

`native/build.py` uses Visual Studio 2022 x64 MSVC and the pinned CMake 3.31.8 in `native/deps/` (the local VS install has no CMake component). It regenerates `include/ManifestData.h` and the truth table `build/fix19-truth.csv`, builds the DLL and `hit_pipeline_test`, runs CTest, and writes `out/build-receipt.json` with what was actually used (cl version and path, SDK, cmake, CTest lines), failing on drift from `toolchain.lock.json`. `build_v03.py` rejects a missing or stale DLL **before** changing the release. Copying a DLL manually does not satisfy the receipt.

Dependencies (`native/deps/`, never packaged, never downloaded by the build): git clones of CommonLibSSE-NG, spdlog, rapidcsv and nlohmann/json at the commits in `dependencies.lock.json` (checked on every build), plus the extracted CMake 3.31.8. `fetch_cmake.py` downloads the official archive, checks the SHA-256 pinned in `toolchain.lock.json`, extracts it and deletes the archive. The Address Library file whose SHA-256 is compiled into the DLL is set by `address_library_bin` in `settings.json`.

Layout:

- `include/Selection.h` - pure selection `Input -> Key`.
- `include/HitPipeline.h` - pure filter (a port of the Papyrus hit gates) and `BuildInput`, which asks the engine the same CTDA predicates the old entry-51 segments used.
- `src/Plugin.cpp` - engine reads, `CastSpellImmediate` (effectiveness 1.0), log, on-screen notices, SKSE/Papyrus glue. All mutable state is in one `State`.
- `tests/hit_pipeline_test.cpp` - groups A (production truth table), B (wiring), C (filter parity with Papyrus), D (lightning distribution).

Generated release files:

- `package/Elements Spellblade/SKSE/Plugins/ElementsSpellblade.dll`
- `package/Elements Spellblade/SKSE/Plugins/ElementsSpellblade/manifest.json`

`ESSB_NativeWanted` persists the MCM preference. `ESSB_NativeHit` is the transient status (default 0, Constant flag); the DLL recomputes it on data load, game load, new game and MCM changes. Papyrus reads it as a GLOB on the hit path (never calls into the DLL there); the three `ESSBNative` functions are called only from the MCM. A fault latches native processing OFF for this process and shows a notice.

Read `../build/native-verification.md` before changing engine APIs. `../build/fix19-probes.md` is the player acceptance card. Game deployment and runtime acceptance have not been performed by this build.
