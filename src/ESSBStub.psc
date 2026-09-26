Scriptname ESSBStub extends ActiveMagicEffect
{Round 22（N3）：空腳本。掛在 DLL 要結算「結束」的引擎效果上（印記、冰封、白熱引信、星痕引信、死咒、浮空、恐懼、瘋狂……），
只為了讓引擎在效果移除時送出效果移除事件；判定與結算全部在 DLL（native/src/Plugin.cpp 的 RemoveSink）。
沒有屬性、沒有成員、沒有事件：存檔裡不帶任何狀態。}
