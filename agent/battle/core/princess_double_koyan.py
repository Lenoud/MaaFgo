"""用户确认的双杀狐公主三回合方案；仅根据实际初始编队绑定槽位。"""
from copy import deepcopy

PRINCESS = "2300500"
KOYAN = "604200"


def apply_profile(param, frontline):
    """身份不符不生成固定槽位方案，避免把充能点给剧情固定成员。"""
    roster = tuple(str(sid) if sid is not None else None for sid in frontline)
    if len(roster) != 3 or roster.count(PRINCESS) != 1 or roster.count(KOYAN) != 2:
        return None
    princess = roster.index(PRINCESS) + 1
    foxes = [slot for slot, sid in enumerate(roster, 1) if sid == KOYAN]

    def skill(slot, index, target=None):
        value = {"servant_slot": slot, "skill_index": index}
        if target is not None:
            value["target_ally"] = target
        return value

    turns = [
        {"servant_skills": [skill(fox, index, princess) for fox in foxes for index in (2, 3)]
         + [skill(princess, 2)], "np_order": [princess]},
        {"servant_skills": [skill(fox, 1, princess) for fox in foxes], "np_order": [princess]},
        {"servant_skills": [skill(princess, index) for index in (1, 3, 2)],
         "np_order": [princess]},
    ]
    result = deepcopy(param)
    result["plan"] = {"turns": turns}
    card = result.setdefault("card_policy", {})
    card.update(np_first=True, color_priority=["B", "A", "Q"])
    native = card.setdefault("native_strategy", {})
    native.update(enabled=True, preferred_servant_ids=[PRINCESS], preferred_slots=[],
                  servant_priority_weight=100, color_weights={"B": 6, "A": 3, "Q": 2},
                  np_colors_by_servant_id={PRINCESS: "B"})
    return result
