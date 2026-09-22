# fix round 4：離線傷害路徑證據

| 傷害路徑 | B／係數來源 → 最終入口 | BaseDamageMult 次數 |
|---|---|---:|
| 普通、重擊、雙生附傷 | RollBase → ApplyProc → DoCombatSpellApply | 1 |
| 開印／終焉、反擊、自燃、連鎖、節點追加傷害 | BaseMax／ReactDamage → ApplyDamage → ApplyDamageRaw | 1 |
| 融斷爆傷 | OnFormClosed → EndMark → ESSBReactions.End（含 K_sync）→ 各元素終焉 → ApplyDamage → Raw | 1 |
| 毒 DoT（含催毒、毒霧加層） | Status.Tick → BaseMax(Poison) × PoisonDotK → ApplyDamage → Raw | 1 |
| 流血 DoT | Status.Tick → BleedPerLayer → ApplyDamage → Raw | 1 |
| 血潮剩餘流血 | EndBlood → BleedRemaining(BleedPerLayer) → ApplyDamage → Raw | 1 |
| 延遲死咒／處刑追加段 | EndDark 儲存未乘值 → Status.Tick → ApplyDamage；AfterDeathCurse 收到原始 amount，再各自 ApplyDamage | 每一傷害段 1 |
| 星痕／落地延遲傷害 | 未乘值／層數保留於狀態 → DetonateAstral／OnLanding → ApplyDamage → Raw | 1 |
| 傷害領域 | 火域 → OnIgnite；冰原／地裂 → 狀態及反應；毒霧 → 毒層；死域 → ApplyDamage；星域 → 目標增幅 | 每一傷害段 1 |
| 星斷（B_max 轉真傷） | Fall → FallHit → ApplyTrueDamage(aiTree=10) 的專用分支 | 1 |
| 無元素樹真傷 | ApplyTrueDamage(aiTree=11／預設值) | 0（依規劃 2.7 排除） |
| 放血當前生命百分比 | ApplyBleedDrain → ApplyUtil(7) | 0（原係數與血位效果保留） |
| 過熱自傷、處決 | AddSelf → ApplyDamageRaw（自身 HP 比例）；Execute → TrueSpell | 0（不源自 B） |
| 回血／回魔／回耐、削魔／削耐、控制效果 | ApplyUtil；B_max 類效果仍讀同一張表 | 0（不是元素生命傷害） |

僅 `ApplyProc`、`ApplyDamage` 與 `ApplyTrueDamage(aiTree=10)` 讀取倍率，Raw／公式工廠／狀態容器不讀。Papyrus Float 參數按值傳入；傷害套用不會改寫呼叫端保存的 amount，因此連鎖、反彈與剩餘 DoT 不會持有已乘倍率的值。

## 回歸結果

- init: 16/16 partial lift states repaired; repeated init preserves existing arrays
- init: all 65 controller arrays independently repaired; registry reentry preserves identity
- old source reproduces None sibling access in ArmUpdate; new independent guards repair it
- OnInit (including duplicate delivery) only schedules; initial OnUpdate calls Setup before array access
- 11/11 elements: real ApplyProc normal/power and ReactDamage -> ApplyDamage -> Raw scale once at M=1 and 2.5
- real Status.Tick: bleed 1.2 x 5 ticks, poison 2.0 x 6 ticks; M=2.5 scales once; durations unchanged
- raw overheat / noform true / current-health bleed drain unscaled; B-derived astral true scales once
- real EndBlood: remaining-bleed uses the same BleedDotK, no stored multiplier, one final application
- static: exactly 3 multiplier reads, Raw callers limited to ApplyDamage and overheat AddSelf; native spell delivery centralized

## 完整 grep 呼叫表（出貨白名單）

| 位置 | 函式 | 呼叫／公式 |
|---|---|---|
| `src/ESSBStatus.psc:761` | `Tick` | `Ctl.ApplyDamage(6, bleed * ESSBElem2.BleedPerLayer(Ctl), Holder)` |
| `src/ESSBStatus.psc:769` | `Tick` | `Float venom = ESSBReactions.BaseMax(Ctl, 8) * Ctl.PoisonDotK.GetValue() * poison * Ctl.GetDamageMult(8) * ESSBNodes.OmniMult(Ctl) \` |
| `src/ESSBStatus.psc:775` | `Tick` | `Ctl.ApplyDamage(8, venom, Holder)` |
| `src/ESSBStatus.psc:815` | `Tick` | `Ctl.ApplyDamage(10, amount, Holder)` |
| `src/ESSBReactions.psc:43` | `RollBase` | `Float low = BaseMin(akCtl, aiElement)` |
| `src/ESSBReactions.psc:44` | `RollBase` | `Float high = BaseMax(akCtl, aiElement)` |
| `src/ESSBReactions.psc:54` | `ReactDamage` | `Return BaseMax(akCtl, aiElement) * afK * akCtl.GetDamageMult(aiElement)` |
| `src/ESSBReactions.psc:75` | `Open` | `akCtl.ApplyDamage(1, ReactDamage(akCtl, 1, 0.5) * mult, akTarget)` |
| `src/ESSBReactions.psc:103` | `Open` | `akCtl.Leech(BaseMax(akCtl, 6) * akCtl.GetBloodLeechRatio() * mult)` |
| `src/ESSBReactions.psc:291` | `EndBlood` | `remaining = akStatus.BleedRemaining(ESSBElem2.BleedPerLayer(akCtl))` |
| `src/ESSBReactions.psc:306` | `EndBlood` | `akCtl.ApplyDamage(6, amount, akTarget)` |
| `src/ESSBNodes.psc:90` | `OnSyncStage` | `Float amount = ESSBReactions.BaseMax(akCtl, akCtl.CurrentElement.GetValueInt()) * 2.0` |
| `src/ESSBNodes.psc:214` | `OnEndReward` | `akCtl.ApplyUtil(5, ESSBReactions.BaseMax(akCtl, aiElement), 0, player)` |
| `src/ESSBNoForm.psc:67` | `OnMartialHit` | `akCtl.ApplyTrueDamage(base, akTarget, 11, False)` |
| `src/ESSBNoForm.psc:77` | `OnMartialHit` | `akCtl.ApplyTrueDamage(base * 0.03 * finisher, akTarget, 11, False)` |
| `src/ESSBNoForm.psc:83` | `OnMartialHit` | `akCtl.ApplyTrueDamage(base * 2.0, akTarget, 11, False)` |
| `src/ESSBNoForm.psc:162` | `OnManaBreak` | `akCtl.ApplyTrueDamage(trueAmount, akTarget, 11, False)` |
| `src/ESSBNoForm.psc:246` | `OnCounterSpell` | `akCtl.ApplyTrueDamage(afCost * ratio, akTarget)` |
| `src/ESSBNoForm.psc:312` | `OnBurst` | `akCtl.ApplyUtil(5, ESSBReactions.BaseMax(akCtl, aiElement) * 0.5 * aiMarks, 0, player)` |
| `src/ESSBElem.psc:253` | `OpenFire` | `Float amount = ESSBReactions.BaseMax(akCtl, 1) * 0.5 * akCtl.GetDamageMult(1)` |
| `src/ESSBElem.psc:257` | `OpenFire` | `akCtl.ApplyDamage(1, amount, nearby[index])` |
| `src/ESSBElem.psc:305` | `OpenShock` | `akCtl.ApplyUtil(5, ESSBReactions.BaseMax(akCtl, 3), 0, player)` |
| `src/ESSBElem.psc:396` | `OnIgnite` | `Float amount = ESSBReactions.BaseMax(akCtl, 1) * IgniteMult(akCtl, aiHeat) * akCtl.GetDamageMult(1)` |
| `src/ESSBElem.psc:397` | `OnIgnite` | `akCtl.ApplyDamage(1, amount, akTarget)` |
| `src/ESSBElem.psc:402` | `OnIgnite` | `akCtl.ApplyUtil(4, ESSBReactions.BaseMax(akCtl, 1) * 2.0, 0, player)` |
| `src/ESSBElem.psc:425` | `Detonate` | `Float amount = ESSBReactions.BaseMax(akCtl, 1) * afMult * mult * akCtl.GetDamageMult(1) * SignatureMult(akCtl, 1)` |
| `src/ESSBElem.psc:426` | `Detonate` | `akCtl.ApplyDamage(1, amount, akTarget)` |
| `src/ESSBElem.psc:436` | `Detonate` | `akCtl.ApplyDamage(1, amount * 0.5, nearby[index])` |
| `src/ESSBElem.psc:463` | `Shatter` | `akCtl.ApplyDamage(2, ESSBReactions.ReactDamage(akCtl, 2, 5.0) * afMult * signature, akTarget)` |
| `src/ESSBElem.psc:469` | `Shatter` | `akCtl.ApplyDamage(2, ESSBReactions.ReactDamage(akCtl, 2, 2.5) * afMult * signature, akTarget)` |
| `src/ESSBElem.psc:478` | `Shatter` | `akCtl.ApplyDamage(2, ESSBReactions.ReactDamage(akCtl, 2, 1.0) * afMult * signature, akTarget)` |
| `src/ESSBElem.psc:540` | `Discharge` | `akCtl.ApplyDamage(3, amount, akTarget)` |
| `src/ESSBElem.psc:555` | `Discharge` | `akCtl.ApplyDamage(3, amount * jumpRatio, jump[index])` |
| `src/ESSBElem.psc:769` | `OnTick` | `akCtl.ApplyUtil(5, ESSBReactions.BaseMax(akCtl, 3) * charge, 0, player)` |
| `src/ESSBElem2.psc:190` | `OnEarthHit` | `akCtl.ApplyDamage(4, ESSBReactions.ReactDamage(akCtl, 4, 1.5), akTarget)` |
| `src/ESSBElem2.psc:223` | `OnBloodHit` | `Float amount = ESSBReactions.BaseMax(akCtl, 6) * akCtl.GetBloodLeechRatio() * akCtl.GetDamageMult(6)` |
| `src/ESSBElem2.psc:235` | `OnDivineHit` | `akCtl.ApplyUtil(4, ESSBReactions.BaseMax(akCtl, 7) * 0.02 * heal, 0, player)` |
| `src/ESSBElem2.psc:243` | `OnDivineHit` | `akCtl.ApplyDamage(7, ESSBReactions.ReactDamage(akCtl, 7, 0.5) \` |
| `src/ESSBElem2.psc:252` | `OnDivineHit` | `HealAllies(akCtl, ESSBReactions.BaseMax(akCtl, 7))` |
| `src/ESSBElem2.psc:352` | `OpenBlood` | `Float heal = ESSBReactions.BaseMax(akCtl, 6) * 0.5` |
| `src/ESSBElem2.psc:382` | `OpenDivine` | `akCtl.ApplyUtil(4, ESSBReactions.BaseMax(akCtl, 7) * 0.05 * rank, 0, player)` |
| `src/ESSBElem2.psc:398` | `OpenDivine` | `HealAllies(akCtl, ESSBReactions.BaseMax(akCtl, 7))` |
| `src/ESSBElem2.psc:402` | `OpenDivine` | `akCtl.ApplyUtil(4, ESSBReactions.BaseMax(akCtl, 7), 0, player)` |
| `src/ESSBElem2.psc:464` | `OnFormOpened` | `akCtl.ApplyUtil(4, ESSBReactions.BaseMax(akCtl, 7) * 2.0, 0, player)` |
| `src/ESSBElem2.psc:465` | `OnFormOpened` | `HealAllies(akCtl, ESSBReactions.BaseMax(akCtl, 7) * 2.0)` |
| `src/ESSBElem2.psc:513` | `QuakeOne` | `akCtl.ApplyDamage(4, afAmount, akTarget)` |
| `src/ESSBElem2.psc:539` | `OnEarthRetaliate` | `akCtl.ApplyDamage(4, ESSBReactions.ReactDamage(akCtl, 4, 2.0), akAttacker)` |
| `src/ESSBElem2.psc:584` | `WindBladeOne` | `akCtl.ApplyDamage(5, amount, akTarget)` |
| `src/ESSBElem2.psc:649` | `BleedPerLayer` | `Return ESSBReactions.BaseMax(akCtl, 6) * akCtl.BleedDotK.GetValue() * akCtl.GetDamageMult(6) \` |
| `src/ESSBElem2.psc:707` | `Judge` | `akCtl.ApplyDamage(7, amount, akTarget)` |
| `src/ESSBElem2.psc:852` | `EndDivineNodes` | `akCtl.ApplyDamage(7, ESSBReactions.ReactDamage(akCtl, 7, 5.0), prey[index])` |
| `src/ESSBElem2.psc:1008` | `OnAsh` | `akCtl.ApplyUtil(5, ESSBReactions.BaseMax(akCtl, 7) * 2.0, 0, player)` |
| `src/ESSBElem2.psc:1016` | `OnAsh` | `akCtl.ApplyDamage(7, ESSBReactions.ReactDamage(akCtl, 7, 1.0), nearby[index])` |
| `src/ESSBElem3.psc:20` | `` | `真實傷害（星斷）走 ApplyTrueDamage(amount, target, 樹)。}` |
| `src/ESSBElem3.psc:301` | `OnAstralHit` | `akCtl.ApplyUtil(5, ESSBReactions.BaseMax(akCtl, 11), 0, player)` |
| `src/ESSBElem3.psc:305` | `OnAstralHit` | `akCtl.ApplyDamage(11, ESSBReactions.ReactDamage(akCtl, 11, 0.35), akTarget)` |
| `src/ESSBElem3.psc:343` | `OpenPoison` | `akCtl.ApplyUtil(4, ESSBReactions.BaseMax(akCtl, 8) * 0.5, 0, player)` |
| `src/ESSBElem3.psc:426` | `OpenAstral` | `akCtl.ApplyUtil(5, ESSBReactions.BaseMax(akCtl, 11), 0, player)` |
| `src/ESSBElem3.psc:655` | `AfterDeathCurse` | `akCtl.ApplyDamage(10, afAmount * 2.0, akTarget)` |
| `src/ESSBElem3.psc:838` | `OnAstralDetonate` | `akCtl.ApplyUtil(19, ESSBReactions.BaseMax(akCtl, 11) * aiLayers, 10, player)` |
| `src/ESSBElem3.psc:842` | `OnAstralDetonate` | `akCtl.ApplyUtil(4, ESSBReactions.BaseMax(akCtl, 11) * aiLayers, 0, player)` |
| `src/ESSBElem3.psc:868` | `FallHit` | `akCtl.ApplyTrueDamage(amount * 0.6, akTarget, 10)` |
| `src/ESSBElem3.psc:870` | `FallHit` | `akCtl.ApplyDamage(11, amount, akTarget)` |
| `src/ESSBElem3.psc:881` | `DetonateAstral` | `akCtl.ApplyDamage(11, amount, akTarget)` |
| `src/ESSBElem3.psc:1068` | `PoisonFormTick` | `heal = heal + ESSBReactions.BaseMax(akCtl, 8) * 0.5` |
| `src/ESSBElem3.psc:1157` | `OnKill` | `akCtl.ApplyUtil(5, ESSBReactions.BaseMax(akCtl, 10) * curse, 0, player)` |
| `src/ESSBElem3.psc:1199` | `OnShadowBody` | `akCtl.ApplyUtil(5, ESSBReactions.BaseMax(akCtl, 10) * 2.0, 0, player)` |
| `src/ESSBController.psc:976` | `OnWeaponHit` | `ApplyProc(targetActor, element, power, sneak, opening)` |
| `src/ESSBController.psc:983` | `OnWeaponHit` | `ApplyProc(targetActor, element, power, sneak, False)` |
| `src/ESSBController.psc:993` | `OnWeaponHit` | `ApplyDamage(PrevElement, ESSBReactions.BaseMax(Self, PrevElement) * echo \` |
| `src/ESSBController.psc:1037` | `ApplyProc` | `Float magnitude = ESSBReactions.RollBase(Self, aiElement)` |
| `src/ESSBController.psc:1060` | `ApplyProc` | `player.DoCombatSpellApply(procSpell, akTarget)` |
| `src/ESSBController.psc:1098` | `OnNoFormHit` | `ApplyDamage(EmberElem, ESSBReactions.BaseMax(Self, EmberElem) * ember * GetDamageMult(EmberElem), akTarget)` |
| `src/ESSBController.psc:1242` | `ApplyMark` | `player.DoCombatSpellApply(markSpell, akTarget)` |
| `src/ESSBController.psc:1640` | `EnsureStatus` | `player.DoCombatSpellApply(StatusHostSpell, akTarget)` |
| `src/ESSBController.psc:1816` | `ApplyDamage` | `ApplyDamageRaw(aiElement, afAmount * BaseDamageMult.GetValue() * GLevel(ESSBNodes.TreeOf(aiElement)) \` |
| `src/ESSBController.psc:1838` | `ApplyDamageRaw` | `player.DoCombatSpellApply(reactSpell, akTarget)` |
| `src/ESSBController.psc:1867` | `ApplyTrueDamage` | `player.DoCombatSpellApply(TrueSpell, akTarget)` |
| `src/ESSBController.psc:1883` | `ApplyManaBreakMark` | `player.DoCombatSpellApply(ManaBreakSpell, akTarget)` |
| `src/ESSBController.psc:1902` | `ApplySilenceSpell` | `player.DoCombatSpellApply(SilenceSpell, akTarget)` |
| `src/ESSBController.psc:1927` | `ApplyUtil` | `player.DoCombatSpellApply(utilSpell, akTarget)` |
| `src/ESSBController.psc:1948` | `Execute` | `player.DoCombatSpellApply(TrueSpell, akTarget)` |
| `src/ESSBController.psc:2396` | `AddSelf` | `ApplyDamageRaw(1, player.GetActorValueMax("Health") * 0.1, player)` |
| `src/ESSBController.psc:2533` | `MarkEngaged` | `player.DoCombatSpellApply(EngagedSpell, akTarget)` |
| `src/ESSBController.psc:3393` | `TickDomain` | `ApplyUtil(4, ESSBReactions.BaseMax(Self, 6), 0, player)` |
| `src/ESSBController.psc:3396` | `TickDomain` | `ApplyUtil(4, ESSBReactions.BaseMax(Self, 7), 0, player)` |
| `src/ESSBController.psc:3397` | `TickDomain` | `ApplyUtil(5, ESSBReactions.BaseMax(Self, 7), 0, player)` |
| `src/ESSBController.psc:3400` | `TickDomain` | `ApplyUtil(4, ESSBReactions.BaseMax(Self, 9), 0, player)` |
| `src/ESSBController.psc:3401` | `TickDomain` | `ApplyUtil(6, ESSBReactions.BaseMax(Self, 9), 0, player)` |
| `src/ESSBController.psc:3438` | `TickDomain` | `ApplyDamage(10, ESSBReactions.ReactDamage(Self, 10, 0.5), victim)` |
| `src/ESSBController.psc:3706` | `OnLanding` | `ApplyDamage(5, afAmount, akTarget)` |
| `src/ESSBController.psc:3955` | `ApplyCleanse` | `player.DoCombatSpellApply(chosen, player)` |
| `src/ESSBController.psc:4013` | `ApplyStrip` | `player.DoCombatSpellApply(StripSpell, akTarget)` |
| `src/ESSBController.psc:4083` | `ApplyFear` | `player.DoCombatSpellApply(FearSpell, akTarget)` |
| `src/ESSBController.psc:4094` | `ApplyFrenzy` | `player.DoCombatSpellApply(FrenzySpell, akTarget)` |
| `src/ESSBController.psc:4192` | `ApplyReanimate` | `player.DoCombatSpellApply(ReanimateSpell, akTarget)` |
| `src/ESSBController.psc:4296` | `ApplyAsh` | `player.DoCombatSpellApply(AshSpell, akTarget)` |
| `src/ESSBController.psc:4313` | `ApplyInherit` | `player.DoCombatSpellApply(InheritSpell, player)` |
| `src/ESSBGuard.psc:78` | `OnHitEx` | `Ctl.ApplyUtil(5, ESSBReactions.BaseMax(Ctl, 11) * Ctl.GLevel(11), 0, player)` |
| `src/ESSBGuard.psc:140` | `OnHitEx` | `Ctl.ApplyDamage(1, ESSBReactions.ReactDamage(Ctl, 1, 1.0), attacker)` |

非 Skyrim VM 實機測試；原生函式使用明示 mock。歷史 `src/ESSBPlayerAlias.psc` 不在 17 支出貨白名單，未修改也未部署。
