"""从已安装并解包资源的 MaaFgo 安卓版读取游戏识别资源。"""
import argparse
from pathlib import Path
import shutil
import subprocess
import tempfile

from mac_adb_runner import ROOT, resolve_device


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--device", help="ADB 设备地址")
    parser.add_argument("--adb", default="adb", help="adb 命令或路径")
    parser.add_argument("--output", type=Path, default=ROOT / ".runtime/resources",
                        help="本地资源目录，不包含用户配置或运行日志")
    args = parser.parse_args()
    adb = shutil.which(args.adb)
    if not adb:
        parser.error("未找到 adb，请安装 Android platform-tools")
    try:
        device = resolve_device(adb, args.device)
    except ValueError as exc:
        parser.error(str(exc))
    source = "/sdcard/Android/data/com.aliothmoon.maafw.maafgo/files/pi/resource"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="maafgo-resources-", dir=args.output.parent) as temp:
        subprocess.run([adb, "-s", device, "pull", source, temp], check=True)
        shutil.copytree(Path(temp) / "resource", args.output, dirs_exist_ok=True)
    if not (args.output / "base/pipeline").is_dir():
        raise SystemExit("没有找到完整资源，请先在 MaaFgo 安卓版完成资源解包")
    print(f"已读取识别资源：{args.output.resolve()}")


if __name__ == "__main__":
    main()
