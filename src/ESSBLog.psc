Scriptname ESSBLog Hidden
{元素魔戰士 除錯紀錄（規劃 v0.3 第 6.1 節）。

Papyrus 的全域函式不能持有狀態，所以本腳本只做「等級判定 + Debug.Trace 輸出」。
每秒 20 行的節流需要計數器，改由 ESSBController.LogThrottled() 持有並對外提供；
等級 2 以上（命中、詳細）一律走 controller，等級 1 的低頻事件走這裡。

固定格式：[ESSB][機制][L等級] 訊息}

; ESSB_DebugLevel 的本地 FormID 固定為 0x000811（見 build/v03-formids.json 的配置表）。
Int Function Level() Global
	GlobalVariable level = Game.GetFormFromFile(0x00000811, "Elements Spellblade.esp") as GlobalVariable
	If !level
		Return 0
	EndIf
	Return level.GetValueInt()
EndFunction

Function Log(Int aiLevel, String asMechanism, String asMessage) Global
	If Level() < aiLevel
		Return
	EndIf
	Debug.Trace("[ESSB][" + asMechanism + "][L" + aiLevel + "] " + asMessage)
EndFunction
