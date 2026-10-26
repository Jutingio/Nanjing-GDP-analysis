# 资源准备与许可核查

本地原始文件全部保留。`docs/resource-manifest.json` 记录实际文件大小、SHA-256、来源线索与许可核查状态。未授权把整个旧交付包直接公开；`.gitignore` 默认仅允许源码和来源元数据进入候选清单。

| 资源 | 已核对依据 | 状态 / 准备方式 |
| --- | --- | --- |
| 南京市/区 GeoJSON、准备后网格 | 本地 boundary-metadata.json 指向 geoBoundaries commit 9469f09，2017，Lee Beryman / OpenStreetMap，ODbL 1.0；[OSM 许可页](https://www.openstreetmap.org/copyright) | 有许可依据；衍生数据按 ODbL 处理并注明 © OpenStreetMap contributors。核对来源链、坐标系与边界适用性后再批准加入发布包 |
| 河流 | [Natural Earth terms](https://www.naturalearthdata.com/about/terms-of-use/) 声明地图数据 public domain | 当前在 prepared geometry/base blend 内；原始河流文件不在 V3.2 目录，不伪称随仓库提供 |
| earth.jpg | 原下载 URL/hash 在 download-manifest；[NASA media guidelines](https://www.nasa.gov/nasa-brand-center/images-and-media/) 有一般使用规则及第三方例外 | 已核验本地 hash；尚未完整核对该张图的具体署名链，发布前补核，默认不提交 |
| 南京照片 | [原文件页](https://commons.wikimedia.org/wiki/File:Skyline_in_Nanjing_(20250325).jpg) 显示 Fumikas Sagisavas、CC0 1.0，2025-03-25 | 页面与本地 hash 一致；保留作者/年份/来源，原 JPEG 未改，面板 UV 裁切。可从 culture-sources.json 所列 URL 手动准备 |
| Noto Sans CJK woff2 | 本地 OFL.txt 与 [Noto 官方说明](https://github.com/notofonts/noto-docs/blob/main/docs/website/use.md) | 字体家族使用 OFL；本地特定 WOFF2 缺少精确下载/转换来源，保留许可证并补来源，默认不提交 |
| inputs/nanjing-base.blend | 本地 hash 与 base-manifest 一致；本次 Blender 读取确认地球贴图 packed，无外部链接库 | 南京专用烘焙工程。授权者须提供本文件；原始创建脚本不在本版目录，纯源码 checkout 不能从零再建基础地球。公开前检查内嵌文字、资源和路径 |
| 统计网页摘录 | snapshot sources 中 URL/hash | 再分发权未确认，默认不提交；本机可核验，公开版仅附数字引用与获取说明 |

许可网页检查日期 2026-10-26。网页许可不替代对本地二进制身份的核验；未将“NASA”或“公开下载”泛化为整个包可以公开。

复现需要按 config/nanjing.json 的 paths 准备所有输入，并运行 prepare_project。输入缺失会明确报错，不会寻找相邻旧项目。当前本机准备后地理数据从原 build/prepared-geo.json 复制到 data/geo/nanjing-prepared.json，几何数组未变，另加 project 元数据绑定 ENU 原点、公里单位、边界年和两个 GeoJSON hash；原文件保留。地理中心 center 是市域质心，与 ENU 原点是不同概念；镜头从基础工程读出至 data/camera/nanjing.json。

已新增 prepare_city_geo.py 与 build_city_base.py，按同一 ENU 原点、公里单位及对象命名契约生成新城市网格和基础工程。紧凑城市、坐标系、合法素材及输入要求见 city-migration.md。原南京仍使用原工程以保持画面。

原始二进制补充检查：本次读取基础工程及三个旧交付 .blend，未发现外链库或文本块凭据模式命中，但发现原工程存在绝对字体/图片路径。原文件未改，全部默认忽略；若以后发布 Blender 源工程，需另存分发副本，清理路径并复核所有内嵌资源、元数据和署名。
