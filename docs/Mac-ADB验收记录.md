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
| 特殊主线 Boss | 普通方案、低配置 NPC 方案实测战败；改用110级、宝具3、10/10/10、满破黑之圣杯好友黑贞后，专用策略8回合独立通关 |
| 战斗→结算→下一关的主线循环 | 20:54实测胜利并结算，20:55自动进入并完成下一段剧情，最终推进2/2关、战斗1场，框架返回success=True |
| 无人值守范围 | 本轮战斗和下一关由 MaaFgo 完成，无人工选卡、技能或结算输入；不能据此宣称已验证整章所有机制关或连续两场战斗 |

离线验证包括新增的参数编码、槽位绑定、外部资源目录、助战参数完整性与专用策略检查，以及原有的选卡、冷却和主线调度相关测试。运行方式：

```bash
.venv-mac/bin/python -m unittest discover -s tests -p test_mac_adb_profile.py
.venv-mac/bin/python -m unittest discover -s tests -p test_battle_native_card_strategy.py
.venv-mac/bin/python -m unittest discover -s tests -p test_battle_planned_cooldowns.py
.venv-mac/bin/python -m unittest discover -s tests -p test_main_story.py
```

本轮验收从中断战斗的实际前排候选恢复，随后由同一主线任务完成胜利、结算及下一段剧情。纯剧情关的计数与真实战斗场数分别核对。后续需要继续扩大机制关与连续战斗覆盖范围；不把一次样本的成功推广为全章通解。
