// stake_manager.h

#ifndef __INC_STAKE_MANAGER_H__
#define __INC_STAKE_MANAGER_H__

#include <map>
#include "singleton.h"

class CHARACTER;
struct event;

enum EStakePackageType
{
	STAKE_PACKAGE_DAILY	  = 1, // 1 Gün
	STAKE_PACKAGE_WEEKLY  = 2, // 7 Gün
	STAKE_PACKAGE_MONTHLY = 3, // 30 Gün
};

// Doğru struct tanımı
struct StakeData
{
	DWORD	stake_id;
	DWORD	account_id;
	DWORD	owner_pid;
	char	owner_name[25];
	uint32_t gold;
	BYTE	package_type;
	DWORD	remain_sec;
	LPEVENT pkEvent;
};

class CStakeManager : public singleton<CStakeManager>
{
public:
	CStakeManager();
	~CStakeManager();

	void Initialize();				   // Sunucu açılışında
	void LoadFromDB();				  // (Opsiyonel) Sunucu açılışında DB yükleme
	void CreateStake(CHARACTER* ch, uint32_t dwGold, BYTE bPackageType);
	void SendActiveStakesToPlayer(LPCHARACTER pkChr);

	// Veriyi tutan map
	std::map<DWORD, StakeData> m_mapStake;	// Artık "st{}" yok!
	DWORD m_dwNextStakeID;
};

#endif // __INC_STAKE_MANAGER_H__
