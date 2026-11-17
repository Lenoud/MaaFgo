# Mac ADB 验收记录

更新日期：2026-11-17。使用 MaaFramework 5.14.3、Apple Silicon Mac、国服资源及真实安卓手机，手机约4GB内存。原始截图、设备标识和账号运行日志不公开提交。

| 检查项 | 当前结果 |
|---|---|
| Mac 加载 MaaFgo 资源、连接 Python Agent 和安卓 ADB | 已实测通过 |
| Mac 原生 ADB 截图 | 实测约0.34秒；连接约1.5秒 |
| 静态截图单项 OCR | 首次约0.17秒、热运行约0.03秒；只代表该样本和 ROI |
| 初始编队身份识别 | 手机约31秒，Mac 约2.45秒 |
| 助战转编队状态复核 | 手机一次实测155.8秒，Mac 一次实测20.2秒；样本状态不完全相同，不作为严格性能基准 |
| 双杀公主第一回合 | 实测按顺序给公主二、三技能增益，公主二技能，成功选择公主宝具 |
| 第二回合 | 实测双光狐一技能给公主，成功选择公主宝具 |
| 第三回合 | 实测公主一、三、二技能，成功选择公主宝具 |
| 公主补牌优先级 | 离线真实决策器测试通过：公主宝具→公主红卡→公主其他卡；实机遇到部分卡牌归属未知，不能宣称每手都完全识别 |
| 特殊主线 Boss | 已确认普通三回合方案不适用；专用策略能识别 Boss 并切换黑贞，但低配置 NPC 实测战败 |
| 战斗→结算→下一关的完整主线循环 | 尚未通过，不能宣称已完成主线无人值守验收 |

离线验证包括新增的参数编码、槽位绑定、外部资源目录、助战参数完整性与专用策略检查，以及原有的选卡、冷却和主线调度相关测试。运行方式：

```bash
.venv-mac/bin/python -m unittest discover -s tests -p test_mac_adb_profile.py
.venv-mac/bin/python -m unittest discover -s tests -p test_battle_native_card_strategy.py
.venv-mac/bin/python -m unittest discover -s tests -p test_battle_planned_cooldowns.py
.venv-mac/bin/python -m unittest discover -s tests -p test_main_story.py
```

后续验收必须在没有人手动战斗的情况下，确认胜利、结算、返回章节地图及自动启动下一关；纯剧情关的计数与真实战斗场数分别核对。
