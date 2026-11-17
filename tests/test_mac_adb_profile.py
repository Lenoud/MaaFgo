"""Mac 入口与用户确认的三回合方案的离线回归。"""
import importlib.util
import itertools
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "agent"), str(ROOT / "agent/custom")]
from battle.core.princess_double_koyan import apply_profile, PRINCESS, KOYAN
from battle.core.plan_parser import _load_action_param, _parse_plan, _parse_battle_policy
from battle.core.decider import RuleDecider
from battle.core.enums import Scene, CardColor, PrimitiveKind
from battle.core.models import BattleState, Confidence, CommandCard, NpCard, ServantState, SkillState
from battle.strategies.ido_britomart import IdoBritomartDecider, JALTER
from battle.data.resource_paths import resource_roots

spec = importlib.util.spec_from_file_location("mac_adb_runner", ROOT / "tools/mac_adb_runner.py")
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


class MacAdbProfileTests(unittest.TestCase):
    def test_android_double_encoded_parameters_and_scalar_rejection(self):
        value = {"princess_double_koyan": True}
        for raw in (value, json.dumps(value), json.dumps(json.dumps(value))):
            self.assertEqual(_load_action_param(raw), value)
        for raw in (None, "null", "[]", "42", "true", "invalid", json.dumps("text")):
            self.assertEqual(_load_action_param(raw), {})

    def test_skill_targets_follow_actual_formation_for_every_slot(self):
        for roster in set(itertools.permutations((PRINCESS, KOYAN, KOYAN))):
            with self.subTest(roster=roster):
                param = apply_profile({}, roster)
                princess = roster.index(PRINCESS) + 1
                plan = _parse_plan(param)
                self.assertEqual(len(plan.turns), 3)
                self.assertEqual([turn.np_order for turn in plan.turns], [(princess,)] * 3)
                for turn in plan.turns[:2]:
                    for skill in turn.servant_skills:
                        if skill.servant_slot != princess:
                            self.assertEqual(skill.target_ally, princess)
                self.assertEqual([skill.skill_index for skill in plan.turns[0].servant_skills],
                                 [2, 3, 2, 3, 2])
                self.assertEqual([skill.skill_index for skill in plan.turns[1].servant_skills], [1, 1])
                self.assertEqual([skill.skill_index for skill in plan.turns[2].servant_skills], [1, 3, 2])

    def test_unknown_or_story_npc_cannot_receive_princess_plan(self):
        for roster in ((), (KOYAN, PRINCESS, None), (KOYAN, PRINCESS, "1100300")):
            self.assertIsNone(apply_profile({}, roster))

    def test_actual_decider_prefers_princess_buster_then_princess_arts(self):
        param = apply_profile({}, (KOYAN, PRINCESS, KOYAN))
        cards = tuple(CommandCard(slot, color, owner, Confidence(1),
                                  owner_confidence=Confidence(1), owner_servant_id=sid)
                      for slot, color, owner, sid in (
                          (1, CardColor.BUSTER, 1, KOYAN), (2, CardColor.ARTS, 2, PRINCESS),
                          (3, CardColor.BUSTER, 2, PRINCESS), (4, CardColor.QUICK, 3, KOYAN),
                          (5, CardColor.QUICK, 2, PRINCESS)))
        state = BattleState(Scene.COMMAND_SELECTION, Confidence(1), cards,
                            (NpCard(2, Confidence(1)),), ())
        action = RuleDecider(_parse_battle_policy(param), plan=_parse_plan(param)).decide(state, 0)
        self.assertEqual([(pick.kind, pick.slot) for pick in action.picks],
                         [(PrimitiveKind.SELECT_NP, 2), (PrimitiveKind.SELECT_CARD, 3),
                          (PrimitiveKind.SELECT_CARD, 2)])

    def test_external_resources_take_priority_without_changing_source_tree(self):
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp) / "project"
            source = project / "assets/resource"
            source.mkdir(parents=True)
            external = Path(temp) / "external"
            external.mkdir()
            with patch.dict(os.environ, {"MAAFGO_RESOURCE_DIR": str(external)}):
                self.assertEqual(resource_roots(project), (external.resolve(), source.resolve()))

    def test_cli_support_contract_and_no_random_or_refill(self):
        nodes = runner.story_overrides(2, True)
        attach = nodes["助战action"]["attach"]
        required = {"class_name", "class_all", "servant", "礼装状态", "np_level", "level",
                    "普通助战-礼装-满破"}
        required |= {f"skill_active_{i}" for i in range(1, 4)}
        required |= {f"skill_passive_{i}" for i in range(1, 6)}
        self.assertTrue(required <= attach.keys())
        self.assertEqual(attach["servant"], KOYAN)
        self.assertFalse(attach["fallback_after_refresh"])
        self.assertEqual(nodes["全局-战前吃体力"]["next"], ["全局-体力不足"])

    def test_britomart_reserves_fox_charge_and_targets_avenger_after_confirmation(self):
        decider = IdoBritomartDecider(_parse_battle_policy({}))
        ready = (SkillState(True, Confidence(1)),) * 3
        servants = tuple(ServantState(slot, ready, Confidence(1), servant_id=sid)
                         for slot, sid in enumerate((KOYAN, PRINCESS, JALTER), 1))
        state = BattleState(Scene.MAIN_BATTLE, Confidence(1), (), (), (), servants=servants)
        trash = decider.decide(state)
        self.assertFalse(any(skill.servant_slot == 1 for skill in trash.servant_skills))
        decider.boss_seen = True
        boss = decider.decide(state)
        fox_skills = [skill for skill in boss.servant_skills if skill.servant_slot == 1]
        self.assertEqual([skill.target_ally for skill in fox_skills], [3, 3, 3])
        self.assertTrue(any(skill.servant_slot == 3 and skill.skill_index == 3
                            for skill in boss.servant_skills))

    def test_britomart_never_guesses_a_missing_avenger_target(self):
        decider = IdoBritomartDecider(_parse_battle_policy({}))
        decider.boss_seen = True
        ready = (SkillState(True, Confidence(1)),) * 3
        state = BattleState(Scene.MAIN_BATTLE, Confidence(1), (), (), (),
                            servants=(ServantState(1, ready, Confidence(1), servant_id=KOYAN),))
        self.assertFalse(decider.decide(state).servant_skills)

    def test_britomart_preserves_avenger_np_when_no_princess_cards_are_dealt(self):
        decider = IdoBritomartDecider(_parse_battle_policy({}))
        cards = tuple(CommandCard(i, CardColor.BUSTER, 3, Confidence(1),
                                  owner_confidence=Confidence(1), owner_servant_id=JALTER)
                      for i in range(1, 6))
        state = BattleState(Scene.COMMAND_SELECTION, Confidence(1), cards,
                            (NpCard(3, Confidence(1), owner_servant_id=JALTER),), ())
        self.assertTrue(all(pick.kind is PrimitiveKind.SELECT_CARD
                            for pick in decider.decide(state).picks))


if __name__ == "__main__":
    unittest.main()
