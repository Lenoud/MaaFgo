"""在 Mac/电脑执行 MaaFgo 原生流程，通过 ADB 控制安卓游戏。"""
from __future__ import annotations

import argparse
import copy
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]


def deep_merge(base, override):
    result = copy.deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


def support_next(name):
    return ["[JumpBack]进本-关闭告知弹窗", name,
            "[JumpBack]进本-自动编队确认", "[JumpBack]进本-编成条件提示",
            "[JumpBack]进本-攻略提示关闭", "进本-队伍确认",
            "进本-战斗主界面已出现", "[JumpBack]进本-盲点跳过剧情"]


def story_overrides(limit, princess=False):
    result = {
        "主线-配置": {"attach": {
            "server": "cn", "quest_limit": limit, "battle_mode": "native",
            "transition_timeout": 120, "auto_handle_restrictions": True,
            "use_spirit_stone": False, "retry_without_spirit_stone": False,
            "princess_double_koyan": princess,
        }},
        "原生自动战斗-高级策略配置": {"attach": {
            "native_battle_strategy_source": "default",
        }},
        "全局-战前吃体力": {"next": ["全局-体力不足"]},
    }
    if princess:
        result = deep_merge(result, {
            "进本流程": {"next": support_next("助战action")},
            "助战action": {"attach": {
                "servant": "604200", "class_name": "暗杀者", "class_all": "def",
                "level": 90, "skill_active_1": "10", "skill_active_2": "10",
                "skill_active_3": "10", "fallback_after_refresh": False,
                "礼装状态": "满破", "普通助战-礼装-满破": "0_空.png", "np_level": 1,
                "skill_passive_1": "0", "skill_passive_2": "0",
                "skill_passive_3": "0", "skill_passive_4": "0", "skill_passive_5": "0",
            }, "action": {"param": {"custom_action_param": {"support_type": "normal"}}}},
        })
    return result


def resolve_device(adb, requested):
    if requested:
        return requested
    output = subprocess.check_output([adb, "devices"], text=True)
    devices = [line.split()[0] for line in output.splitlines()[1:]
               if len(line.split()) >= 2 and line.split()[1] == "device"]
    if len(devices) != 1:
        raise ValueError("请连接唯一安卓设备，或通过 --device 显式指定设备")
    return devices[0]


def run(args):
    from maa.agent_client import AgentClient
    from maa.controller import AdbController, MaaAdbInputMethodEnum, MaaAdbScreencapMethodEnum
    from maa.resource import Resource
    from maa.tasker import Tasker
    from maa.toolkit import Toolkit

    adb = shutil.which(args.adb)
    if not adb:
        raise ValueError("未找到 adb，请安装 Android platform-tools")
    device = resolve_device(adb, args.device)
    resources = args.resource_dir.resolve()
    if not (resources / "base" / "pipeline").is_dir():
        raise ValueError("--resource-dir 需要指向包含 base/cn 的编译后 resource 目录")
    runtime = args.runtime_dir.resolve()
    runtime.mkdir(parents=True, exist_ok=True)
    Toolkit.init_option(runtime)
    resource = Resource()
    resource.use_cpu()
    for layer in ("base", args.server):
        if not resource.post_bundle(resources / layer).wait().status.succeeded:
            raise RuntimeError(f"资源加载失败：{layer}")
    controller = AdbController(
        adb, device,
        screencap_methods=MaaAdbScreencapMethodEnum.RawWithGzip | MaaAdbScreencapMethodEnum.Encode,
        input_methods=MaaAdbInputMethodEnum.AdbShell,
    )
    started = time.monotonic()
    if not controller.post_connection().wait().status.succeeded:
        raise RuntimeError("ADB 控制器连接失败")
    print(f"ADB 连接完成，用时 {time.monotonic() - started:.2f} 秒", flush=True)
    tasker = Tasker()
    if not tasker.bind(resource, controller):
        raise RuntimeError("无法绑定 MaaFgo 资源和控制器")
    client = AgentClient.create_tcp()
    client.bind(resource)
    client.register_sink(resource, controller, tasker)
    agent_log = (runtime / "agent-output.log").open("a", encoding="utf-8")
    agent = subprocess.Popen(
        [sys.executable, "-u", str(ROOT / "agent" / "main.py"), client.identifier],
        cwd=ROOT, stdout=agent_log, stderr=subprocess.STDOUT,
        env={**os.environ, "MAAFGO_RESOURCE_DIR": str(resources)},
    )
    try:
        if not client.connect():
            raise RuntimeError(f"Python Agent 连接失败，请检查 {runtime / 'agent-output.log'}")
        overrides = story_overrides(args.quest_limit, args.princess_double_koyan)
        overrides = deep_merge(overrides, {
            "主线-配置": {"attach": {"server": args.server}},
            "资源包配置": {"attach": {"resource_package": "cn" if args.server == "cn" else "base"}},
        })
        if args.first_battle_profile:
            normal_next = overrides.get("进本流程", {}).get("next", support_next("进本-选择助战"))
            avenger = story_overrides(args.quest_limit, True)
            avenger["助战action"]["attach"].update({
                "servant": "1100300", "class_name": "复仇者", "level": 100,
                "np_level": 3, "普通助战-礼装-满破": "黑之圣杯.png",
                "search_all_support_slots": True, "max_swipes_before_refresh": 48,
            })
            overrides = deep_merge(overrides, {
                "主线-配置": {"attach": {"first_battle_profile": args.first_battle_profile,
                                         "normal_support_next": normal_next}},
                "进本流程": avenger["进本流程"], "助战action": avenger["助战action"],
            })
        if args.overrides:
            overrides = deep_merge(overrides, json.loads(args.overrides.read_text(encoding="utf-8")))
        (runtime / "effective-overrides.json").write_text(
            json.dumps(overrides, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"开始 MaaFgo 流程：{args.entry}；上限 {args.quest_limit} 关", flush=True)
        job = tasker.post_task(args.entry, overrides)
        try:
            while not job.done:
                time.sleep(0.2)
        except KeyboardInterrupt:
            print("正在停止 MaaFgo，保留游戏现场……", flush=True)
            tasker.post_stop().wait()
            return 130
        detail = job.get()
        print(f"流程结束：success={job.status.succeeded} task_id={job.job_id}", flush=True)
        (runtime / "last-result.json").write_text(
            json.dumps({"success": job.status.succeeded, "entry": args.entry,
                        "task_id": job.job_id, "detail": str(detail)}, ensure_ascii=False, indent=2),
            encoding="utf-8")
        return 0 if job.status.succeeded else 1
    finally:
        client.disconnect()
        if agent.poll() is None:
            agent.terminate()
            try:
                agent.wait(timeout=10)
            except subprocess.TimeoutExpired:
                agent.kill()
                agent.wait()
        agent_log.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--resource-dir", type=Path, required=True,
                        help="编译后的资源目录，内含 base 和 cn/jp")
    parser.add_argument("--device", help="ADB 设备地址；省略时要求唯一在线设备")
    parser.add_argument("--adb", default="adb", help="adb 命令或路径")
    parser.add_argument("--server", choices=("cn", "jp"), default="cn", help="服务器资源")
    parser.add_argument("--quest-limit", type=int, default=2, help="推进上限，默认先验收两关")
    parser.add_argument("--princess-double-koyan", action="store_true",
                        help="普通关查找满技能光狐，实际双杀公主前排才启用三回合方案")
    parser.add_argument("--entry", default="自动推主线调度", help="MaaFgo pipeline 入口")
    parser.add_argument("--first-battle-profile", choices=("ido-britomart",),
                        help="首场战斗使用指定关卡攻略，目前仅奏章Ⅱ第六节进行度3")
    parser.add_argument("--overrides", type=Path, help="额外 pipeline JSON 覆盖文件")
    parser.add_argument("--runtime-dir", type=Path, default=ROOT / ".runtime" / "mac-adb",
                        help="私有运行日志和有效配置目录，不提交 Git")
    args = parser.parse_args()
    if not 1 <= args.quest_limit <= 999:
        parser.error("--quest-limit 必须为 1～999")
    try:
        return run(args)
    except (ValueError, RuntimeError) as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
