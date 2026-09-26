Scriptname ESSBTrees extends ReferenceAlias
{元素魔戰士 技能樹（規劃 v0.3 第 3、3.1、4、5.1–5.13 節）。

13 棵樹（0–10 元素、11 無元素、12 全元素通用），每棵樹三條路線、每路線五階。
每階一個主線節點（15 階 perk 鏈，每點一階）與一到四個分支（單一 perk，各 5 點）。
節點的 FormID 由 build_v03.py 固定配置，執行期以 Game.GetFormFromFile 取回：
  主線 0x004000 + ((tree × 3 + route) × 5 + tier) × 15 + rank
  分支 0x002000 + ((tree × 3 + route) × 5 + tier) × 4 + n
所以本腳本不需要幾千個 VMAD 屬性，也不需要 FormList。

點數：CSF 的 perkPoints 是選單（根）層級的全域變數，所以一棵樹一個設定檔、
一個 ESSB_Pts_<tree>。CSF 每買一個節點只扣 1 點；分支要 5 點，
所以選單關閉後由 Reconcile() 補扣 4 點，補不出來就把該分支退回。

效能：沒有每幀迴圈、沒有忙等。RefreshTree 只在選單關閉、洗點與機制前線主動要求時跑；
13 棵樹以 120 + 75 格分塊保存 rank／branch，命中直接索引。未初始化的快取才即時查詢；
原三槽保留作 RefreshTree 的建置暫存，衍生值在 load／form／購點／洗點／升級／MCM 事件刷新。}

; ---------------------------------------------------------------- 屬性

ESSBController Property Controller Auto
{同一個 Player 別名上的第一個腳本}
GlobalVariable Property CurrentElement Auto
GlobalVariable Property FormActive Auto
GlobalVariable Property DebugLevel Auto
GlobalVariable Property ShowMenu Auto
{CSF 選單層級旗標，腳本不讀，留著讓屬性與設定檔一一對應}
GlobalVariable Property XPPerHit Auto
{每次有效命中給的 CSF 技能使用量，預設 1.0}

GlobalVariable[] Property LvlGlobals Auto
GlobalVariable[] Property RatioGlobals Auto
GlobalVariable[] Property PtsGlobals Auto
GlobalVariable[] Property ColorGlobals Auto
GlobalVariable[] Property ShowLvlGlobals Auto
GlobalVariable[] Property RespecGlobals Auto
{洗點冷卻時戳（遊戲日），預設 -10 代表從未洗過}

; ---------------------------------------------------------------- 常數

Int Property TREE_COUNT = 13 AutoReadOnly
Int Property ROUTE_COUNT = 3 AutoReadOnly
Int Property TIER_COUNT = 5 AutoReadOnly
Int Property MAIN_MAX_RANK = 15 AutoReadOnly
Int Property BRANCH_SLOTS = 4 AutoReadOnly
Int Property BRANCH_COST = 5 AutoReadOnly
Int Property MAIN_BASE = 16384 AutoReadOnly
{0x004000}
Int Property BRANCH_BASE = 8192 AutoReadOnly
{0x002000}
Int Property CACHE_SLOTS = 3 AutoReadOnly
Int Property XP_PER_SECOND = 10 AutoReadOnly
String Property PLUGIN_FILE = "Elements Spellblade.esp" AutoReadOnly
String Property MENU_NAME = "StatsMenu" AutoReadOnly
{CSF 3.x 沒有對外公開選單名稱；CustomSkills.dll 的 MenuSetup 修補的是原版 StatsMenu，
所以這裡用 StatsMenu，並在 Reconcile 前後各留一道保險（重複開啟時先結清上一次）。}

; ---------------------------------------------------------------- 內部狀態

Actor PlayerRef
Bool Ready
Bool TablesInitialised
String[] SkillIds
String[] TreeNames

; 節點快取：三個槽，各 15 格（3 路線 × 5 階）。
Int[] CacheTree
Int[] CacheRank
Int[] CacheBranch
Int CacheNext
Int[] AllRankA
Int[] AllRankB
Int[] AllBranchA
Int[] AllBranchB
Bool[] AllValid
Int[] LevelCache
Bool SettingsBusy
Int QueuedTree = -1
Bool OpeningMenu
Float MenuRequestedAt

; 選單前的分支快照（15 格位元遮罩），只對 PendingTree 有效。
Int[] SnapBranch
Int PendingTree = -1

Float XPWindowStart
Int XPCount

; ---------------------------------------------------------------- 生命週期

Event OnInit()
	If !Controller || !Controller.IsCurrentController() || Controller.StateBroken
		Return
	EndIf
	RegisterForSingleUpdate(3.0)
EndEvent

Event OnPlayerLoadGame()
	If !Controller || !Controller.IsCurrentController() || Controller.StateBroken
		Return
	EndIf
	Ready = False
	XPWindowStart = Utility.GetCurrentRealTime()
	XPCount = 0
	SettingsBusy = False
	QueuedTree = -1
	OpeningMenu = False
	If AllValid
		Int i = 0
		While i < 13
			AllValid[i] = False
			i += 1
		EndWhile
	EndIf
	ClearShowMenu()
	RegisterForSingleUpdate(3.0)
EndEvent

Event OnUpdate()
	If !Controller || !Controller.IsCurrentController() || Controller.StateBroken
		Return
	EndIf
	If OpeningMenu && Utility.GetCurrentRealTime() - MenuRequestedAt >= 1.0
		OpeningMenu = False
	EndIf
	If !Ready
		Setup()
	EndIf
	If QueuedTree >= 0
		; Wait for the close event if a slow MessageBox outlives the first deferred update.
		If UI.IsMenuOpen("MessageBoxMenu")
			Return
		EndIf
		Int tree = QueuedTree
		OpeningMenu = True
		QueuedTree = -1
		OpenTree(tree, True)
	EndIf
EndEvent

; CSF treats a non-zero showMenu global as "open the tree now". Trees are opened through the API,
; so keep it at 0 (older saves stored the former default of 1).
Function ClearShowMenu()
	If !Controller || !Controller.IsCurrentController() || Controller.StateBroken
		Return
	EndIf
	If ShowMenu && ShowMenu.GetValueInt() != 0
		ShowMenu.SetValueInt(0)
	EndIf
EndFunction

Function Setup()
	If !Controller || !Controller.IsCurrentController() || Controller.StateBroken
		Return
	EndIf
	ClearShowMenu()
	Actor player = GetActorReference()
	If !player
		RegisterForSingleUpdate(5.0)
		Return
	EndIf
	PlayerRef = player
	InitTables()
	If Controller.StateBroken
		Return
	EndIf
	RefreshActive(CurrentTree())
	CustomSkills_AliasExt.RegisterForCustomSkillIncrease(Self)
	Ready = True
	If Controller.CachedDebugLevel >= 1
		Controller.LogEvent(1, "trees", "ready trees=" + TREE_COUNT + " api=" + CustomSkills.GetAPIVersion())
	EndIf
EndFunction

Function InitTables()
	If !Controller || !Controller.IsCurrentController() || Controller.StateBroken || TablesInitialised
		Return
	EndIf
	If !SkillIds
		SkillIds = new String[13]
	EndIf
	If !SkillIds
		Controller.BreakState()
		Return
	EndIf
	If !TreeNames
		TreeNames = new String[13]
	EndIf
	If !TreeNames
		Controller.BreakState()
		Return
	EndIf
	If !CacheTree
		CacheTree = new Int[3]
	EndIf
	If !CacheTree
		Controller.BreakState()
		Return
	EndIf
	If !CacheRank
		CacheRank = new Int[45]
	EndIf
	If !CacheRank
		Controller.BreakState()
		Return
	EndIf
	If !CacheBranch
		CacheBranch = new Int[45]
	EndIf
	If !CacheBranch
		Controller.BreakState()
		Return
	EndIf
	If !SnapBranch
		SnapBranch = new Int[15]
	EndIf
	If !SnapBranch
		Controller.BreakState()
		Return
	EndIf
	If !LvlGlobals || LvlGlobals.Length != 13
		Controller.BreakState()
		Return
	EndIf
	Int checkLvlGlobals = 0
	While checkLvlGlobals < 13
		If !LvlGlobals[checkLvlGlobals]
			Controller.BreakState()
			Return
		EndIf
		checkLvlGlobals += 1
	EndWhile
	If !RatioGlobals || RatioGlobals.Length != 13
		Controller.BreakState()
		Return
	EndIf
	Int checkRatioGlobals = 0
	While checkRatioGlobals < 13
		If !RatioGlobals[checkRatioGlobals]
			Controller.BreakState()
			Return
		EndIf
		checkRatioGlobals += 1
	EndWhile
	If !PtsGlobals || PtsGlobals.Length != 13
		Controller.BreakState()
		Return
	EndIf
	Int checkPtsGlobals = 0
	While checkPtsGlobals < 13
		If !PtsGlobals[checkPtsGlobals]
			Controller.BreakState()
			Return
		EndIf
		checkPtsGlobals += 1
	EndWhile
	If !ColorGlobals || ColorGlobals.Length != 13
		Controller.BreakState()
		Return
	EndIf
	Int checkColorGlobals = 0
	While checkColorGlobals < 13
		If !ColorGlobals[checkColorGlobals]
			Controller.BreakState()
			Return
		EndIf
		checkColorGlobals += 1
	EndWhile
	If !ShowLvlGlobals || ShowLvlGlobals.Length != 13
		Controller.BreakState()
		Return
	EndIf
	Int checkShowLvlGlobals = 0
	While checkShowLvlGlobals < 13
		If !ShowLvlGlobals[checkShowLvlGlobals]
			Controller.BreakState()
			Return
		EndIf
		checkShowLvlGlobals += 1
	EndWhile
	If !RespecGlobals || RespecGlobals.Length != 13
		Controller.BreakState()
		Return
	EndIf
	Int checkRespecGlobals = 0
	While checkRespecGlobals < 13
		If !RespecGlobals[checkRespecGlobals]
			Controller.BreakState()
			Return
		EndIf
		checkRespecGlobals += 1
	EndWhile
	SkillIds[0] = "ESSB_fire"
	SkillIds[1] = "ESSB_frost"
	SkillIds[2] = "ESSB_lightning"
	SkillIds[3] = "ESSB_earth"
	SkillIds[4] = "ESSB_wind"
	SkillIds[5] = "ESSB_blood"
	SkillIds[6] = "ESSB_divine"
	SkillIds[7] = "ESSB_poison"
	SkillIds[8] = "ESSB_water"
	SkillIds[9] = "ESSB_darkness"
	SkillIds[10] = "ESSB_astral"
	SkillIds[11] = "ESSB_noform"
	SkillIds[12] = "ESSB_common"
	TreeNames[0] = "火焰"
	TreeNames[1] = "冰霜"
	TreeNames[2] = "雷電"
	TreeNames[3] = "大地"
	TreeNames[4] = "風"
	TreeNames[5] = "鮮血"
	TreeNames[6] = "神聖"
	TreeNames[7] = "毒素"
	TreeNames[8] = "水"
	TreeNames[9] = "黑暗"
	TreeNames[10] = "星界"
	TreeNames[11] = "無元素"
	TreeNames[12] = "全元素通用"
	CacheTree[0] = -1
	CacheTree[1] = -1
	CacheTree[2] = -1
	AllRankA = new Int[120]
	AllRankB = new Int[75]
	AllBranchA = new Int[120]
	AllBranchB = new Int[75]
	AllValid = new Bool[13]
	LevelCache = new Int[13]
	If !AllRankA || !AllRankB || !AllBranchA || !AllBranchB || !AllValid || !LevelCache
		Controller.BreakState()
		Return
	EndIf
	TablesInitialised = True
EndFunction

Actor Function ThePlayer()
	If !Controller || !Controller.IsCurrentController() || Controller.StateBroken
		Return None
	EndIf
	If !PlayerRef
		PlayerRef = GetActorReference()
	EndIf
	Return PlayerRef
EndFunction

; ---------------------------------------------------------------- 樹與節點的定址

String Function SkillId(Int aiTree)
	If !Controller || !Controller.IsCurrentController() || Controller.StateBroken
		Return ""
	EndIf
	InitTables()
	If Controller.StateBroken
		Return ""
	EndIf
	If aiTree < 0 || aiTree >= TREE_COUNT
		Return ""
	EndIf
	Return SkillIds[aiTree]
EndFunction

String Function TreeName(Int aiTree)
	If !Controller || !Controller.IsCurrentController() || Controller.StateBroken
		Return ""
	EndIf
	InitTables()
	If Controller.StateBroken
		Return ""
	EndIf
	If aiTree < 0 || aiTree >= TREE_COUNT
		Return "?"
	EndIf
	Return TreeNames[aiTree]
EndFunction

Int Function TreeOfSkillId(String asSkillId)
	If !Controller || !Controller.IsCurrentController() || Controller.StateBroken
		Return 0
	EndIf
	InitTables()
	If Controller.StateBroken
		Return 0
	EndIf
	Int index = 0
	While index < TREE_COUNT
		If SkillIds[index] == asSkillId
			Return index
		EndIf
		index += 1
	EndWhile
	Return -1
EndFunction

; 形態啟用時是當前元素樹，否則是無元素樹（規劃 4）。
Int Function CurrentTree()
	If !Controller || !Controller.IsCurrentController() || Controller.StateBroken
		Return 0
	EndIf
	If FormActive && FormActive.GetValueInt() == 1 && CurrentElement
		Int element = CurrentElement.GetValueInt()
		If element >= 1 && element <= 11
			Return element - 1
		EndIf
	EndIf
	Return 11
EndFunction

Int Function CommonTree()
	If !Controller || !Controller.IsCurrentController() || Controller.StateBroken
		Return 0
	EndIf
	Return 12
EndFunction

Int Function NodeIndex(Int aiTree, Int aiRoute, Int aiTier)
	If !Controller || !Controller.IsCurrentController() || Controller.StateBroken
		Return 0
	EndIf
	Return (aiTree * ROUTE_COUNT + aiRoute) * TIER_COUNT + aiTier
EndFunction

Int Function MainBase(Int aiTree, Int aiRoute, Int aiTier)
	If !Controller || !Controller.IsCurrentController() || Controller.StateBroken
		Return 0
	EndIf
	Return MAIN_BASE + NodeIndex(aiTree, aiRoute, aiTier) * MAIN_MAX_RANK
EndFunction

Int Function BranchBase(Int aiTree, Int aiRoute, Int aiTier)
	If !Controller || !Controller.IsCurrentController() || Controller.StateBroken
		Return 0
	EndIf
	Return BRANCH_BASE + NodeIndex(aiTree, aiRoute, aiTier) * BRANCH_SLOTS
EndFunction

Bool Function ValidCell(Int aiTree, Int aiRoute, Int aiTier)
	If !Controller || !Controller.IsCurrentController() || Controller.StateBroken
		Return False
	EndIf
	Return aiTree >= 0 && aiTree < TREE_COUNT && aiRoute >= 0 && aiRoute < ROUTE_COUNT \
		&& aiTier >= 0 && aiTier < TIER_COUNT
EndFunction

; 主線第 aiRank 階（1 起算）的 perk。
Perk Function GetMainPerk(Int aiTree, Int aiRoute, Int aiTier, Int aiRank)
	If !Controller || !Controller.IsCurrentController() || Controller.StateBroken
		Return None
	EndIf
	If !ValidCell(aiTree, aiRoute, aiTier) || aiRank < 1 || aiRank > MAIN_MAX_RANK
		Return None
	EndIf
	Return Game.GetFormFromFile(MainBase(aiTree, aiRoute, aiTier) + aiRank - 1, PLUGIN_FILE) as Perk
EndFunction

; 第 aiIndex 個分支（0 起算）；不存在就回 None。
Perk Function GetBranch(Int aiTree, Int aiRoute, Int aiTier, Int aiIndex)
	If !Controller || !Controller.IsCurrentController() || Controller.StateBroken
		Return None
	EndIf
	If !ValidCell(aiTree, aiRoute, aiTier) || aiIndex < 0 || aiIndex >= BRANCH_SLOTS
		Return None
	EndIf
	Return Game.GetFormFromFile(BranchBase(aiTree, aiRoute, aiTier) + aiIndex, PLUGIN_FILE) as Perk
EndFunction

; ---------------------------------------------------------------- 讀取已投點數

; 二分搜尋 15 階鏈：16 個候選值（0～15），固定 4 次 HasPerk。
Int Function GetMainRank(Int aiTree, Int aiRoute, Int aiTier)
	If !Controller || !Controller.IsCurrentController() || Controller.StateBroken
		Return 0
	EndIf
	Actor player = ThePlayer()
	If !player || !ValidCell(aiTree, aiRoute, aiTier)
		Return 0
	EndIf
	Int base = MainBase(aiTree, aiRoute, aiTier)
	Int low = 0
	Int high = MAIN_MAX_RANK
	While low < high
		Int mid = (low + high + 1) / 2
		Perk step = Game.GetFormFromFile(base + mid - 1, PLUGIN_FILE) as Perk
		If step && player.HasPerk(step)
			low = mid
		Else
			high = mid - 1
		EndIf
	EndWhile
	Return low
EndFunction

Bool Function HasBranch(Int aiTree, Int aiRoute, Int aiTier, Int aiIndex)
	If !Controller || !Controller.IsCurrentController() || Controller.StateBroken
		Return False
	EndIf
	Actor player = ThePlayer()
	Perk branch = GetBranch(aiTree, aiRoute, aiTier, aiIndex)
	Return player != None && branch != None && player.HasPerk(branch)
EndFunction

Int Function Bit(Int aiIndex)
	If !Controller || !Controller.IsCurrentController() || Controller.StateBroken
		Return 0
	EndIf
	If aiIndex == 0
		Return 1
	ElseIf aiIndex == 1
		Return 2
	ElseIf aiIndex == 2
		Return 4
	ElseIf aiIndex == 3
		Return 8
	EndIf
	Return 0
EndFunction

; ---------------------------------------------------------------- 快取（給機制前線）

Int Function CacheSlotOf(Int aiTree)
	If !Controller || !Controller.IsCurrentController() || Controller.StateBroken
		Return 0
	EndIf
	Int index = 0
	While index < CACHE_SLOTS
		If CacheTree[index] == aiTree
			Return index
		EndIf
		index += 1
	EndWhile
	Return -1
EndFunction

; 三個快取槽固定分工：0 當前元素樹、1 無元素樹（11）、2 通用樹（12）。
; 機制前線每一次計算都同時要這三棵，用輪替會在切換元素時把通用樹擠掉。
Int Function SlotFor(Int aiTree)
	If !Controller || !Controller.IsCurrentController() || Controller.StateBroken
		Return 0
	EndIf
	If aiTree == 11
		Return 1
	ElseIf aiTree == 12
		Return 2
	EndIf
	Return 0
EndFunction

; 把一棵樹的 15 個主線階數與分支位元遮罩算進快取。約 120 次原生呼叫，只在事件時跑。
Function RefreshTree(Int aiTree)
	If !Controller || !Controller.IsCurrentController() || Controller.StateBroken
		Return
	EndIf
	InitTables()
	If Controller.StateBroken
		Return
	EndIf
	Actor player = ThePlayer()
	If !player || aiTree < 0 || aiTree >= TREE_COUNT
		Return
	EndIf
	Int slot = SlotFor(aiTree)
	CacheTree[slot] = -1
	AllValid[aiTree] = False
	Int pos = 0
	While pos < 15
		Int route = pos / TIER_COUNT
		Int tier = pos % TIER_COUNT
		CacheRank[slot * 15 + pos] = GetMainRank(aiTree, route, tier)
		Int bits = 0
		Int n = 0
		While n < BRANCH_SLOTS
			Perk branch = GetBranch(aiTree, route, tier, n)
			If branch && player.HasPerk(branch)
				bits = Math.LogicalOr(bits, Bit(n))
			EndIf
			n += 1
		EndWhile
		CacheBranch[slot * 15 + pos] = bits
		Int cacheIndex = aiTree * 15 + pos
		If cacheIndex < 120
			AllRankA[cacheIndex] = CacheRank[slot * 15 + pos]
			AllBranchA[cacheIndex] = bits
		Else
			AllRankB[cacheIndex - 120] = CacheRank[slot * 15 + pos]
			AllBranchB[cacheIndex - 120] = bits
		EndIf
		pos += 1
	EndWhile
	CacheTree[slot] = aiTree
	LevelCache[aiTree] = TreeLevel(aiTree)
	AllValid[aiTree] = True
	If Controller.CachedDebugLevel >= 3
		If Controller.CachedDebugLevel >= 3
			Controller.LogEvent(3, "trees", "refresh tree=" + aiTree + " slot=" + slot)
		EndIf
	EndIf
	Controller.RankCacheA = AllRankA
	Controller.RankCacheB = AllRankB
	Controller.BranchCacheA = AllBranchA
	Controller.BranchCacheB = AllBranchB
	Controller.LevelMirror = LevelCache
	Controller.NodeMirrorReady = True
	Controller.RefreshSyncStage()
EndFunction

; 機制前線的讀取入口：快取命中就 O(1)，沒命中就即時二分搜尋。
Int Function CachedMainRank(Int aiTree, Int aiRoute, Int aiTier)
	If !Controller || !Controller.IsCurrentController() || Controller.StateBroken
		Return 0
	EndIf
	InitTables()
	If Controller.StateBroken
		Return 0
	EndIf
	If !ValidCell(aiTree, aiRoute, aiTier)
		Return 0
	EndIf
	Int slot = CacheSlotOf(aiTree)
	If slot < 0
		Return GetMainRank(aiTree, aiRoute, aiTier)
	EndIf
	Return CacheRank[slot * 15 + aiRoute * TIER_COUNT + aiTier]
EndFunction

; 機制前線用：一次把「當前元素樹 + 無元素樹 + 通用樹」算進三個固定槽。
; 只在形態開／切／關與技能樹選單關閉時呼叫，不在命中路徑上。
Function RefreshActive(Int aiTree)
	If !Controller || !Controller.IsCurrentController() || Controller.StateBroken
		Return
	EndIf
	Int i = 0
	While i < TREE_COUNT
		If !AllValid || !AllValid[i] || i == aiTree || i >= 11
			RefreshTree(i)
		EndIf
		i += 1
	EndWhile
	Controller.RefreshSyncStage()
EndFunction

; 規劃 2.7：L 是該樹等級（1–100），G(L) = 1 + 0.05 × L，100 級為 ×6。
Int Function TreeLevel(Int aiTree)
	If !Controller || !Controller.IsCurrentController() || Controller.StateBroken
		Return 0
	EndIf
	If aiTree < 0 || aiTree >= TREE_COUNT || !LvlGlobals
		Return 1
	EndIf
	GlobalVariable level = LvlGlobals[aiTree]
	If !level
		Return 1
	EndIf
	Int value = level.GetValueInt()
	If value < 1
		value = 1
	EndIf
	Return value
EndFunction

Float Function TreeG(Int aiTree)
	If !Controller || !Controller.IsCurrentController() || Controller.StateBroken
		Return 0.0
	EndIf
	Return 1.0 + 0.05 * TreeLevel(aiTree)
EndFunction

Bool Function CachedBranch(Int aiTree, Int aiRoute, Int aiTier, Int aiIndex)
	If !Controller || !Controller.IsCurrentController() || Controller.StateBroken
		Return False
	EndIf
	InitTables()
	If Controller.StateBroken
		Return False
	EndIf
	If !ValidCell(aiTree, aiRoute, aiTier) || aiIndex < 0 || aiIndex >= BRANCH_SLOTS
		Return False
	EndIf
	Int slot = CacheSlotOf(aiTree)
	If slot < 0
		Return HasBranch(aiTree, aiRoute, aiTier, aiIndex)
	EndIf
	Return Math.LogicalAnd(CacheBranch[slot * 15 + aiRoute * TIER_COUNT + aiTier], Bit(aiIndex)) != 0
EndFunction

; ---------------------------------------------------------------- 經驗（規劃 4）

; 每次有效命中：開形態給當前元素樹 + 通用樹，關形態給無元素樹。
Function OnValidHitXP(Int aiElement)
	If !Controller || !Controller.IsCurrentController() || Controller.StateBroken
		Return
	EndIf
	Award(aiElement)
EndFunction

; 開印：新印記元素樹 + 通用樹。
Function OnOpenXP(Int aiElement)
	If !Controller || !Controller.IsCurrentController() || Controller.StateBroken
		Return
	EndIf
	Award(aiElement)
EndFunction

; 終焉與融斷：被結清的元素樹 + 通用樹。
Function OnEndXP(Int aiElement)
	If !Controller || !Controller.IsCurrentController() || Controller.StateBroken
		Return
	EndIf
	Award(aiElement)
EndFunction

Function Award(Int aiElement)
	If !Controller || !Controller.IsCurrentController() || Controller.StateBroken
		Return
	EndIf
	Float amount = 1.0
	If XPPerHit
		amount = XPPerHit.GetValue()
	EndIf
	If amount <= 0.0 || !XPBudget()
		Return
	EndIf
	If aiElement >= 1 && aiElement <= 11
		CustomSkills.AdvanceSkill(SkillId(aiElement - 1), amount)
		CustomSkills.AdvanceSkill(SkillId(12), amount)
	Else
		CustomSkills.AdvanceSkill(SkillId(11), amount)
	EndIf
EndFunction

; 規劃 4：高速雙持與多段的去重與權重內部處理，每秒經驗有上限。
Bool Function XPBudget()
	If !Controller || !Controller.IsCurrentController() || Controller.StateBroken
		Return False
	EndIf
	Float now = Utility.GetCurrentRealTime()
	If now < XPWindowStart || now - XPWindowStart >= 1.0
		XPWindowStart = now
		XPCount = 0
	EndIf
	If XPCount >= XP_PER_SECOND
		Return False
	EndIf
	XPCount += 1
	Return True
EndFunction

; CSF 升級：每升一級給該樹 1 點（規劃 3），並顯示原版樣式的升級訊息。
Event OnCustomSkillIncrease(String asSkillId)
	If !Controller || !Controller.IsCurrentController() || Controller.StateBroken
		Return
	EndIf
	Int tree = TreeOfSkillId(asSkillId)
	If tree < 0
		Return
	EndIf
	Int level = CustomSkills.GetSkillLevel(asSkillId)
	GlobalVariable points = PtsGlobals[tree]
	Int after = 0
	If points
		after = points.GetValueInt() + 1
		points.SetValueInt(after)
	EndIf
	RefreshTree(tree)
	Controller.RefreshRuntimeValues()
	CustomSkills.ShowSkillIncreaseMessage(asSkillId, level)
	If Controller.CachedDebugLevel >= 1
		Controller.LogEvent(1, "trees", "levelup tree=" + tree + " skill=" + asSkillId \
			+ " level=" + level + " points=" + after)
	EndIf
EndEvent

; ---------------------------------------------------------------- 選單與分支扣點

Function OpenTree(Int aiTree, Bool abQueued = False)
	If !Controller || !Controller.IsCurrentController() || Controller.StateBroken
		Return
	EndIf
	If !Ready || !Controller.IsReadyUI()
		Debug.Notification("元素魔戰士：尚未就緒")
		Return
	EndIf
	If !abQueued && (SettingsBusy || QueuedTree >= 0 || OpeningMenu)
		Return
	EndIf
	If UI.IsMenuOpen(MENU_NAME) || UI.IsMenuOpen("MessageBoxMenu")
		OpeningMenu = False
		Return
	EndIf
	If !abQueued && OpeningMenu
		Return
	EndIf
	OpeningMenu = True
	InitTables()
	If Controller.StateBroken
		Return
	EndIf
	If aiTree < 0 || aiTree >= TREE_COUNT
		Return
	EndIf
	If PendingTree >= 0
		; 上一次的選單沒有送出關閉事件（被別的模組關掉、或選單名稱不同），先補結清。
		Int stale = PendingTree
		PendingTree = -1
		Reconcile(stale)
	EndIf
	TakeSnapshot(aiTree)
	PendingTree = aiTree
	RegisterForMenu(MENU_NAME)
	MenuRequestedAt = Utility.GetCurrentRealTime()
	RegisterForSingleUpdate(1.0)
	CustomSkills.OpenCustomSkillMenu(SkillId(aiTree))
EndFunction

Function OpenCommonTree()
	If !Controller || !Controller.IsCurrentController() || Controller.StateBroken
		Return
	EndIf
	OpenTree(CommonTree())
EndFunction

Event OnMenuClose(String asMenuName)
	If !Controller || !Controller.IsCurrentController() || Controller.StateBroken
		Return
	EndIf
	If asMenuName == "MessageBoxMenu"
		UnregisterForMenu("MessageBoxMenu")
		If QueuedTree >= 0
			RegisterForSingleUpdate(0.2)
		EndIf
		Return
	EndIf
	If asMenuName != MENU_NAME || PendingTree < 0
		Return
	EndIf
	OpeningMenu = False
	SettingsBusy = True
	UnregisterForMenu(MENU_NAME)
	Int tree = PendingTree
	PendingTree = -1
	Reconcile(tree)
	SettingsBusy = False
EndEvent

Function TakeSnapshot(Int aiTree)
	If !Controller || !Controller.IsCurrentController() || Controller.StateBroken
		Return
	EndIf
	Actor player = ThePlayer()
	Int pos = 0
	While pos < 15
		Int route = pos / TIER_COUNT
		Int tier = pos % TIER_COUNT
		Int bits = 0
		Int n = 0
		While n < BRANCH_SLOTS
			Perk branch = GetBranch(aiTree, route, tier, n)
			If player && branch && player.HasPerk(branch)
				bits = Math.LogicalOr(bits, Bit(n))
			EndIf
			n += 1
		EndWhile
		SnapBranch[pos] = bits
		pos += 1
	EndWhile
EndFunction

; CSF 每個節點只扣 1 點；分支要 5 點，所以這裡補扣 4 點，補不出來就退回該分支。
Function Reconcile(Int aiTree)
	If !Controller || !Controller.IsCurrentController() || Controller.StateBroken
		Return
	EndIf
	Actor player = ThePlayer()
	If !player || aiTree < 0 || aiTree >= TREE_COUNT
		Return
	EndIf
	GlobalVariable points = PtsGlobals[aiTree]
	If !points
		Return
	EndIf
	Int available = points.GetValueInt()
	Int bought = 0
	Int refused = 0
	Int pos = 0
	While pos < 15
		Int route = pos / TIER_COUNT
		Int tier = pos % TIER_COUNT
		Int n = 0
		While n < BRANCH_SLOTS
			If Math.LogicalAnd(SnapBranch[pos], Bit(n)) == 0
				Perk branch = GetBranch(aiTree, route, tier, n)
				If branch && player.HasPerk(branch)
					If available >= BRANCH_COST - 1
						available -= (BRANCH_COST - 1)
						bought += 1
					Else
						player.RemovePerk(branch)
						; CSF 已經扣掉的那 1 點也要退回。
						available += 1
						refused += 1
					EndIf
				EndIf
			EndIf
			n += 1
		EndWhile
		pos += 1
	EndWhile
	If available < 0
		available = 0
	EndIf
	points.SetValueInt(available)
	If refused > 0
		Debug.Notification("點數不足：" + TreeName(aiTree) + " 有 " + refused + " 個分支已退回")
	EndIf
	RefreshTree(aiTree)
	If Controller && Controller.IsReadyUI()
		Controller.RefreshAbilities()
	EndIf
	If Controller.CachedDebugLevel >= 1
		Controller.LogEvent(1, "trees", "reconcile tree=" + aiTree + " branches=" + bought \
			+ " refused=" + refused + " points=" + available)
	EndIf
EndFunction

; ---------------------------------------------------------------- 洗點（規劃 3.1）

Bool Function RespecReady(Int aiTree)
	If !Controller || !Controller.IsCurrentController() || Controller.StateBroken
		Return False
	EndIf
	GlobalVariable stamp = RespecGlobals[aiTree]
	If !stamp
		Return True
	EndIf
	Return Utility.GetCurrentGameTime() - stamp.GetValue() >= Controller.CooldownSeconds(86400.0) / 86400.0
EndFunction

Bool Function RespecAllowed()
	If !Controller || !Controller.IsCurrentController() || Controller.StateBroken
		Return False
	EndIf
	Actor player = ThePlayer()
	If !player
		Return False
	EndIf
	If player.IsInCombat()
		Debug.Notification("洗點：脫離戰鬥後才能洗點")
		Return False
	EndIf
	If FormActive && FormActive.GetValueInt() == 1
		Debug.Notification("洗點：請先關閉形態")
		Return False
	EndIf
	Return True
EndFunction

Function Respec(Int aiTree)
	If !Controller || !Controller.IsCurrentController() || Controller.StateBroken
		Return
	EndIf
	InitTables()
	If Controller.StateBroken
		Return
	EndIf
	If aiTree < 0 || aiTree >= TREE_COUNT || !RespecAllowed()
		Return
	EndIf
	If !RespecReady(aiTree)
		Debug.Notification("洗點：" + TreeName(aiTree) + " 一個遊戲日內只能洗一次")
		Return
	EndIf
	Int removed = RespecTree(aiTree)
	Debug.Notification("洗點完成：" + TreeName(aiTree) + "，退回 " + removed + " 個節點")
EndFunction

Function RespecAll()
	If !Controller || !Controller.IsCurrentController() || Controller.StateBroken
		Return
	EndIf
	InitTables()
	If Controller.StateBroken
		Return
	EndIf
	If !RespecAllowed()
		Return
	EndIf
	Int removed = 0
	Int skipped = 0
	Int tree = 0
	While tree < TREE_COUNT
		If RespecReady(tree)
			removed += RespecTree(tree, False)
		Else
			skipped += 1
		EndIf
		tree += 1
	EndWhile
	If Controller && Controller.IsReadyUI()
		Controller.RefreshAbilities()
	EndIf
	Debug.Notification("洗點完成：全部，退回 " + removed + " 個節點，冷卻中 " + skipped + " 棵")
EndFunction

; 移除該樹全部節點、把點數設回等級數、蓋上冷卻時戳（規劃 3.1）。
Int Function RespecTree(Int aiTree, Bool abRefreshAbilities = True)
	If !Controller || !Controller.IsCurrentController() || Controller.StateBroken
		Return 0
	EndIf
	Actor player = ThePlayer()
	If !player
		Return 0
	EndIf
	Int removed = 0
	Int pos = 0
	While pos < 15
		Int route = pos / TIER_COUNT
		Int tier = pos % TIER_COUNT
		Int base = MainBase(aiTree, route, tier)
		Int rank = GetMainRank(aiTree, route, tier)
		Int step = 0
		While step < rank
			Perk node = Game.GetFormFromFile(base + step, PLUGIN_FILE) as Perk
			If node
				player.RemovePerk(node)
				removed += 1
			EndIf
			step += 1
		EndWhile
		Int n = 0
		While n < BRANCH_SLOTS
			Perk branch = GetBranch(aiTree, route, tier, n)
			If branch && player.HasPerk(branch)
				player.RemovePerk(branch)
				removed += 1
			EndIf
			n += 1
		EndWhile
		pos += 1
	EndWhile
	GlobalVariable points = PtsGlobals[aiTree]
	GlobalVariable level = LvlGlobals[aiTree]
	Int restored = 0
	If points && level
		restored = level.GetValueInt()
		points.SetValueInt(restored)
	EndIf
	GlobalVariable stamp = RespecGlobals[aiTree]
	If stamp
		stamp.SetValue(Utility.GetCurrentGameTime())
	EndIf
	RefreshTree(aiTree)
	If Controller && abRefreshAbilities && Controller.IsReadyUI()
		Controller.RefreshAbilities()
	EndIf
	If Controller.CachedDebugLevel >= 1
		Controller.LogEvent(1, "trees", "respec tree=" + aiTree + " removed=" + removed \
			+ " points=" + restored)
	EndIf
	Return removed
EndFunction

; ---------------------------------------------------------------- 除錯

Function DumpTree(Int aiTree)
	If !Controller || !Controller.IsCurrentController() || Controller.StateBroken
		Return
	EndIf
	InitTables()
	If Controller.StateBroken
		Return
	EndIf
	If aiTree < 0 || aiTree >= TREE_COUNT
		Return
	EndIf
	GlobalVariable level = LvlGlobals[aiTree]
	GlobalVariable points = PtsGlobals[aiTree]
	Int levelValue = 0
	Int pointValue = 0
	If level
		levelValue = level.GetValueInt()
	EndIf
	If points
		pointValue = points.GetValueInt()
	EndIf
	Debug.Trace("[ESSB][trees][L0] tree=" + aiTree + " name=" + TreeName(aiTree) \
		+ " skill=" + SkillId(aiTree) + " level=" + levelValue + " points=" + pointValue)
	Int pos = 0
	While pos < 15
		Int route = pos / TIER_COUNT
		Int tier = pos % TIER_COUNT
		Int bits = 0
		Int n = 0
		While n < BRANCH_SLOTS
			If HasBranch(aiTree, route, tier, n)
				bits = Math.LogicalOr(bits, Bit(n))
			EndIf
			n += 1
		EndWhile
		Debug.Trace("[ESSB][trees][L0] route=" + route + " tier=" + tier \
			+ " main=" + GetMainRank(aiTree, route, tier) + "/15 branches=" + bits)
		pos += 1
	EndWhile
EndFunction

Int Function MainRankInternal(Int aiTree, Int aiRoute, Int aiTier)
	If !Controller || Controller.StateBroken || aiTree < 0 || aiTree >= 13 || aiRoute < 0 || aiRoute >= 3 || aiTier < 0 || aiTier >= 5
		Return 0
	EndIf
	If !AllValid || !AllValid[aiTree]
		Return GetMainRank(aiTree, aiRoute, aiTier)
	EndIf
	Int cacheIndex = aiTree * 15 + aiRoute * 5 + aiTier
	If cacheIndex < 120
		Return AllRankA[cacheIndex]
	EndIf
	Return AllRankB[cacheIndex - 120]
EndFunction

Bool Function BranchInternal(Int aiTree, Int aiRoute, Int aiTier, Int aiIndex)
	If !Controller || Controller.StateBroken || aiTree < 0 || aiTree >= 13 || aiRoute < 0 || aiRoute >= 3 || aiTier < 0 || aiTier >= 5 || aiIndex < 0 || aiIndex >= 4
		Return False
	EndIf
	If !AllValid || !AllValid[aiTree]
		Return HasBranch(aiTree, aiRoute, aiTier, aiIndex)
	EndIf
	Int cacheIndex = aiTree * 15 + aiRoute * 5 + aiTier
	Int bits = 0
	If cacheIndex < 120
		bits = AllBranchA[cacheIndex]
	Else
		bits = AllBranchB[cacheIndex - 120]
	EndIf
	Int bitValue = 1
	If aiIndex == 1
		bitValue = 2
	ElseIf aiIndex == 2
		bitValue = 4
	ElseIf aiIndex == 3
		bitValue = 8
	EndIf
	Return Math.LogicalAnd(bits, bitValue) != 0
EndFunction

Float Function TreeGInternal(Int aiTree)
	If !Controller || Controller.StateBroken || aiTree < 0 || aiTree >= 13
		Return 1.0
	EndIf
	If !AllValid || !AllValid[aiTree]
		Return TreeG(aiTree)
	EndIf
	Return 1.0 + 0.05 * LevelCache[aiTree]
EndFunction

Function AwardInternal(Int aiElement)
	If !Controller || Controller.StateBroken
		Return
	EndIf
	Float amount = 1.0
	If XPPerHit
		amount = XPPerHit.GetValue()
	EndIf
	If amount <= 0.0 || !XPBudgetInternal()
		Return
	EndIf
	If aiElement >= 1 && aiElement <= 11
		CustomSkills.AdvanceSkill(SkillIdInternal(aiElement - 1), amount)
		CustomSkills.AdvanceSkill(SkillIdInternal(12), amount)
	Else
		CustomSkills.AdvanceSkill(SkillIdInternal(11), amount)
	EndIf
EndFunction

Bool Function XPBudgetInternal()
	If !Controller || Controller.StateBroken
		Return False
	EndIf
	Float now = Utility.GetCurrentRealTime()
	If now < XPWindowStart || now - XPWindowStart >= 1.0
		XPWindowStart = now
		XPCount = 0
	EndIf
	If XPCount >= XP_PER_SECOND
		Return False
	EndIf
	XPCount += 1
	Return True
EndFunction

String Function SkillIdInternal(Int aiTree)
	If !Controller || Controller.StateBroken
		Return ""
	EndIf
	If Controller.StateBroken
		Return ""
	EndIf
	If aiTree < 0 || aiTree >= TREE_COUNT
		Return ""
	EndIf
	Return SkillIds[aiTree]
EndFunction

Bool Function BeginSettings()
	If !Controller || !Controller.IsReadyUI() || !Ready
		Debug.Notification("元素魔戰士：尚未就緒")
		Return False
	EndIf
	If SettingsBusy || QueuedTree >= 0 || OpeningMenu
		Return False
	EndIf
	If UI.IsMenuOpen(MENU_NAME)
		Return False
	EndIf
	; Recheck after native call before claiming this alias-local mutex.
	If SettingsBusy || QueuedTree >= 0 || OpeningMenu
		Return False
	EndIf
	SettingsBusy = True
	RegisterForMenu("MessageBoxMenu")
	Return True
EndFunction

Function FinishSettings(Int aiChoice)
	If !Controller || !Controller.IsReadyUI()
		Return
	EndIf
	If !SettingsBusy
		Return
	EndIf
	If aiChoice == 0
		QueuedTree = CurrentTree()
		If Controller.CachedDebugLevel >= 1
			Controller.LogEvent(1, "settings", "open tree current")
		EndIf
	ElseIf aiChoice == 1
		QueuedTree = 12
		If Controller.CachedDebugLevel >= 1
			Controller.LogEvent(1, "settings", "open tree common")
		EndIf
	EndIf
	If QueuedTree >= 0
		RegisterForSingleUpdate(0.2)
	EndIf
	SettingsBusy = False
EndFunction

Event OnMenuOpen(String asMenuName)
	If !Controller || !Controller.IsCurrentController() || Controller.StateBroken
		Return
	EndIf
	If asMenuName == MENU_NAME && PendingTree >= 0
		OpeningMenu = False
	EndIf
EndEvent
