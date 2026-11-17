"""用当前敌人名称确认布里托玛特阶段，不根据回合数猜测面数。"""
import mfaalog
from ..core.enums import Scene
from .runtime import AutoBattleRuntime


class IdoBritomartRuntime(AutoBattleRuntime):
    def _observe(self, **kwargs):
        state = super()._observe(**kwargs)
        if state.scene is Scene.MAIN_BATTLE and not self.decider.boss_seen:
            image = self.controller.post_screencap().wait().get()
            if image is not None:
                name = "奏章二-确认布里托玛特"
                result = self.ctx.run_recognition(name, image, pipeline_override={name: {
                    "recognition": {"type": "OCR", "param": {
                        "roi": [0, 0, 850, 140],
                        "expected": ["布里托玛特|ブリトマート|Britomart"],
                    }},
                }})
                if result and result.hit:
                    self.decider.boss_seen = True
                    mfaalog.info("[奏章二专用] 已识别布里托玛特；增益、充能、宝具与补牌转给复仇者黑贞")
        return state
