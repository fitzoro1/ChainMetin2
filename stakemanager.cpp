// stakemanager.cpp

#include "stdafx.h"
#include "stakemanager.h"
#include "char.h"
#include "char_manager.h"
#include "desc.h"
#include "db.h"
#include "packet.h"
#include "event.h"
#include "log.h"
#include "utils.h"
#include "config.h"

#define STAKE_TABLE "stake_data"
#define PASSES_PER_SEC(sec) ((sec) * passes_per_sec)

// --------------------------------------------------
// CStakeManager Implementasyonu
// --------------------------------------------------

CStakeManager::CStakeManager()
{
	m_dwNextStakeID = 1;
}

CStakeManager::~CStakeManager()
{
	// destructor
}

void CStakeManager::Initialize()
{
	// Sunucu açılırken otomatik load etmek isterseniz:
	// LoadFromDB();
}

// --------------------------------------------------
// Stake Event
// --------------------------------------------------

namespace
{
	// Event parametre veri yapısı
	EVENTINFO(stake_event_info)
	{
		DWORD stake_id;

		stake_event_info()
		{
			stake_id = 0;
		}
	};

	EVENTFUNC(stake_event)
	{
		stake_event_info* info = dynamic_cast<stake_event_info*>(event->info);
		if (!info)
			return 0;

		DWORD stakeID = info->stake_id;
		auto & m = CStakeManager::instance().m_mapStake;
		auto it = m.find(stakeID);
		if (it == m.end())
			return 0;

		StakeData & st = it->second;

		if (st.remain_sec <= 1)
		{
			// Süre doldu -> Yang iade + EP ver
			LPCHARACTER pkChr = CHARACTER_MANAGER::instance().FindByPID(st.owner_pid);

			DWORD millionCount = st.gold / 1000000; // 1M kaç tane?
			DWORD epReward = 0;

			switch (st.package_type)
			{
				case STAKE_PACKAGE_DAILY:	epReward = millionCount * 1; break;
				case STAKE_PACKAGE_WEEKLY:	epReward = millionCount * 2; break;
				case STAKE_PACKAGE_MONTHLY: epReward = millionCount * 3; break;
			}

			// iade
			if (pkChr)
			{
				// Online iade
				pkChr->PointChange(POINT_GOLD, static_cast<long>(st.gold));

				if (epReward > 0)
				{
					char szQuery[256];
					snprintf(szQuery, sizeof(szQuery),
						"UPDATE account.account SET cash = cash + %u WHERE id = %u",
						epReward, st.account_id
					);
					DBManager::instance().DirectQuery(szQuery);

					pkChr->ChatPacket(CHAT_TYPE_INFO,
									  "Stake bitti! %u Yang geri, +%u EP eklendi.",
									  st.gold, epReward);
				}
				else
				{
					pkChr->ChatPacket(CHAT_TYPE_INFO,
									  "Stake bitti! %u Yang geri verildi.",
									  st.gold);
				}

				// Client'a SUBHEADER_GC_STAKE_REMOVE yolla
				TPacketGCStakeRemove p;
				p.bHeader	 = HEADER_GC_STAKE;			 // 212
				p.bSubHeader = SUBHEADER_GC_STAKE_REMOVE;// 2
				p.dwStakeID	 = st.stake_id;

				if (pkChr->GetDesc())
					pkChr->GetDesc()->Packet(&p, sizeof(p));
			}
			else
			{
				// Offline iade
				if (epReward > 0)
				{
					char szQuery[256];
					snprintf(szQuery, sizeof(szQuery),
						"UPDATE account.account SET cash = cash + %u WHERE id = %u",
						epReward, st.account_id
					);
					DBManager::instance().DirectQuery(szQuery);
				}
				// Yang'ı player tablosuna eklemek isterseniz,
				// orada gold sütunu varsa benzer şekilde:
				// "UPDATE player.player SET gold=gold+X WHERE pid=st.owner_pid"
			}

			// DB'den sil
			{
				char delQ[256];
				snprintf(delQ, sizeof(delQ),
						 "DELETE FROM %s WHERE stake_id=%u",
						 STAKE_TABLE, st.stake_id);
				DBManager::instance().DirectQuery(delQ);
			}

			// m_mapStake'den sil
			m.erase(it);
			return 0; // Event biter
		}
		else
		{
			// her 1 saniyede remain_sec--
			st.remain_sec--;

			// her 60 sn de DB güncelle
			if (st.remain_sec % 60 == 0)
			{
				char upQ[256];
				snprintf(upQ, sizeof(upQ),
					"UPDATE %s SET remain_sec=%u WHERE stake_id=%u",
					STAKE_TABLE, st.remain_sec, st.stake_id
				);
				DBManager::instance().DirectQuery(upQ);
			}

			// tekrar 1 saniye sonra dön
			return PASSES_PER_SEC(1);
		}
	}
} // namespace (anon)

// --------------------------------------------------
// CStakeManager Metodları
// --------------------------------------------------

// Yeni stake oluştur
void CStakeManager::CreateStake(LPCHARACTER pkChr, uint32_t dwGold, BYTE bPackageType)
{
	if (!pkChr)
		return;

	// Yeterli gold?
	if (pkChr->GetGold() < dwGold)
	{
		pkChr->ChatPacket(CHAT_TYPE_INFO, "Yeterli altının yok!");
		return;
	}

	// Altını düş
	pkChr->PointChange(POINT_GOLD, -static_cast<long>(dwGold));

	// StakeData doldur
	StakeData st;
	st.stake_id	  = m_dwNextStakeID++;
	st.account_id = pkChr->GetDesc()->GetAccountTable().id;
	st.owner_pid  = pkChr->GetPlayerID();
	strlcpy(st.owner_name, pkChr->GetName(), sizeof(st.owner_name));
	st.gold		  = dwGold;
	st.package_type = bPackageType;

	// Süre
	DWORD stakeSec = 30; // test = 30 sn
	switch (bPackageType)
	{
		case STAKE_PACKAGE_DAILY:	stakeSec = 24*60*60;	  break;
		case STAKE_PACKAGE_WEEKLY:	stakeSec = 7*24*60*60;	  break;
		case STAKE_PACKAGE_MONTHLY: stakeSec = 30*24*60*60;	  break;
	}
	st.remain_sec = stakeSec;
	st.pkEvent	  = nullptr;

	// map'e ekle
	m_mapStake[st.stake_id] = st;

	// DB Insert
	{
		char insQ[512];
		snprintf(insQ, sizeof(insQ),
			"INSERT INTO %s "
			"(stake_id, account_id, owner_pid, owner_name, gold, package_type, remain_sec, create_time) "
			"VALUES (%u, %u, %u, '%s', %llu, %u, %u, UNIX_TIMESTAMP())",
			STAKE_TABLE,
			st.stake_id,
			st.account_id,
			st.owner_pid,
			st.owner_name,
			(unsigned long long)st.gold,
			st.package_type,
			st.remain_sec
		);
		DBManager::instance().DirectQuery(insQ);
	}

	// Event oluştur
	stake_event_info* info = AllocEventInfo<stake_event_info>();
	info->stake_id = st.stake_id;
	LPEVENT ev = event_create(stake_event, info, PASSES_PER_SEC(1));
	m_mapStake[st.stake_id].pkEvent = ev;

	// Client'a "stake eklendi" packet
	TPacketGCStakeAdd p;
	p.bHeader	  = HEADER_GC_STAKE;		   // 212
	p.bSubHeader  = SUBHEADER_GC_STAKE_ADD;	   // 1
	p.dwStakeID	  = st.stake_id;
	p.dwRemainSec = st.remain_sec;
	p.dwStakeYang = st.gold;

	const char* pkgName = "";
	switch(bPackageType)
	{
		case STAKE_PACKAGE_DAILY:	pkgName = "Gunluk";	  break;
		case STAKE_PACKAGE_WEEKLY:	pkgName = "Haftalik"; break;
		case STAKE_PACKAGE_MONTHLY: pkgName = "Aylik";	  break;
	}
	memset(p.szPackageName, 0, sizeof(p.szPackageName));
	strncpy(p.szPackageName, pkgName, sizeof(p.szPackageName)-1);

	if (pkChr->GetDesc())
		pkChr->GetDesc()->Packet(&p, sizeof(p));
}

// Oyuncu oyuna girince aktif stake'lerini gönder
void CStakeManager::SendActiveStakesToPlayer(LPCHARACTER pkChr)
{
	if (!pkChr)
		return;

	DWORD pid = pkChr->GetPlayerID();

	for (auto & it : m_mapStake)
	{
		StakeData & st = it.second;
		if (st.owner_pid == pid)
		{
			TPacketGCStakeAdd p;
			p.bHeader	  = HEADER_GC_STAKE;
			p.bSubHeader  = SUBHEADER_GC_STAKE_ADD;
			p.dwStakeID	  = st.stake_id;
			p.dwRemainSec = st.remain_sec;
			p.dwStakeYang = st.gold;

			const char* pkgName = "";
			switch(st.package_type)
			{
				case STAKE_PACKAGE_DAILY:	pkgName="Gunluk";	break;
				case STAKE_PACKAGE_WEEKLY:	pkgName="Haftalik"; break;
				case STAKE_PACKAGE_MONTHLY: pkgName="Aylik";	break;
			}
			memset(p.szPackageName, 0, sizeof(p.szPackageName));
			strncpy(p.szPackageName, pkgName, sizeof(p.szPackageName)-1);

			if (pkChr->GetDesc())
				pkChr->GetDesc()->Packet(&p, sizeof(p));
		}
	}
}

// Sunucu açılışında DB'den yüklemek isterseniz
void CStakeManager::LoadFromDB()
{
	char query[256];
	snprintf(query, sizeof(query),
		"SELECT stake_id, account_id, owner_pid, owner_name, gold, package_type, remain_sec "
		"FROM %s",
		STAKE_TABLE
	);

	std::unique_ptr<SQLMsg> pMsg(DBManager::instance().DirectQuery(query));
	SQLResult* res = pMsg->Get();
	if (!res || res->uiNumRows == 0)
		return;

	MYSQL_ROW row;
	while ((row = mysql_fetch_row(res->pSQLResult)))
	{
		StakeData st{};
		int col=0;

		st.stake_id	   = strtoul(row[col++], nullptr, 10);
		st.account_id  = strtoul(row[col++], nullptr, 10);
		st.owner_pid   = strtoul(row[col++], nullptr, 10);
		strlcpy(st.owner_name, row[col++], sizeof(st.owner_name));
		st.gold		   = strtoull(row[col++], nullptr, 10);
		st.package_type= static_cast<BYTE>(strtoul(row[col++], nullptr, 10));
		st.remain_sec  = strtoul(row[col++], nullptr, 10);
		st.pkEvent	   = nullptr;

		m_mapStake[st.stake_id] = st;
		if (m_dwNextStakeID <= st.stake_id)
			m_dwNextStakeID = st.stake_id + 1;
	}

	// Load sonrası, her stake için event başlat
	for (auto & it : m_mapStake)
	{
		stake_event_info* info = AllocEventInfo<stake_event_info>();
		info->stake_id = it.second.stake_id;

		LPEVENT pkEv = event_create(stake_event, info, PASSES_PER_SEC(1));
		it.second.pkEvent = pkEv;
	}
}
