# City Geography Film · 城市地理数据可视化

使用 **Blender + Python**，把城市地图、统计数据和文化介绍制作成一段 60 秒的地理数据可视化影片。

项目以南京为首个案例，包含地球视角、镜头推进、城市概览、三个地区的数据展示，以及返回地球的闭环动画。通过独立配置、地理数据预处理和基础场景生成脚本，可以将这套流程迁移到其他城市。

**作者：** [Jutingio](https://github.com/Jutingio) · **版本：** 3.3.0 · **源码许可：** [MIT](LICENSE)

> **AI 协作说明：** 本项目在 AI 的辅助下开发，AI 参与了方案讨论、代码编写与重构、测试及文档整理。具体参与范围与验证边界见下文。

## 项目特点

- **配置驱动**：城市名称、统计年份、数据与素材路径、镜头和渲染参数集中管理。
- **数据驱动展示**：从统计快照读取 GDP、人口与社会消费品零售总额，按官方全市值计算地区占比。
- **地理场景生成**：从 WGS84 GeoJSON 生成地区网格、边界和定位锚点，支持多面与孔洞。
- **保留原南京影片**：南京配置沿用已有基础工程；其他城市使用独立基础场景生成入口。
- **可复现的动画**：镜头和动画烘焙为关键帧，保存的场景不依赖自动运行回调脚本。
- **离线合成演示**：无需南京原素材，也能生成一套演示输入并运行构建、验证和抽帧。
- **输入与缓存校验**：校验年份、地区代码、文件摘要和场景配置，拒绝错配输入与过期缓存。

## 源码、视频和素材有什么区别？

| 内容 | 源码包是否包含 | 用途 |
| --- | --- | --- |
| Python 脚本、配置模板、文档、测试 | 包含 | 阅读、修改和运行项目 |
| 统计数字快照、来源元数据、合成数据示例 | 包含 | 数据校验与演示 |
| 南京原始 `.blend`、地图、照片、字体和贴图文件 | 默认不包含 | 补齐后复现原南京影片 |
| 已经生成的完整 MP4 | 默认不包含 | 可作为独立演示文件另行发布 |
| 渲染帧、缓存、日志和本机配置 | 不包含 | 本地生成 |

**源码包不是完整视频文件包。** 解压后没有 `deliverables/` 文件夹，并不表示视频被删除；源码包默认没有收录成片。完成本项目的全帧渲染和编码后，新视频写入：

```text
output/<city-id>/deliverables/<city-id>-60s.mp4
```

如果只执行下面的抽帧命令，会生成 PNG 预览，不会生成完整 MP4。视频与原素材的发布条件也需要分别判断，详见 [源码、成片与素材说明](docs/code-video-assets.md)。

## 环境要求

| 工具 | 要求与验证状态 |
| --- | --- |
| Blender | 本机验证版本为 **5.2.2 LTS**；未验证 4.x / 6.x |
| 外部 Python | 本机验证版本为 **3.13.5**；CI 配置为 3.12 / 3.13 |
| Python 依赖 | `requirements-geo.txt` 包含运行、测试和地理预处理依赖 |
| FFmpeg | 编码 MP4 时需要支持 `libx264` 的版本，需自行安装 |

`bpy` 使用 Blender 自带的 Python 环境。请用 Blender 执行涉及 `bpy` 的脚本，不要通过外部 Python 安装或运行 `bpy`。

以下命令均在项目根目录执行。确保 `python`、`blender` 在 PATH 中；Windows PowerShell 也可以用 `& "你的Blender路径/blender.exe"` 替换命令中的 `blender`。

## 快速开始：离线合成演示

这个入口不需要下载南京的照片、地图、字体或基础工程。生成的地图、图片和统计数字均为**合成演示内容，不代表真实城市**。

### 1. 安装外部 Python 依赖

建议先创建并激活虚拟环境：

```sh
python -m venv .venv
```

Windows PowerShell：

```powershell
.\.venv\Scripts\Activate.ps1
```

macOS / Linux：

```sh
source .venv/bin/activate
```

安装依赖并运行测试：

```sh
python -m pip install -r requirements-geo.txt
python -m unittest discover -s tests -v
```

源码包不含南京原资产，因此相应的来源、缓存和原场景输入检查会明确显示 `skipped`；纯 Python 与几何测试仍可执行。

### 2. 生成演示输入和地理网格

```sh
python scripts/create_demo_city.py
python scripts/prepare_city_geo.py --config config/demo.local.json
```

生成的输入位于 `data/generated-demo/`，配置位于 `config/demo.local.json`。

### 3. 生成基础场景、镜头和影片场景

```sh
blender --background --factory-startup --disable-autoexec --python-exit-code 1 --python scripts/build_city_base.py -- --config config/demo.local.json
python scripts/prepare_project.py --config config/demo.local.json
blender --background --disable-autoexec data/generated-demo/base.blend --python-exit-code 1 --python scripts/build_v3.py -- --config config/demo.local.json
```

基础场景生成器会写入相机轨迹、基础工程的 SHA-256，并将该配置标记为可运行。影片场景写入 `output/demo/build/nanjing-v3.blend`。

> `nanjing-v3.blend` 是保留的兼容文件名。城市由配置和数据决定，不由这个文件名决定。

### 4. 验证场景并渲染预览

```sh
blender --background --disable-autoexec output/demo/build/nanjing-v3.blend --python-exit-code 1 --python scripts/validate_v3.py -- --config config/demo.local.json
blender --background --disable-autoexec output/demo/build/nanjing-v3.blend --python-exit-code 1 --python scripts/render_v3.py -- --config config/demo.local.json --frames 91,751 --scale 25 --samples 4
```

预览保存到 `output/demo/previews/`。`--scale 25` 对应 480×270 输出；`--samples` 控制三维世界采样，HUD 采样由配置中的 `hud_samples` 控制。

输入生成器会拒绝覆盖已有输入。若需要另一套演示，可使用独立名称和坐标，例如：

```sh
python scripts/create_demo_city.py --id demo-two --origin 103.17,24.05
```

后续命令使用 `config/demo-two.local.json` 和对应的 `data/generated-demo-two/`、`output/demo-two/` 路径。

## 渲染完整视频

场景验证通过后，渲染第 1–1800 帧：

```sh
blender --background --disable-autoexec output/demo/build/nanjing-v3.blend --python-exit-code 1 --python scripts/render_v3.py -- --config config/demo.local.json --start 1 --end 1800
```

日志会显示本次任务目录，例如 `output/demo/render/JOB_ID`。将实际任务编号和 FFmpeg 可执行文件路径填入以下命令：

```sh
python scripts/encode_v3.py --config config/demo.local.json --job output/demo/render/JOB_ID --ffmpeg PATH_TO_FFMPEG
```

编码器检查帧序列并对结果进行完整解码验证，成功后输出：

```text
output/demo/deliverables/demo-60s.mp4
```

默认影片为 **60 秒、30 fps、无音轨**。第 1801 帧是循环衔接检查帧，不编码为重复末帧。分辨率由配置中的 `render.scale` 控制；场景原始版式为 1920×1080。

原缓存加速链也保留在 `cache_hud.py`、`prepare_particle_sequence.py` 和 `render_layer_cache.py` 中，适用于固定 960×540 的缓存方案。初次运行建议先使用上面的直接渲染流程。

## 换成真实城市

复制 `config/example.json` 为该城市的独立配置，然后准备：

1. **统计快照**：同一统计年度的全市总量、地区值、三个展示地区代码和来源记录。
2. **地区边界**：WGS84 / EPSG:4326 的 GeoJSON，包含 `regionCode` 和 `name`。
3. **城市介绍**：历史、景点、照片标题与年份，以及照片 SHA-256。
4. **素材**：有权使用的照片、地球贴图和字体；中文城市需使用支持中文的字体。
5. **配置**：城市名称、ENU 原点、边界年份、各输入路径、署名与独立输出目录。

处理流程如下：

```text
统计快照 + GeoJSON + 城市介绍 + 素材 + 配置
                    ↓
         prepare_city_geo.py
                    ↓
          build_city_base.py
                    ↓
           prepare_project.py
                    ↓
              build_v3.py
                    ↓
            validate_v3.py
                    ↓
             render_v3.py
                    ↓
             encode_v3.py
```

地区网格采用约束三角剖分，并限制三角面长边，避免大面片切入地球表面。配置和输入文件的摘要会随场景保存；更改数据或素材后需要重新构建场景和缓存。

完整输入格式、命令和边界条件见 [换城市操作](docs/city-migration.md)。

### 当前适用范围

- 固定展示三个地区，影片时长为 60 秒，帧率为 30 fps。
- 面向紧凑城市：纬度范围在 ±75° 内，经纬跨度不超过 8°，不跨 180° 经线。
- 支持 Polygon / MultiPolygon 与孔洞；行政区 PolygonZ 的高度信息按二维边界处理。
- 输入应为 WGS84，不能将 GCJ-02 / BD-09 坐标直接当作 WGS84 使用。
- 通用生成器不会自动抓取官方统计，也不会自动获取当地河流数据。
- 长城市名、长区名和不同形状的城市需要抽帧检查构图与排版。

## 南京案例与统计口径

南京案例采用《南京统计年鉴2025》公布的 **2024 年**数据，展示雨花台、玄武和鼓楼三个区的 GDP、年末常住人口及社会消费品零售总额占全市的比重。

| 项目 | 数值或说明 |
| --- | --- |
| 全市 GDP | 18500.81 亿元 |
| 分板块公布 GDP 合计 | 18479.96 亿元 |
| 两者算术差额 | 20.85 亿元，保留公布数，不机械补差 |
| 占比分母 | 同年官方全市公布值，而非展示区之和或区级最大值 |
| 地图 | 2017 年概览边界，不等同于 2024 年精确核算边界 |

与江北新区直管区同一指标项下，浦口区、六合区的数据采用剔除该直管区后的统计口径。直管区不是额外的行政区，不能把统计板块与行政区边界直接混用。

数据表链接、来源记录与限制见 [数据来源及口径](docs/data-sources.md)。

复现原南京影片需要另外补齐 `config/nanjing.json` 指向的原输入。资源齐备时，从以下检查开始：

```sh
python scripts/prepare_project.py --config config/nanjing.json
```

随后使用已有 `inputs/nanjing-base.blend` 执行 `build_v3.py`，无需运行新城市基础场景生成器。素材准备要求见 [资源说明](docs/resources.md)。

## 目录结构

```text
.
├── .github/workflows/       GitHub Actions 源码与地理预处理检查
├── src/                    数据、时间轴、坐标转换与配置校验
├── scripts/                地理准备、场景生成、渲染、编码和源码导出
├── config/                 南京配置、换城模板和配置 Schema
├── data/                   统计快照、来源元数据、Schema 与合成示例
├── assets/                 来源清单；原素材需另行准备
├── inputs/                 本地基础工程，源码包不含原二进制
├── output/                 本地生成的场景、预览、帧序列和成片
├── tests/                  自动化测试
├── docs/                   数据口径、城市迁移、资源与发布说明
├── requirements*.txt       外部 Python 依赖
├── CITATION.cff             项目引用信息
└── LICENSE                 原创源码 MIT 许可证
```

`inputs/` 等本地资源目录可能不出现在源码包中；生成内容及 `*.local.json` 默认不纳入 Git。

## 验证状态

本机已完成：

- 28 项 Python 测试全部通过。
- 原南京场景的 14 项 Blender 检查通过。
- 两组不同坐标的合成城市完成地理准备、基础工程生成、影片场景生成、场景检查及开场/地区定位抽帧。
- 无原南京资产的源码副本完成源码检查和演示预处理；5 项依赖原资产的测试明确跳过。
- 源码导出包的文件筛选、凭据与个人路径启发式检查，以及压缩包完整性检查。

GitHub Actions 配置了 Python 3.12 / 3.13 的源码检查，但未在远端实际运行。完整 60 秒视频的重新渲染与编码、4K 输出、现场循环播放及第二座真实城市的数据核验，均未列为本轮已完成验证。

详细记录见 [V3.3 验证说明](docs/v3.3-validation.md)。

## AI 协作说明

本项目由 [Jutingio](https://github.com/Jutingio) 提出需求并组织迭代，开发过程中使用了 **AI** 进行辅助。本项目并非全部由作者独立手写完成。

AI 参与的工作包括：

- 讨论影片叙事、数据展示方式和 Blender + Python 实现思路。
- 协助编写、调整和重构 Python / Blender 脚本，包括配置管理、地理预处理、镜头、场景和渲染流程。
- 协助编写测试、执行本地验证、排查问题和检查渲染预览。
- 协助整理仓库、README、数据口径、素材来源和发布说明。

**数据与素材来源单独标注：** 南京案例中的统计数字引用官方统计资料，不能解释为 AI 生成或推算的数值；原南京照片、地图、字体和地球贴图也各有来源。离线演示中的地图、数字和插图是 Python 程序生成的合成示例，不代表真实城市，也不是实拍资料。

AI 辅助生成代码不等于结果已经全面正确。本文“验证状态”只列出实际完成的检查，不能据此声称所有代码已由作者逐行审核、所有城市都已适配，或全部素材许可均已核验。维护者仍需审阅修改，并对项目的使用和发布作出判断。

## 许可证与素材署名

原创源码、文档及原创合成演示采用 [MIT License](LICENSE)，版权署名 **2026 Jutingio**。

第三方素材保留各自的许可条件：

| 素材 | 许可或来源记录 |
| --- | --- |
| 南京区界衍生数据 | geoBoundaries / OpenStreetMap，按记录适用 ODbL 1.0 |
| Natural Earth 水系 | Public Domain |
| 南京资料照片 | Fumikas Sagisavas，原页标注 CC0 1.0 |
| Noto Sans CJK 字体家族 | SIL OFL 1.1；特定本地文件来源链仍需补核 |
| NASA 地球贴图 | 按具体图像的来源与 NASA 使用规则核查；特定文件署名链仍需补核 |

**第三方素材不等于必须重新申请授权。** 开放许可证可以允许使用与分发，但应遵守对应条件。发布成片与分发原始字体、地图数据库或素材文件的要求也可能不同。素材未收入源码包，不表示已经判定其禁止发布。

具体来源、文件摘要和核查状态见 [资源清单](docs/resource-manifest.json)、[素材说明](docs/resources.md) 和 [许可说明](docs/licensing.md)。

## 上传与维护

生成源码包：

```sh
python scripts/export_source.py
```

输出为 `output/github-source.zip`。解压后，将里面的源码和文档放入 GitHub 仓库根目录；保留 `.github/` 与 `.gitignore`，以便识别自动测试和忽略规则。

源码包默认不带完整 MP4。需要展示视频时，可根据素材条件另行发布视频，并在 README 中添加实际视频链接。请勿把本机整个渲染目录当作源码上传。

上传步骤见 [GitHub 上传说明](docs/github-upload.md)。引用本项目时，可使用 [CITATION.cff](CITATION.cff)，并分别引用使用的统计表和地理数据。
