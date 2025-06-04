import ui
import net
import chat
import app
import time

# Client -> Server packet header
HEADER_CG_STAKE = 211  # (C++ tarafında da HEADER_CG_STAKE = 211)
# Server -> Client packet header
HEADER_GC_STAKE = 212  # (C++ tarafında da HEADER_GC_STAKE = 212)

SUBHEADER_GC_STAKE_ADD = 1
SUBHEADER_GC_STAKE_REMOVE = 2

def RecvStakePacket():
	"""
	Server, HEADER_GC_STAKE (212) ile geldiğinde bu fonksiyon çağrılır.
	Sunucu SUBHEADER_GC_STAKE_ADD ya da _REMOVE gönderirse,
	ilgili stake satırını eklemek veya silmek için stakeWin fonksiyonlarını çağırır.
	"""
	subHeader = net.GetPacketByte()

	if subHeader == SUBHEADER_GC_STAKE_ADD:
		# Aşağıdaki veriler sunucunun yolladığı TPacketGCStakeAdd türünden geliyor.
		stakeID = net.GetPacketDWORD()
		remainSec = net.GetPacketDWORD()
		stakeYang = net.GetPacketDWORD()
		packageName = net.GetPacketString()	 # net.GetPacketString() -> string okuma

		stakeWin = GetStakeWindow()
		if stakeWin:
			stakeWin.AddStakeLineFromServer(
				stake_id=stakeID,
				remain_sec=remainSec,
				gold=stakeYang,
				package_name=packageName
			)

	elif subHeader == SUBHEADER_GC_STAKE_REMOVE:
		# Sunucu "Stake silindi" bildiriminde stakeID yollayacak
		stakeID = net.GetPacketDWORD()
		stakeWin = GetStakeWindow()
		if stakeWin:
			stakeWin.RemoveStakeLine(stakeID)

	else:
		chat.AppendChat(chat.CHAT_TYPE_INFO, 
						"[Stake] Gecersiz subHeader: %d" % subHeader)


class StakeLineItem(ui.Window):
	"""
	Bir satırlık stake bilgisini (kalan süre, miktar, vs.) gösteren kontrol.
	"""
	def __init__(self):
		ui.Window.__init__(self)
		self.SetSize(500, 25)

		self.stake_id	  = 0
		self.owner_name	  = ""
		self.gold		  = 0
		self.package_name = ""
		self.remain_sec	  = 0
		self.create_time  = 0

		self.timeText = ui.TextLine()
		self.timeText.SetParent(self)
		self.timeText.SetPosition(5,5)
		self.timeText.Show()

		self.goldText = ui.TextLine()
		self.goldText.SetParent(self)
		self.goldText.SetPosition(140,5)
		self.goldText.Show()

		self.pkgText = ui.TextLine()
		self.pkgText.SetParent(self)
		self.pkgText.SetPosition(270,5)
		self.pkgText.Show()

		self.ownerText = ui.TextLine()
		self.ownerText.SetParent(self)
		self.ownerText.SetPosition(380,5)
		self.ownerText.Show()

		self.createTimeText = ui.TextLine()
		self.createTimeText.SetParent(self)
		self.createTimeText.SetPosition(120,25)
		self.createTimeText.Show()

	def SetData(self, stake_id, owner_name, gold, package_name, remain_sec, create_time):
		self.stake_id	  = stake_id
		self.owner_name	  = owner_name
		self.gold		  = gold
		self.package_name = package_name
		self.remain_sec	  = remain_sec
		self.create_time  = create_time

		self.UpdateTimeText()
		self.goldText.SetText("Yang: %d" % self.gold)
		self.pkgText.SetText("Paket: %s" % self.package_name)

		if self.owner_name:
			self.ownerText.SetText("Sahip: %s" % self.owner_name)
		else:
			self.ownerText.SetText("")

		if self.create_time > 0:
			t = time.localtime(self.create_time)
			timeStr = time.strftime("%Y-%m-%d %H:%M:%S", t)
			self.createTimeText.SetText("Baslangic: %s" % timeStr)
		else:
			self.createTimeText.SetText("")

	def UpdateTimeText(self):
		hh = self.remain_sec // 3600
		mm = (self.remain_sec % 3600) // 60
		ss = self.remain_sec % 60
		self.timeText.SetText("Kalan: %02d:%02d:%02d" % (hh, mm, ss))

	def DecreaseOneSecond(self):
		if self.remain_sec > 0:
			self.remain_sec -= 1
		self.UpdateTimeText()


class StakeWindow(ui.ScriptWindow):
	"""
	'Aktif Stake İşlemleri' paneli:
	  - Seçilen stake paketi (günlük/haftalık/aylık)
	  - Girilen Yang miktarı
	  - Alttaki satırlar -> AddStakeLineFromServer()
	"""
	def __init__(self):
		ui.ScriptWindow.__init__(self)
		self.activeStakeLineList = []
		self.lastUpdateTime = 0.0
		self.totalHeight = 0
		self.selected_package_str = None

		self.__LoadWindow()

	def __del__(self):
		ui.ScriptWindow.__del__(self)

	def __LoadWindow(self):
		loader = ui.PythonScriptLoader()
		loader.LoadScriptFile(self, "uiscript/stakepanel.py")

		self.Board = self.GetChild("board")
		self.activeStakeBoard = self.GetChild("active_stake_board")
		self.listContainer = self.GetChild("active_stake_container")
		self.scrollBar = self.GetChild("active_stake_scroll")

		self.daily_button = ui.Button()
		self.daily_button.SetParent(self.Board)
		self.daily_button.SetPosition(80, 210)
		self.daily_button.SetUpVisual("d:/ymir work/ui/public/small_button_01.sub")
		self.daily_button.SetOverVisual("d:/ymir work/ui/public/small_button_02.sub")
		self.daily_button.SetDownVisual("d:/ymir work/ui/public/small_button_03.sub")
		self.daily_button.SetText("SecG")
		self.daily_button.SetEvent(lambda: self.__SelectPackage("Gunluk"))
		self.daily_button.Show()

		self.weekly_button = ui.Button()
		self.weekly_button.SetParent(self.Board)
		self.weekly_button.SetPosition(230,210)
		self.weekly_button.SetUpVisual("d:/ymir work/ui/public/small_button_01.sub")
		self.weekly_button.SetOverVisual("d:/ymir work/ui/public/small_button_02.sub")
		self.weekly_button.SetDownVisual("d:/ymir work/ui/public/small_button_03.sub")
		self.weekly_button.SetText("SecH")
		self.weekly_button.SetEvent(lambda: self.__SelectPackage("Haftalik"))
		self.weekly_button.Show()

		self.monthly_button = ui.Button()
		self.monthly_button.SetParent(self.Board)
		self.monthly_button.SetPosition(380,210)
		self.monthly_button.SetUpVisual("d:/ymir work/ui/public/small_button_01.sub")
		self.monthly_button.SetOverVisual("d:/ymir work/ui/public/small_button_02.sub")
		self.monthly_button.SetDownVisual("d:/ymir work/ui/public/small_button_03.sub")
		self.monthly_button.SetText("SecA")
		self.monthly_button.SetEvent(lambda: self.__SelectPackage("Aylik"))
		self.monthly_button.Show()

		self.inputSlot = ui.SlotBar()
		self.inputSlot.SetParent(self.Board)
		self.inputSlot.SetPosition(50, 260)
		self.inputSlot.SetSize(200, 20)
		self.inputSlot.Show()

		self.yangInput = ui.EditLine()
		self.yangInput.SetParent(self.inputSlot)
		self.yangInput.SetSize(200,20)
		self.yangInput.SetMax(12)
		self.yangInput.SetText("1000000")
		self.yangInput.SetPosition(5,3)
		self.yangInput.Show()

		self.stakeButton = ui.Button()
		self.stakeButton.SetParent(self.Board)
		self.stakeButton.SetPosition(270,260)
		self.stakeButton.SetUpVisual("d:/ymir work/ui/public/middle_button_01.sub")
		self.stakeButton.SetOverVisual("d:/ymir work/ui/public/middle_button_02.sub")
		self.stakeButton.SetDownVisual("d:/ymir work/ui/public/middle_button_03.sub")
		self.stakeButton.SetText("Stake")
		self.stakeButton.SetEvent(self.OnClickStake)
		self.stakeButton.Show()

		if self.scrollBar:
			self.scrollBar.SetScrollEvent(self.__OnScroll)

	def __SelectPackage(self, pkg):
		self.selected_package_str = pkg
		chat.AppendChat(chat.CHAT_TYPE_INFO, "[Stake] Seçilen Paket: %s" % pkg)

	def OnClickStake(self):
		"""
		Kullanıcı 'Stake' butonuna tıkladığında:
		 - girilen Yang miktarını al
		 - seçilen paket tipini saptayarak net.SendStakePacket() gönder.
		"""
		if not self.selected_package_str:
			chat.AppendChat(chat.CHAT_TYPE_INFO, "[Stake] Lütfen bir paket seçin.")
			return

		yang_str = self.yangInput.GetText()
		try:
			gold = int(yang_str)
			# En az 1M ve 1M'in katları şartı
			if gold < 1000000 or (gold % 1000000) != 0:
				chat.AppendChat(chat.CHAT_TYPE_INFO, "[Stake] En az 1M ve katlarını girebilirsiniz.")
				return
		except ValueError:
			chat.AppendChat(chat.CHAT_TYPE_INFO, "[Stake] Geçersiz sayı!")
			return

		# "Gunluk" = 1, "Haftalik" = 2, "Aylik" = 3
		if self.selected_package_str == "Gunluk":
			package_type = 1
		elif self.selected_package_str == "Haftalik":
			package_type = 2
		elif self.selected_package_str == "Aylik":
			package_type = 3
		else:
			package_type = 0

		# Artık Py/C++ bridging'de tanımlı net.SendStakePacket(gold, package_type) fonksiyonunu çağırıyoruz
		net.SendStakePacket(gold, package_type)

		chat.AppendChat(chat.CHAT_TYPE_INFO,
						"[Stake] Stake isteği yollandı (Yang=%d, Paket=%s)" % (gold, self.selected_package_str))
		self.Close()

	def AddStakeLineFromServer(self, stake_id, gold, package_name, remain_sec):
		"""
		Sunucu SUBHEADER_GC_STAKE_ADD geldiğinde bu fonksiyonla tabloya satır eklenir.
		"""
		line = StakeLineItem()
		line.SetParent(self.listContainer)
		line.SetData(
			stake_id=stake_id,
			owner_name="",		 # eğer isterseniz ekleyebilirsiniz
			gold=gold,
			package_name=package_name,
			remain_sec=remain_sec,
			create_time=0
		)
		line.Show()
		self.activeStakeLineList.append(line)
		self.__ArrangeLinePositions()
		self.__UpdateScrollBar()

	def RemoveStakeLine(self, stake_id):
		"""
		Sunucu SUBHEADER_GC_STAKE_REMOVE geldiğinde bu fonksiyonla tablo satırı silinir.
		"""
		foundIndex = -1
		for idx, lineItem in enumerate(self.activeStakeLineList):
			if lineItem.stake_id == stake_id:
				foundIndex = idx
				break

		if foundIndex >= 0:
			self.activeStakeLineList[foundIndex].Hide()
			del self.activeStakeLineList[foundIndex]
			self.__ArrangeLinePositions()
			self.__UpdateScrollBar()

	def __ArrangeLinePositions(self):
		"""
		Satırlar alt alta dizilecek. Y konumlarını yeniden hesapla.
		"""
		yPos = 0
		for line in self.activeStakeLineList:
			line.SetPosition(0, yPos)
			yPos += 25
		self.totalHeight = yPos

	def __UpdateScrollBar(self):
		if not self.scrollBar:
			return
		cHeight = self.listContainer.GetHeight()
		if self.totalHeight <= cHeight:
			self.scrollBar.Hide()
			self.scrollBar.SetPos(0.0)
		else:
			self.scrollBar.Show()
			pageSize = float(cHeight) / float(self.totalHeight)
			self.scrollBar.SetMiddleBarSize(pageSize)
		self.__OnScroll()

	def __OnScroll(self):
		if not self.scrollBar or not self.scrollBar.IsShow():
			return
		pos = self.scrollBar.GetPos()
		cHeight = self.listContainer.GetHeight()
		maxScroll = self.totalHeight - cHeight
		if maxScroll < 0:
			maxScroll = 0

		scrollY = int(pos * maxScroll)
		for idx, line in enumerate(self.activeStakeLineList):
			baseY = idx * 25
			line.SetPosition(0, baseY - scrollY)

	def OnUpdate(self):
		"""
		ui.ScriptWindow'dan miras alır. Her frame çağrılır.
		Biz 1 saniyede bir remain_sec azaltmak istiyoruz.
		"""
		curTime = app.GetTime()
		if (curTime - self.lastUpdateTime) >= 1.0:
			self.lastUpdateTime = curTime
			for line in self.activeStakeLineList:
				line.DecreaseOneSecond()

	def Open(self):
		self.Show()
		self.SetTop()

	def Close(self):
		if self.IsFocus():
			self.KillFocus()
		self.Hide()

	def OnPressEscapeKey(self):
		self.Close()
		return True

	def Destroy(self):
		for line in self.activeStakeLineList:
			line.Hide()
		self.activeStakeLineList = []

		if self.scrollBar:
			self.scrollBar.Hide()
			self.scrollBar = None

		if self.listContainer:
			self.listContainer.Hide()
			self.listContainer = None

		if self.activeStakeBoard:
			self.activeStakeBoard.Hide()
			self.activeStakeBoard = None

		if self.daily_button:
			self.daily_button.Hide()
			self.daily_button = None

		if self.weekly_button:
			self.weekly_button.Hide()
			self.weekly_button = None

		if self.monthly_button:
			self.monthly_button.Hide()
			self.monthly_button = None

		if self.yangInput:
			self.yangInput.Hide()
			self.yangInput = None

		if self.stakeButton:
			self.stakeButton.Hide()
			self.stakeButton = None

		if self.Board:
			self.Board.Hide()
			self.Board = None

		ui.ScriptWindow.Destroy(self)


g_StakeWindow = None

def GetStakeWindow():
	global g_StakeWindow
	return g_StakeWindow

def OpenStakeWindow():
	global g_StakeWindow
	if not g_StakeWindow:
		g_StakeWindow = StakeWindow()
	g_StakeWindow.Open()
	return g_StakeWindow

def CloseStakeWindow():
	global g_StakeWindow
	if g_StakeWindow:
		g_StakeWindow.Close()
