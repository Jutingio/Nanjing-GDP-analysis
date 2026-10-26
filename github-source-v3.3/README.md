# 南京地理数据可视化 · Blender + Python

在现有 V3.2 的 60 秒地球 → 南京 → 雨花台/玄武/鼓楼 → 地球动画上整理。沿用原基础工程、玻璃 HUD、照片、轨道粒子和镜头，配置入口为 `config/nanjing.json`。本项目不是官方行政地图或统计核算系统，原创源码采用 MIT，署名 Jutingio；第三方原资产的分发仍按来源清单逐项核查。

## 目录

```text
src/           纯 Python 数据、时间轴、配置与校验
scripts/       原有 Blender 构建/渲染入口及准备、审计脚本
config/        南京配置、待填换城模板、JSON Schema
data/          统计快照、引用、schema、合成示例；geo/camera 为本地输入
assets/        原 GeoJSON、照片、地球贴图、字体和来源清单
inputs/        保留的南京基础 .blend（必须单独准备）
output/        新场景、报告、预览、帧序列与成片，不提交
tests/         纯 Python、配置、来源和已有缓存测试
docs/          口径、资产、许可、发布检查与整理方案
```

旧 `build/ render/ previews/ deliverables/` 留在本地；原资产不移动、不删除。原脚本文件名保留，主要构建链现在从配置读输入并写 `output/nanjing/`。其他旧检查/修补/打包脚本仍面向旧交付，不作为新流程入口。原版说明保存在本次整理的备份中，不作为当前复现指南。

## 环境和资源

本机实际执行 `blender --version`：**Blender 5.2.2 LTS**，build d13f752e3b9c；原文档记录制作时 5.2.1 LTS。本次不能据此保证 Blender 4.x 或 6.x 兼容。外部 Python 实测 **3.13.5**、Pillow 11.1.0、NumPy 2.1.3；配置验证本身仅使用标准库。`bpy` 来自 Blender 自带 Python，不用 pip 安装。

在项目根目录执行（Windows PowerShell 可将 `blender` 替换为 `& "本机路径/blender.exe"`）：

```sh
python -m venv .venv
# 激活虚拟环境，再安装；不要修改 Blender 内置 Python。
python -m pip install -r requirements-dev.txt
python scripts/prepare_project.py --config config/example.json --schema-only
python scripts/prepare_project.py --config config/nanjing.json
python -m unittest discover -s tests -v
```

先按 [资源说明](docs/resources.md) 和配置路径补齐资源。当前本机资源齐备；源码白名单不会带上未经逐项批准的二进制或源网页摘录。缺少基础工程时不能复现完整影片。`prepare_project.py` 验证年份、来源 hash、选区、地理代码、基础工程 hash、照片与镜头文件，不改写数字。原 `prepare_data.py --verified-extract` 是南京专用历史采集入口，会重写快照；日常复现不需要运行，也不再隐式复制相邻旧版工程。

## 从数据到场景再到渲染

```sh
blender --background --disable-autoexec inputs/nanjing-base.blend --python-exit-code 1 --python scripts/build_v3.py -- --config config/nanjing.json
blender --background --disable-autoexec output/nanjing/build/nanjing-v3.blend --python-exit-code 1 --python scripts/validate_v3.py -- --config config/nanjing.json
blender --background --disable-autoexec output/nanjing/build/nanjing-v3.blend --python-exit-code 1 --python scripts/render_v3.py -- --config config/nanjing.json --frames 91,601,751,1021,1261 --scale 50 --samples 4
```

配置默认 `camera.mode=preserve`，逐帧比对 1801 帧的原镜头记录，保留基础工程动画。`track` 模式显式重烘焙独立轨迹，可设置公里单位 location_offset、lens_scale；需要重新检查引线、构图和遮挡。build 会校验基础工程与预处理网格的顶点一致性，并把配置写入场景和 config-used.json。渲染拒绝与场景不一致的配置；配置更改后重新构建。预览不会覆盖原始成片。`--samples` 只覆盖三维世界采样，HUD 与遮罩使用配置 hud_samples。构建绑定输入文件 hash，输入变化后须重建。

完整直接渲染（耗时较长）：

```sh
blender --background --disable-autoexec output/nanjing/build/nanjing-v3.blend --python-exit-code 1 --python scripts/render_v3.py -- --config config/nanjing.json --start 1 --end 1800
python scripts/encode_v3.py --config config/nanjing.json --job output/nanjing/render/JOB_ID --ffmpeg PATH_TO_FFMPEG
```

JOB_ID 从渲染输出读取；编码需要 FFmpeg 的 libx264，逐帧检查后完整解码验证，输出 `output/nanjing/deliverables/nanjing-60s.mp4`。FFmpeg 不分发，本轮未重编码全片。第 1801 帧仅用于闭环检查，不编码。

原缓存加速链也保留：`cache_hud.py`（Blender 打开新场景）→ `prepare_particle_sequence.py`（外部 Python）→ `render_layer_cache.py`（Blender 打开新场景）→ `encode_v3.py`。各入口均可传 `--config`；缓存方案固定 960×540，使用配置的 samples/hud_samples，配置 scale 必须为 50。完整缓存渲染本轮若未执行，不代表已验证。需要其他分辨率时用上面的直接渲染入口。版式和时间轴保持 1920×1080 / 30fps / 60秒，校验会拒绝不支持的改动。

## 换城市与离线演示

已新增 `prepare_city_geo.py` 和 `build_city_base.py`，可从另一座城市的 WGS84 区界生成预处理网格、基础地球工程和1801帧镜头，再复用现有V3构建/渲染链。需要提供真实统计数据、文化介绍和有权使用的素材；固定三地区、60秒版式。

源码克隆不带南京原资产，也可以运行离线合成演示：先安装 `requirements-geo.txt`，再运行 `create_demo_city.py`、`prepare_city_geo.py`、`build_city_base.py` 和现有 `build_v3.py`。完整命令、真实城市输入契约和适用限制见 [换城市操作](docs/city-migration.md)。

原南京配置仍使用保留的基础工程。通用适配器已用两组不同坐标的合成城市验证，不把演示数字作为真实城市统计。

## 数据、归属与发布

2024 南京市 GDP **18500.81 亿元**，分板块公布数合计 **18479.96 亿元**，差 **20.85**；保留原值，不机械补差。与江北新区直管区同指标项下，浦口、六合采用剔除直管区的板块统计口径。当前三区使用全市公布值作分母，2017 概览边界不能替代当期核算边界。详见 [数据来源及引用](docs/data-sources.md)。

原创源码与文档采用 **MIT**，版权署名 **2026 Jutingio**，见 LICENSE。地图衍生数据、字体、照片、NASA 素材各有独立来源与条件，见 [资源许可核查](docs/resources.md)、[代码许可建议](docs/licensing.md)、CITATION.cff。照片原页标注 Fumikas Sagisavas / CC0 1.0，地图署名须包含 OpenStreetMap contributors / geoBoundaries，水系为 Natural Earth；特定地球贴图和字体文件的来源链仍需补核。

源码发布文件已补齐，可运行 `python scripts/export_source.py` 导出 `output/github-source.zip`；上传步骤及 CI 说明见 [GitHub 上传](docs/github-upload.md)。目前项目目录不是 Git 仓库，没有初始化或推送。请先完成 [公开前检查清单](docs/publishing.md)，运行 `python scripts/audit_publication.py`，审阅候选文件及原仓库历史（如另有仓库）。`.gitignore` 不会删除本地资产，也不能清除已跟踪文件或历史密钥。
