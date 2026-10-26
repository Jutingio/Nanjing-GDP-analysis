# 换城市操作

现在可以由提供的城市数据生成新基础工程，不需要手工复制南京.blend。原南京配置继续使用原基础工程，以保留已完成的动画。

## 先运行不含第三方资产的演示

安装 Blender 5.2 LTS 和外部 Python 3.12/3.13，在干净源码目录运行：

```sh
python -m pip install -r requirements-geo.txt
python scripts/create_demo_city.py
python scripts/prepare_city_geo.py --config config/demo.local.json
blender --background --factory-startup --disable-autoexec --python-exit-code 1 --python scripts/build_city_base.py -- --config config/demo.local.json
blender --background --disable-autoexec data/generated-demo/base.blend --python-exit-code 1 --python scripts/build_v3.py -- --config config/demo.local.json
blender --background --disable-autoexec output/demo/build/nanjing-v3.blend --python-exit-code 1 --python scripts/validate_v3.py -- --config config/demo.local.json
blender --background --disable-autoexec output/demo/build/nanjing-v3.blend --python-exit-code 1 --python scripts/render_v3.py -- --config config/demo.local.json --frames 91,751 --scale 25 --samples 4
```

演示图形、数字和照片均由程序生成，不代表任何真实城市；英文演示使用 Blender 内置字体，不下载南京照片/地图/字体。重复运行输入生成器会拒绝覆盖，可以指定新的 `--id demo-two --origin 103.17,24.05`；相应配置变为 config/demo-two.local.json，输出目录为 output/demo-two。生成输入和 .local 配置均不提交。

## 换成真实城市

1. 复制 config/example.json 为新配置，例如 config/mycity.local.json；填写 city.id/name/kicker/period、geometry.originLonLat（WGS84经纬度）、boundaryYear 和真实署名。每个城市使用独立 paths 和 output；初始 template=true，baseSha256 保留64个0。
2. 准备 snapshot.json：同年全市分母、各区值、三个展示区代码、原始来源文件及 SHA-256。结构参见 data/schemas/snapshot.schema.json。示例合成数字不能改个地名当作真实统计；不同统计口径要先整理，不能重叠映射行政区。
3. 准备 districts.geojson：WGS84 EPSG:4326，FeatureCollection，每个 Feature 包含 properties.regionCode 和 properties.name，geometry 为有效 Polygon/MultiPolygon。支持孔洞和多面；PolygonZ 中高度明确忽略。禁止将 GCJ-02/BD-09 当成 WGS84，禁止重叠行政区。
4. 准备 culture.json：history 为 year/text 数组，sights 为 name/text 数组，photo 至少包含 file、caption、capturedOn、sha256。图片、字体和地球贴图必须有可使用依据，并配置相应路径。中文使用合法 CJK 字体；只有合成英文演示使用内置字体。截图照片与统计年度可不同，但须标明。
5. 用该配置依次运行 prepare_city_geo.py → build_city_base.py → prepare_project.py → build_v3.py → validate_v3.py → render_v3.py。把上面演示命令里的路径换成自己的路径即可。build_city_base 会生成相机轨迹、基础工程，并将真实 baseSha256 与 template=false 写回该配置。

culture 最小结构（数据仅示意，图片 hash 用真实值）：

```json
{"history":[{"year":"年份","text":"有来源的简介"}],"sights":[{"name":"景点","text":"有来源的描述"}],"photo":{"file":"data/cities/example/photo.jpg","caption":"资料图片，注明年份","capturedOn":"2024-01-01","sha256":"填写真实SHA256"}}
```

城市预处理将经纬度投影到局部等距方位坐标，约束三角剖分并将长边细分到5公里以内，再放置到WGS84椭球上，避免粗三角面被地球遮挡。边界长线也细分。原始GeoJSON不改写；准备后的文件绑定原点/单位/年份和输入hash。

## 适用范围与限制

当前适用于紧凑城市：原点和几何纬度在±75°内，整体经纬跨度不超过8°，不跨180°经线；仍为三地区、60秒、30fps、原1920×1080版式。不是全球任意形状的 GIS 引擎。水系目前可为空，通用适配器不会自动获取当地河流。长城市名和区名需要抽帧检查排版，必要时在脚本中调整文本尺寸。

通用适配器沿用原影片构图和时间节奏，为新城市重新生成基础地球与镜头；新城市的贴图效果会受所供资源影响。原南京场景不重建。历史输出仍使用 nanjing-v3.blend 兼容文件名，由独立 output/<city-id>/ 隔离，不代表展示内容仍为南京。

本轮实际验证了两组不同坐标的合成城市构建与抽帧。尚未验证第二座真实城市的全部数据/地图与完整60秒成片，不能代替当地来源、口径和空间位置审阅。
