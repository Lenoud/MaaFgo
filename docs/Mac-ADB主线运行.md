# Mac 计算、安卓运行游戏

本分支增加命令行运行入口：MaaFramework、OCR、助战筛选、卡牌识别、主线调度和 Python Agent 在 Mac 执行，通过 USB ADB 截图与输入控制安卓游戏。安卓端仅运行游戏，不需要同时启动 MaaFgo 悬浮窗任务。

仍复用 MaaFgo 的 pipeline 和原生自动战斗逻辑。主线任务自行寻找 NEXT、选择助战、进入战斗、结算并返回地图，不需要操作者逐回合点击。

## 安装

已验证运行环境为 Apple Silicon、Python 3.12、MaaFramework 5.14.3。其他平台尚未完成实机验证。

```bash
brew install python@3.12 android-platform-tools
git clone https://github.com/Lenoud/MaaFgo.git
cd MaaFgo
python3.12 -m venv .venv-mac
.venv-mac/bin/python -m pip install -r tools/mac_requirements.txt
```

手机开启 USB 调试并允许电脑连接。运行 `adb devices` 确认状态为 `device`。同一时间只运行一个游戏控制程序。

## 获取识别资源

Python 代码和模型、图片资源分别加载。可使用 v2.0.27 编译发布包中的 `resource` 目录，或者从已经安装并完成解包的 MaaFgo 安卓版读取：

```bash
.venv-mac/bin/python tools/pull_android_resources.py
```

读取范围仅为应用外部文件中的 `pi/resource`，不会读取用户配置、账号画面或日志；不需要 root。资源默认保存在被 Git 忽略的 `.runtime/resources`。

资源目录应直接包含 `base/` 和 `cn/` 或 `jp/`。外部资源路径通过 `MAAFGO_RESOURCE_DIR` 同时传给 Python Agent，使助战、初始编队、卡牌归属、从者状态和 NEXT 识别使用同一套资源。

## 运行主线

先在手机上进入当前章节地图、副本列表、助战页或队伍确认页。默认推进两关，适合先验收循环：

```bash
.venv-mac/bin/python tools/mac_adb_runner.py \
  --resource-dir .runtime/resources \
  --server cn \
  --quest-limit 2
```

`Ctrl+C` 会先停止 MaaFramework 任务，再断开并结束 Python Agent，保留游戏现场。多设备时使用 `--device` 指定 ADB 地址。

任务中断后若游戏仍在战斗页，可通过 `--resume-roster` 传入六个从者ID候选（逗号分隔，未知位置留空），恢复本场并继续结算和下一关。候选应来自此前真实编队记录；它们只用于缩小当前画面识别范围，不代替实时身份识别，也不生成虚假的初始编队采样。仅对本次运行第一场生效，后续关卡重新采集编队。

默认不补充苹果、不使用灵脉石。`.runtime/mac-adb/effective-overrides.json` 保存实际参数，`last-result.json` 保存框架任务结果。Agent 详细识别日志保存在被忽略的 `debug/recognition-*.log`；运行输出保存在 `.runtime/mac-adb/agent-output.log`。

只有完成战斗、结算并正确返回地图后，主线调度才累加关数。纯剧情关也计入推进上限，因此验证战斗循环时还应核对日志里的完成战斗场数。

## 双杀狐与公主

```bash
.venv-mac/bin/python tools/mac_adb_runner.py \
  --resource-dir .runtime/resources \
  --quest-limit 2 \
  --princess-double-koyan
```

手机当前队伍需已有自有光之高扬斯卡娅和 Archetype：Earth。此选项查找 90 级、主动技能 10/10/10 的光狐助战，不随机换成其他从者；不自动重排自有队伍或更换礼装。

仅在实测初始前排确认为两名光狐和一名公主时按身份绑定槽位，执行以下方案；已有导入计划优先，不覆盖已设置的计划：

| 回合 | 技能顺序 | 出卡 |
|---|---|---|
| 1 | 两名光狐的二、三技能均给公主，再用公主二技能 | 公主宝具；补牌优先公主红卡，再选公主其他卡 |
| 2 | 两名光狐一技能均给公主 | 同上 |
| 3 | 公主一、三技能，再用公主二技能 | 同上 |

技能仍受实机冷却、封印、NP 和行动限制检查。第三回合二技能能否转好，取决于实际技能等级及相关初始冷却条件；本方案不保证任意培养程度都能三连发。日志中的 `[双杀公主]` 和 `plan=loaded plan_turns=3` 才代表方案已启用，单纯选中光狐助战不算方案执行成功。

该方案按回合执行，不能把“第三回合”自动等同于“第三面”。若第一面没清掉、出现 Break 或剧情机制，三回合计划结束后会回到原生通用策略，不能宣称已经完成三回合验收。

## 特殊主线关卡

主线原生调度已有编制限制处理，可按游戏的固定队伍或多个 NPC 要求继续；限制关会清除普通队伍方案并采用通用战斗逻辑。这不代表支持全部特殊 Boss。

宝具封印、强制单挑、特定支援、Break、多阶段无敌、指定技能解机制等关卡，需要专用计划或额外识别逻辑。遇到这些关卡，应保留失败现场并分析，不把延长超时或手动打过当成自动验收成功。

### 实验性：奏章Ⅱ第六节进行度3

该关布里托玛特〔Alter〕有非复仇者耐性及额外特殊耐性，击破第一条血后结束战斗。普通双杀公主方案不适用。[关卡机制资料](https://fgo.wiki/w/奏章Ⅱ_不可逆废弃孔_伊底/关卡配置)

```bash
.venv-mac/bin/python tools/mac_adb_runner.py \
  --resource-dir .runtime/resources \
  --first-battle-profile ido-britomart \
  --quest-limit 2
```

本方案显式用于本次运行的第一场战斗，不会自动判断整章所有关卡。它查找100级以上、宝具至少3、主动技能10/10/10且装备满破黑之圣杯的黑贞助战；找不到时不随机替代。游戏内需要已有光狐和公主。仅实际确认前排有黑贞才启动专用战斗逻辑。

前两面以公主处理杂兵并保留复仇者的宝具；OCR 确认敌人名字包含布里托玛特后，将光狐充能与增益、宝具和补牌重点转给黑贞。若与 `--princess-double-koyan` 同用，首场结算后恢复普通关卡的光狐助战配置。

**当前为实验性攻略，已完成该关单样本实机通关。** 110级、宝具3、10/10/10、满破黑之圣杯好友黑贞实测8回合通关，并由主线调度自动完成后续纯剧情关。低配置 NPC 黑贞实测未通关；不能把该关样本推广为全章通解。详见 [验收记录](Mac-ADB验收记录.md)。

## 自定义与诊断

`--overrides 文件.json` 可深度合并额外 pipeline 参数，列表整体替换。`--entry` 可选择已有 MaaFgo pipeline 入口，供流程验证使用。不会启动任意外部脚本。

手机端同时进行 OCR 和游戏可能出现明显竞争与低内存回收。本分支的目的就是将计算移到电脑；静态截图的单项 OCR 速度不能代表完整战斗速度。完整验收仍需检查至少两关的自动开战、正确技能与出卡、结算及下一关循环。
