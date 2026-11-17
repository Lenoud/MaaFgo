"""奏章Ⅱ第六节进行度3：公主处理杂兵，黑贞应对非复仇者耐性。"""
from dataclasses import replace

from ..core.decider import RuleDecider
from ..core.enums import Scene
from ..core.models import BattleAction, BattlePlan, ServantSkillAction, TurnPlan

PRINCESS = "2300500"
KOYAN = "604200"
JALTER = "1100300"


class IdoBritomartDecider(RuleDecider):
    def __init__(self, policy):
        super().__init__(policy)
        self.boss_seen = False

    def decide(self, state, turn_index=0):
        members = {servant.servant_id: servant.slot for servant in state.servants
                   if servant.servant_id}
        focus = JALTER if self.boss_seen else PRINCESS
        if state.scene is Scene.MAIN_BATTLE:
            skills = []
            target = members.get(focus)
            for servant in state.servants:
                if self.boss_seen:
                    indexes = (1, 2, 3) if servant.servant_id in (JALTER, KOYAN) else ()
                    if servant.servant_id == PRINCESS:
                        indexes = (3,)
                else:
                    indexes = (1, 2, 3) if servant.servant_id == PRINCESS else ()
                    if servant.servant_id == JALTER:
                        indexes = (2,)
                for index in indexes:
                    if servant.skills[index - 1].available is True:
                        ally = target if servant.servant_id == KOYAN else None
                        if servant.servant_id == KOYAN and ally is None:
                            continue
                        skills.append(ServantSkillAction(servant.slot, index, target_ally=ally))
            return BattleAction(target_enemy=self._pick_enemy_target(state, turn_index),
                                picks=(), servant_skills=tuple(skills),
                                rationale_tag="ido_britomart:boss" if self.boss_seen else "ido_britomart:trash")
        # 优先级由当下识别到的卡牌身份确定，不沿用退场前的槽位。
        slots = {card.owner_slot for card in state.cards if card.owner_servant_id == focus
                 and card.owner_slot is not None}
        slots.update(card.servant_slot for card in state.np_cards if card.owner_servant_id == focus)
        if len(slots) != 1:
            if not self.boss_seen:
                # 杂兵面没有公主卡时用普通卡补齐，不能误耗留给 Boss 的黑贞宝具。
                policy = replace(self.policy, card=replace(self.card_policy, np_first=False))
                return RuleDecider(policy).decide(state, turn_index)
            return super().decide(state, turn_index)
        slot = slots.pop()
        native = replace(self.card_policy.native_strategy, enabled=True,
                         preferred_servant_ids=(focus,), preferred_slots=(),
                         servant_priority_weight=100)
        policy = replace(self.policy, card=replace(self.card_policy, native_strategy=native))
        return RuleDecider(policy, BattlePlan(turns=(TurnPlan(np_order=(slot,)),))).decide(state, 0)
