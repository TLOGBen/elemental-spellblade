Goal and acceptance:
Produce a small set of concept art images for the Skyrim SE mod "元素魔戰士 / Elements Spellblade" in D:\Game\Other\SKSE\.codex\elemental-spellblade, using your image generation tool. Report in Traditional Chinese.

What the mod is (read 元素魔戰士規劃-v0.3_alter.md sections 0, 1, 2.11, 2.12 and 5.3 for the full picture; you only need the look and feel): a melee spellblade who opens an elemental "form" with a hotkey and fights with weapon strikes; each form imbues the weapon with one of 11 elements (火 fire, 冰 frost, 雷 lightning, 地 earth, 風 wind, 血 blood, 聖 divine, 毒 poison, 水 water, 暗 darkness, 星 astral). Hits leave an element mark on the enemy; switching element on a marked enemy triggers a reaction; closing the form detonates all marks ("融斷"). Element visuals live on the weapon only — the single exception is the fire form's max-heat state 「白熱」, where the player's whole body becomes a flame source that burns nearby enemies at the cost of the player's own health (inspired by Path of Exile's "Righteous Fire").

Deliver in art-book/ (create it; it is the art book of the public GitHub repo):
  1. key-art: the spellblade mid-combat in a Skyrim setting at the moment of switching element — the blade transitioning between two elements, a marked enemy reacting. Wide, suitable as a mod-page banner.
  2. weapon-sheet: the same one-handed sword shown 11 times, one per element imbue, on a neutral background, labelled only by layout order (no text in the image), for comparing the elements side by side.
  3. white-heat: the fire form's 「白熱」 state — full-body flame aura, heat distortion, enemies close by burning; the player visibly paying a cost (strain, embers eating at the armour).
  4. marks: 11 small enemy-mark sigils, one per element, readable at a glance as floating/overlaid markers, consistent style.
  5. reaction: one example of an element reaction on a marked enemy (e.g. wind mark cut by divine: the divine strike echoing several times).
  6. skill-icons: a 3x3 sample of skill-tree node icons in one consistent style (a few elements, plus the element-less tree).
  Optional, only if the budget allows: an MCM/menu header banner.

Style: grounded Skyrim / Nordic dark fantasy, painterly concept-art finish, readable silhouettes; each element should have a distinct colour and motion language that survives at small size. Keep the set visually consistent (same character design across 1, 3, 5).

Acceptance:
  - art-book/README.md listing every image: file name, what it shows, the exact prompt used, and notes on what worked.
  - At least items 1-6 delivered as image files in art-book/.
  - No text, logos, watermarks or UI chrome inside the images; no real people; no copyrighted characters, no Bethesda or other trademarked logos; no imitation of a named living artist's style.
  - A root README.md for the public GitHub repo https://github.com/TLOGBen/elemental-spellblade (none exists yet; create it). Traditional Chinese first, with a one-line English tagline. Short: what the mod is (a few sentences from the design docs — forms, marks, reactions, 融斷, the 白熱 flame source), status (in development, Skyrim SE 1.5.97, SKSE native plugin planned), then a concept-art showcase that embeds the art-book images with relative links (art-book/<file>) and one-line captions, key-art at the top. Mark clearly that these are concept art, not in-game screenshots, and that the mod itself reuses visual effects from installed spell mods. Do not describe build steps or third-party dependencies beyond a line saying vendor files are not included.
  - Keep the total to about 6-9 images — this is exploration, not production. If a result is clearly off, one retry per item is fine.

Permission boundary:
  - Read scope: everything under D:\Game\Other\SKSE\.codex\elemental-spellblade (documents only; you do not need the game or MO2).
  - Write set (exact): art-book/** and README.md (repo root) only.
  - MUST NOT: touch any other file (another agent is working in src/, native/, build/, build_v03.py, settings.json and package/ right now); access the network except through your image generation tool.

You may change tools, commands, and technical approaches at will,
within the granted permissions and write set.
A single tool or approach being unavailable means only that this
strategy failed — switch approaches and retry. Report blocked only
when the acceptance goal is genuinely unreachable, or when you need
permissions or scope beyond what was granted.
