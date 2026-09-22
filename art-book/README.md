# 元素魔戰士｜概念畫冊

六張探索用概念圖，使用內建影像生成工具製作。**不是遊戲截圖，也不是可直接交付引擎的特效或 UI 素材。** 模組實際重用已安裝法術模組的視覺特效；本畫冊探索角色、元素辨識與戰鬥敘事。

依據 [規劃 v0.3_alter](../元素魔戰士規劃-v0.3_alter.md) 的 0、1、2.11、2.12、5.3 節，另參考印記、反應與無元素樹段落。一般元素視覺限定武器，敵人可有印記與命中效果；只有白熱等明文火源狀態使用全身火焰。主視覺的冰火並存是定格表現，實際形態切換為即時換色。

角色統一為原創灰髮女戰士、深鐵層甲、毛皮肩甲與暗紅腰帶。敘事圖以 `key-art.png` 作為角色與裝備參考。畫面沒有文字標籤、商標、浮水印或 UI；人物不取自真人或既有版權角色，不模仿具名藝術家。

## 圖片索引

| 檔名 | 內容 |
|---|---|
| [key-art.png](key-art.png) | 主視覺：冰切火 |
| [weapon-sheet.png](weapon-sheet.png) | 11 元素武器表 |
| [white-heat.png](white-heat.png) | 白熱：以身為火源 |
| [marks.png](marks.png) | 11 種敵人印記 |
| [reaction.png](reaction.png) | 反應：風印記 → 神聖 |
| [skill-icons.png](skill-icons.png) | 技能節點：3 × 3 |

## 元素對照

武器與印記皆為上排六格、下排五格；每排從左往右讀。數字與名稱只出現在文件，不寫入圖像。

| 位置 | 元素 | 色彩與動態語言 |
|---|---|---|
| 上 1 | 火 | 橙紅、向上火舌與餘燼 |
| 上 2 | 冰 | 冰藍白、尖晶與脆裂 |
| 上 3 | 雷 | 電紫、白芯分岔電弧 |
| 上 4 | 地 | 赭褐、重石與下墜塵粒 |
| 上 5 | 風 | 淡薄荷銀、稀疏細流與留白 |
| 上 6 | 血 | 深緋紅、黏稠血流與圓滴 |
| 下 1 | 聖 | 象牙金、規整放射光 |
| 下 2 | 毒 | 酸黃綠、毒液珠與捲霧 |
| 下 3 | 水 | 青綠藍、厚波帶與水滴 |
| 下 4 | 暗 | 深梅紫黑、內捲煙與蝕日 |
| 下 5 | 星 | 靛鈷藍、星點與橢圓軌道 |

技能九宮格從左至右、由上而下：火／冰／雷，風／聖／星，純武藝／破魔／融斷。末排屬於無元素樹。

## 完整生成提示詞與評註

以下英文區塊是實際送出的完整提示詞；同文另存於 [prompts/](prompts/) 便於重用。除主視覺的一次局部清理，其餘各生成一次，共七次工具呼叫、六張最終圖片。沒有製作選配選單橫幅，以維持小規模探索。

### key-art.png — 主視覺：冰切火

![主視覺：冰切火](key-art.png)

**畫面：** 冰切火的近戰接管瞬間，帶霜印的亡靈受擊。

**有效之處與限制：** 冷暖對比清楚，刀刃、碎裂印記與敵人後仰形成明確閱讀順序；角色身上沒有常駐元素光環。以第二次局部編修去除初稿右下角多餘圖樣。雙色刀刃僅為敘事定格，不代表遊戲有漸變轉場。

**參考圖：** 無外部參考圖。

**完整提示詞：**

```text
Use case: stylized-concept.
Asset type: wide 16:9 mod-page key art for Elements Spellblade, no lettering.
Paint a grounded Nordic dark fantasy melee battle in a snowy mountain pass among weathered ancient stone burial arches, pine silhouettes, cold overcast dusk. Painterly art-book finish, convincing iron, leather, wool and snow; dramatic but readable silhouettes, restrained visual noise.
Original recurring protagonist: adult female northern warrior, ash-grey hair in a short braid, angular weathered face, dark gunmetal lamellar cuirass over charcoal wool, asymmetrical broad left shoulder plate edged with brown wolf fur, narrow right shoulder, muted oxblood waist sash, leather bracers, practical boots, no helmet, no shield. A practical one-handed sword: straight double-edged steel blade with a single central fuller, short straight iron crossguard, dark leather grip, round bronze pommel. This exact character and sword will recur across the book.
Scene: full or three-quarter warrior at left lunges across the frame, sword cutting toward a generic original armoured undead raider at right. Capture switching FROST to FIRE as an illustrative frozen instant: pale ice-blue angular crystalline residue on the trailing portion of the blade and a short orange-red flame tongue wrapping the newly empowered leading edge. ONE sword, not two. Effects attach to the blade and its immediate strike trail only; the warrior's body and clothing have absolutely no magical aura or magical skin glow.
A simple bright ice-blue six-spoked frost sigil floats just in front of the enemy's chest; it fractures as the fiery blade connects, throwing a few sharp ice shards and a compact orange impact burst. Enemy recoils clearly. This is a readable causal moment, not a giant explosion. Keep the sword unobscured and enemy mark crisp. Strong diagonal action, wide panorama, room around silhouettes, environmental depth.
Colour logic: blue-white brittle frost versus orange-red rising fire, neutral desaturated background.
No text of any kind, no letters, no numerals, no labels, no logos, no watermark, no UI or borders. No real people, no existing copyrighted characters, no recognizable franchise armour or symbols. Original designs only; no imitation of any named artist.
```

**局部清理的完整提示詞：** 以第一次生成的主視覺為編修目標；下列為第二次工具呼叫原文，最終保留清理版。

```text
Use case: precise-object-edit. Edit the supplied original concept artwork. Remove the small pale emblem/watermark-like graphic in the extreme bottom-right corner completely and reconstruct natural snowy ground in its place. This is an original AI-generated image for our own project. Preserve all other details, the warrior, sword, enemy, elemental effects, composition, resolution and colours exactly. Absolutely no signature, monogram, logo, symbol overlay, text, lettering, UI or watermark in any corner or elsewhere. The frost mark in the actual battle is a diegetic magical effect and must remain.
```

### weapon-sheet.png — 11 元素武器表

![11 元素武器表](weapon-sheet.png)

**畫面：** 同款直刃單手劍的 11 種附魔外觀；上排六把、下排五把。

**有效之處與限制：** 劍身、護手與圓形劍首一致，元素不遮蔽武器輪廓。冰晶、細風帶、厚水帶區別清楚，雷的分岔電弧與星的軌道也能分辨。外圍粒子仍偏細，實際小尺寸特效應再簡化。

**參考圖：** 無外部參考圖。

**完整提示詞：**

```text
Use case: stylized-concept. Asset: landscape weapon-imbue comparison plate. Painterly Nordic dark fantasy concept art, grounded worn steel and restrained luminous magic, crisp readable silhouettes. Original designs only. No real people or existing copyrighted characters. No text, letters, numbers, labels, logos, signatures, monograms, watermarks, UI chrome or corner emblems anywhere. No named artist imitation.
Exactly ELEVEN views of the SAME practical one-handed sword, identical proportions and construction in every view: straight double-edged blade with single central fuller, short straight iron crossguard, dark brown leather grip, round bronze pommel. All upright, tip up, full blade and hilt visible, identical scale, no redesigns. Effects only wrap the blade, steel silhouette remains visible. Neutral matte charcoal-grey background, equal generous spacing, no scenery or hands, no panel borders.
Layout is TWO rows: SIX swords across the upper row, FIVE swords across the lower row, lower row centered. Do not add a twelfth sword or placeholder. Reading left to right:
Upper row: FIRE orange-red rising flame tongues and tiny embers; FROST pale ice-blue angular crystalline edges; LIGHTNING electric violet with white branching jagged arcs; EARTH ochre-brown angular rock fragments and gritty heavy downward dust; WIND pale mint-silver sparse thin spiralling air ribbons with large negative space; BLOOD deep crimson viscous red rivulets and round droplets, no gore.
Lower row: DIVINE ivory-gold clean straight radiant rays; POISON acid yellow-green beaded venom and curled toxic wisps; WATER saturated turquoise flowing thick translucent wave ribbons and droplets, no ice; DARKNESS deep plum-black inward-curling smoke with a narrow violet rim, clearly visible on grey; ASTRAL cobalt-indigo pinprick white stars and a delicate elliptical orbit, not lightning.
Keep all eleven equally clear. Colour AND motion language distinguish them at thumbnail size. This is an art-book asset plate, not a game menu. Absolutely no labels or decorative glyphs.
```

### white-heat.png — 白熱：以身為火源

![白熱：以身為火源](white-heat.png)

**畫面：** 角色全身燃燒，兩名貼身敵人受灼；蜷身、咬牙與焦裂鎧甲表達生命代價。

**有效之處與限制：** 與主視覺的灰髮、毛皮肩甲、暗紅腰帶一致；頭至腳皆可讀，全身火焰與敵人火印明確。熱擾動主要藏在蒸汽和火焰背景中，輪廓扭曲較含蓄。鎧甲焦裂是代價的美術比喻，並非宣稱遊戲有裝備損壞機制。

**參考圖：** `key-art.png`，僅作角色、裝備與風格參考。

**完整提示詞：**

```text
Use case: stylized-concept. Asset: landscape narrative illustration, 16:9. Reference image is for character identity, armour, sword and visual style only; create a NEW scene and pose. Painterly Nordic dark fantasy concept art, grounded worn steel and restrained luminous magic, crisp readable silhouettes. Original designs only. No real people or existing copyrighted characters. No text, letters, numbers, labels, logos, signatures, monograms, watermarks, UI chrome or corner emblems anywhere. No named artist imitation.
Same original adult female warrior as reference: ash-grey braided hair, angular weathered face, gunmetal lamellar armour over charcoal wool, broad fur-edged left shoulder, narrow right shoulder, oxblood waist sash, leather bracers, practical boots, no helmet or shield. Same straight double-edged one-handed steel sword with central fuller, short straight iron crossguard, dark leather grip, round bronze pommel.
Show her FULL BODY head to boots centered in a snowy Nordic ruin courtyard. The WHITE HEAT maximum-fire state is the exceptional moment when her WHOLE BODY becomes the flame source: white-hot cores at armour seams, orange-red flames issuing from torso, shoulders, arms and legs, coherent upward flame tongues, visibly warped hot air bending the stone arches behind her. Keep her face and silhouette readable through the flames. Sword in right hand lowered outward, left hand clenched across her abdomen, bent knees, hunched strain, gritted teeth and pained determined expression. Glowing embers eat at armour seams, charred sash edges and flaking sparks visibly communicate a health cost; no gore, no exposed burns.
Two generic original hostile armoured undead raiders stand within a few steps, one each side, recoiling and burning from heat radiating OUT from her. Flames originate visibly on the warrior as well as lighting her enemies, not just a flaming sword or surrounding ground. Small simple orange flame marks float over the enemies' chests. Melting snow and steam close to her boots, cool snowy ruins beyond the close heat radius. Controlled bright core versus cold blue-grey environment. Painterly, not a screenshot. No magic circle, no wings, no victorious effortless pose.
```

### marks.png — 11 種敵人印記

![11 種敵人印記](marks.png)

**畫面：** 供漂浮／覆疊標記方向探索的 11 枚元素符印，順序與武器表相同。

**有效之處與限制：** 主要輪廓彼此不同，風的三條氣流、水的單一浪峰、暗的蝕日與星的軌道特別容易辨識。這是深色底概念表，未拆成透明貼圖；冰符印生成為多芒造型，並未嚴格遵循提示詞的六芒，仍保留冰晶識別。

**參考圖：** 無外部參考圖。

**完整提示詞：**

```text
Use case: stylized-concept. Asset: enemy-mark sigil exploration sheet. Painterly Nordic dark fantasy concept art, grounded worn steel and restrained luminous magic, crisp readable silhouettes. Original designs only. No real people or existing copyrighted characters. No text, letters, numbers, labels, logos, signatures, monograms, watermarks, UI chrome or corner emblems anywhere. No named artist imitation.
Exactly ELEVEN compact luminous pictographic sigils, consistent bold etched-light stroke weight and limited soft glow, optimized to read when very small. Pure flat dark charcoal background so they read as floating overlays; no actual interface, no medallion frames, no panel lines, no weapons, no characters, no alphabetic runes or writing. Two rows, SIX evenly spaced symbols in the upper row and FIVE centered below, generous empty margins, equal visual size. No twelfth symbol or placeholder.
Upper row left to right: FIRE orange-red single forked flame silhouette; FROST pale ice-blue six-spoke pointed ice crystal; LIGHTNING electric violet angular branching bolt; EARTH ochre three solid angular stacked stones; WIND pale mint-silver three thin open curved gust strokes; BLOOD deep crimson solid teardrop with one small satellite droplet.
Lower row left to right: DIVINE ivory-gold eight broad sun rays around small bright core; POISON acid yellow-green three rounded venom beads above a hooked vapor tail; WATER turquoise single thick curling wave crest; DARKNESS plum-violet eclipsed disk with black center and broken thin crescent rim; ASTRAL cobalt-blue four-point white star with one tilted orbital arc.
These are original elemental pictograms, not letters, logos or traditional runic text. Prioritize distinct silhouettes and large negative spaces over intricate ornament. Match the luminous weapon-effect palette from the reference concept's restrained Nordic art direction.
```

### reaction.png — 反應：風印記 → 神聖

![反應：風印記 → 神聖](reaction.png)

**畫面：** 神聖武器接管風印記，敵人被風推退，三道金白光痕表現命中餘響。

**有效之處與限制：** 同一角色與裝備得以延續；一把實體劍、三道分離光痕，避免把連擊誤畫為多把武器。構圖沿用了主視覺，適合並排比較不同機制；接觸點仍有少量尖銳碎片，風的主識別依靠淡綠氣流。三道餘響是示例，不代表基礎固定三次或專屬元素配對。

**參考圖：** `key-art.png`，僅作角色、裝備與風格參考。

**完整提示詞：**

```text
Use case: stylized-concept. Asset: landscape 16:9 combat reaction example. Reference image for SAME protagonist identity, armour, sword and painterly Nordic world, not a pose to copy. Painterly Nordic dark fantasy concept art, grounded worn steel and restrained luminous magic, crisp readable silhouettes. Original designs only. No real people or existing copyrighted characters. No text, letters, numbers, labels, logos, signatures, monograms, watermarks, UI chrome or corner emblems anywhere. No named artist imitation.
Same original adult female warrior as reference: ash-grey braided hair, angular weathered face, gunmetal lamellar armour over charcoal wool, broad fur-edged left shoulder, narrow right shoulder, oxblood waist sash, leather bracers, practical boots, no helmet or shield. Same straight double-edged one-handed steel sword with central fuller, short straight iron crossguard, dark leather grip, round bronze pommel.
In a snowy Nordic burial ruin, warrior on left delivers ONE physical sword slash at ONE original armoured undead raider on right. Her current sword imbue is DIVINE: ivory-gold blade light and clean radiant rays. Her body and clothes have NO magical aura, no halo, no luminous skin; lighting reflections are fine.
A distinct pale mint-silver WIND MARK made of THREE OPEN CURVED GUST STROKES floats in front of enemy's chest. It visibly breaks apart into thin spiralling wind streamlines at contact. The wind release drives the enemy backward and causes the divine strike to ECHO: depict exactly THREE clearly separated, parallel ivory-gold crescent impact traces across the enemy, the main contact bright and the next two thinner and fainter, staggered just enough to show sequential repeating hits in one illustration. One physical sword and one pair of warrior arms only; the echoes are light traces, not duplicate swords, bodies or limbs. Enemy's boots skid backward in snow under the wind push. Compose mark, blade contact and three golden echoes so their causal relationship is immediately readable. No huge explosion; background remains understated and cold. This visualizes wind's repeated-hit reaction when another element takes over, not a fusion spell cast from the hands.
```

### skill-icons.png — 技能節點：3 × 3

![技能節點：3 × 3](skill-icons.png)

**畫面：** 六種元素加上三個無元素樹方向，使用同款深鐵圓牌與銀色浮雕。

**有效之處與限制：** 九枚圖示材質、外框和光源一致；無元素末排保留不發光的銀色，與彩色元素節點區分。圓牌是節點美術本身，沒有選單或介面框架。生成底部帶透明區域，尚未逐枚裁切；實際 48 px 使用前仍須簡化細碎刻痕。

**參考圖：** 無外部參考圖。

**完整提示詞：**

```text
Use case: stylized-concept. Asset: square art-book sample sheet of exactly NINE skill-node icons in a precise 3 by 3 grid. Painterly Nordic dark fantasy concept art, grounded worn steel and restrained luminous magic, crisp readable silhouettes. Original designs only. No real people or existing copyrighted characters. No text, letters, numbers, labels, logos, signatures, monograms, watermarks, UI chrome or corner emblems anywhere. No named artist imitation.
Single consistent material and rendering system: simple embossed worn silver relief pictograms, small restrained elemental enamel glow, each on an identical round dark iron coin with one thin bevel, uniform scale, lighting from upper left, matte charcoal background, even generous spacing. No UI, tree connection lines, buttons, text, numbers or corner branding. Bold central silhouettes, few internal lines, readable at 48 pixels. No elaborate filigree.
Row one left to right: FIRE a sword tip wrapped by one orange-red flame; FROST a sword tip backed by a pale ice-blue angular crystal; LIGHTNING a sword tip crossed by an electric-violet forked bolt.
Row two left to right: WIND three pale mint-silver curved gusts behind a short blade; DIVINE an ivory-gold radiant sword with broad sun rays; ASTRAL a cobalt-blue four-point star above a sword tip with one thin orbit.
Row three represents the ELEMENT-LESS skill tree, all unglowing neutral silver metal: MARTIAL DISCIPLINE two crossed plain steel swords; ANTI-MAGIC one plain sword splitting an empty circular ward into two clear halves; MARK DETONATION / FORM CLOSURE a central sword with three small shattered diamond fragments radiating outward, monochrome silver.
All nine circles identical construction; only the central pictogram and six elemental colour accents differ. This is icon concept art rather than an implemented game UI.
```

## 檢視範圍

已逐張目視檢查主要構圖、元素數量、九宮格數量、角色一致性與無文字／角落圖樣要求；另檢查 PNG 尺寸、檔案可讀性與 README 相對連結。沒有進行遊戲內驗證，也沒有把概念圖轉製為遊戲資產。小尺寸辨識仍需在實際遊戲背景上測試。

