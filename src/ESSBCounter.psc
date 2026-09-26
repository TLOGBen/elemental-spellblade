Scriptname ESSBCounter extends ActiveMagicEffect
{破魔印 AME（round 23 起不做事）。

反咒（v0.4 5.1）改由 DLL 的施法事件判定（TESSpellCastEvent：施法者帶你的破魔印時，受該次施法消耗魔力 ×（100% +
2%／無元素樹等級）的真實傷害，native/include/Hurt.h PlanSpellCast；裁定 R7）。原本在這裡替控制器登記的施法動畫事件
連同控制器的 StartCounter／StopCounter／OnAnimationEvent 一起刪除。腳本與屬性留著，是因為破魔印效果的 VMAD 與舊存檔
裡還在跑的 AME 都指向它；舊 AME 的事件一律不做事。}

Quest Property Controller Auto
{ESSB_MainQuest；玩家 ReferenceAlias 為 alias 0}

Event OnEffectStart(Actor akTarget, Actor akCaster)
EndEvent

Event OnEffectFinish(Actor akTarget, Actor akCaster)
EndEvent
