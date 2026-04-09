# FeatureScript 使用教程

这份文档是 `fs-builder` 项目内的长期参考资料。

目标不是把 Onshape FeatureScript 所有内容都讲完，而是固定一套适合本项目的写法，让后续模板开发、排错和扩展都能有统一标准。

## 1. FeatureScript 文件结构

一个最基础的自定义特征通常长这样：

```featurescript
FeatureScript 2399;
import(path : "onshape/std/geometry.fs", version : "2399.0");

annotation { "Feature Type Name" : "Demo Feature" }
export const demoFeature = defineFeature(function(context is Context, id is Id, definition is map)
precondition
{
}
{
    // 在这里写建模逻辑
});
```

项目里的最终 `.fs` 文件由 `merger.py` 统一包壳，所以模板生成器只需要输出特征函数内部的语句，不要重复写文件头、`import` 或 `defineFeature(...)`。

## 2. 基础语法

- 语句以分号结尾。
- 变量声明常用 `var` 和 `const`。
- 映射写法像 JSON，但 key 和 value 之间用 `:`
- 字符串拼接用 `~`
- 常见流程控制有 `if`、`for`、`while`
- 类型约束经常出现在函数签名里，比如 `context is Context`

常见例子：

```featurescript
var radius = 25 * millimeter;
var origin = vector(0, 0, 0) * millimeter;
var sketchPlane = plane(origin, Z_DIRECTION);
```

## 3. 单位与 ValueWithUnits

FeatureScript 的单位不是普通数字字符串，而是带单位的值。

- `10 * millimeter`
- `0.5 * inch`
- `vector(0, 0, 10) * millimeter`

本项目固定约定：

- plan 里的尺寸全部存储为“毫米数值”
- 在模板里真正使用时，统一乘 `millimeter`
- 不在模板内部偷偷换算成米
- 代码里看到的长度变量，尽量都已经是 `ValueWithUnits`

推荐写法：

```featurescript
var width = 120 * millimeter;
var center = vector(0, 0) * millimeter;
```

## 4. defineFeature 结构

FeatureScript 自定义特征的主入口是：

```featurescript
defineFeature(function(context is Context, id is Id, definition is map)
precondition
{
}
{
    // body
});
```

几个关键对象：

- `context`：当前建模上下文，几何操作都作用在这里
- `id`：当前特征 ID，用来拼出稳定的操作 ID
- `definition`：用户输入参数；本项目模板阶段暂时不直接暴露参数 UI，所以合并后的总特征里 precondition 为空

## 5. Context、Query、ev*、op*

这是 FeatureScript 最核心的一组概念。

- `Context`
  - 建模发生的现场环境
- `Query`
  - 用来选几何对象，不直接拿到实体本身，而是先表达“我要选谁”
- `ev*`
  - evaluate 系列函数，用来从 Query 中取出几何信息
- `op*`
  - 真正执行建模操作的底层函数，比如拉伸、布尔、倒角

项目第一版模板主要使用：

- `qSketchRegion(...)`
- `qCreatedBy(...)`
- `qContainsPoint(...)`
- `qUnion([...])`
- `opExtrude(...)`
- `opLoft(...)`
- `opBoolean(...)`
- `opDeleteBodies(...)`

## 6. 草图建模主流程

本项目统一采用这条路线：

`newSketchOnPlane -> sk* -> skSolve -> op*`

理由很简单：

- 写法直观，适合毕设展示
- 和官方教程思路一致
- 对简单几何稳定
- 后面扩展孔、台阶、法兰时比较容易复用

标准流程如下：

```featurescript
var sketchPlane = plane(vector(0, 0, 0) * millimeter, Z_DIRECTION);
var sketch = newSketchOnPlane(context, id + "base_sketch", {
    "sketchPlane" : sketchPlane
});

skRectangle(sketch, "profile", {
    "firstCorner" : vector(-20, -10) * millimeter,
    "secondCorner" : vector(20, 10) * millimeter
});

skSolve(sketch);

opExtrude(context, id + "base_extrude", {
    "entities" : qSketchRegion(id + "base_sketch"),
    "direction" : Z_DIRECTION,
    "endBound" : BoundingType.BLIND,
    "endDepth" : 30 * millimeter
});
```

## 7. 常用草图 API

当前模板阶段最常用的是：

- `skRectangle(...)`
- `skCircle(...)`

矩形常见写法：

```featurescript
skRectangle(sketch, "profile", {
    "firstCorner" : vector(-50, -30) * millimeter,
    "secondCorner" : vector(50, 30) * millimeter
});
```

圆常见写法：

```featurescript
skCircle(sketch, "profile", {
    "center" : vector(0, 0) * millimeter,
    "radius" : 15 * millimeter
});
```

注意：

- 草图元素画完后一定要 `skSolve(sketch);`
- 如果草图里有多个闭合区域，不要默认 `qSketchRegion(...)` 只会返回你想要的那个区域
- 环形区域这类情况，要配合 `qContainsPoint(...)` 精确选区

## 8. 拉伸与布尔操作

### 拉伸

简单实体多数直接用 `opExtrude(...)`：

```featurescript
opExtrude(context, id + "boss_extrude", {
    "entities" : qSketchRegion(id + "boss_sketch"),
    "direction" : Z_DIRECTION,
    "endBound" : BoundingType.BLIND,
    "endDepth" : 60 * millimeter
});
```

### 布尔并体

多个实体要合成一个零件时，用 `opBoolean(...)`：

```featurescript
opBoolean(context, id + "union", {
    "tools" : qUnion([
        qCreatedBy(id + "body_a_extrude", EntityType.BODY),
        qCreatedBy(id + "body_b_extrude", EntityType.BODY)
    ]),
    "operationType" : BooleanOperationType.UNION
});
```

### 清理草图体

模板完成后，建议删掉草图创建出来的中间几何：

```featurescript
opDeleteBodies(context, id + "delete_sketch", {
    "entities" : qCreatedBy(id + "base_sketch", EntityType.BODY)
});
```

## 9. 本项目模板写法规范

后续所有模板都按下面这些规则统一：

- 只输出 FeatureScript 语句，不输出完整文件壳
- 所有操作 ID 必须以 `id + "<part_id>_"` 形式稳定生成
- plan 中的尺寸参数统一是毫米数值，模板使用时统一乘 `millimeter`
- 零件的 `position.x_mm / y_mm / z_bottom_mm` 统一解释为“零件底部基准中心”
- 优先使用草图 + 拉伸，避免自由发挥式建模
- 多实体并成一个零件时，显式做 `opBoolean(... UNION ...)`
- 草图阶段如果存在多个闭合区域，必须显式选区，不靠猜
- 缺少必填参数、尺寸非法、shape 不支持时直接 fail-fast

## 10. 当前 5 个 shape 的模板映射

### `box`

- 在 `z_bottom_mm` 平面建矩形草图
- 以 `x_mm / y_mm` 为底面中心
- 用 `width_mm / depth_mm / height_mm`
- 单次 `opExtrude`

### `cylinder`

- 在底面平面建圆
- 直径来自 `diameter_mm`
- 单次 `opExtrude`

### `hollow_cylinder`

- 同一草图画外圆和内圆
- 用 `qContainsPoint(...)` 选中环形区域
- 单次 `opExtrude`

### `tapered_cylinder`

- 在底面和顶面分别建两个圆截面
- 半径分别来自 `bottom_diameter_mm / top_diameter_mm`
- 使用 `opLoft(...)` 连接成锥台

### `flange`

- 底部法兰盘：一个圆草图 + 拉伸
- 上部轴段：在法兰顶面再建一个圆草图 + 拉伸
- 最后 `opBoolean(... UNION ...)` 合成一个零件

## 11. 常见坑

- 不要把毫米值先转成米再传给 FeatureScript，这会让模板和 plan 的语义变乱
- 不要忘记 `skSolve`
- 不要对多区域草图直接裸用 `qSketchRegion(...)`
- 不要让不同零件复用同一个操作 ID 后缀
- 不要在模板里偷偷补参数或猜参数含义
- `flange` 和 `tapered_cylinder` 这类零件，如果 schema 不够表达，就应该在校验阶段报错

## 12. 给后续模板开发的建议

- 先把每个 shape 的“最小稳定版”做对，再考虑孔、倒角、圆角
- 每加一种新 shape，先更新这份文档，再写模板代码
- 新模板优先复用现有的平面生成、单位转换、ID 命名方式
- 如果某个 FeatureScript API 不确定，优先查 Onshape 官方 FsDoc，不要靠猜

## 13. 官方资料

- Introduction: `https://cad.onshape.com/FsDoc/intro.html`
- Syntax: `https://cad.onshape.com/FsDoc/syntax.html`
- Feature types: `https://cad.onshape.com/FsDoc/feature-types.html`
- Modeling: `https://cad.onshape.com/FsDoc/modeling.html`
- Standard library: `https://cad.onshape.com/FsDoc/library.html`
- Sketch tutorial: `https://cad.onshape.com/FsDoc/tutorials/add-sketch-geometry.html`
