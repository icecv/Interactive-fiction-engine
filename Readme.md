交互式小说游戏引擎
一个基于脚本驱动的交互式小说游戏引擎，采用自定义DSL语言编写故事内容，支持多媒体展示和复杂的分支剧情。

项目概述
这是一个完整的交互式小说游戏引擎，包含以下核心组件：

Python后端引擎 - 处理游戏逻辑、脚本解析和状态管理
Godot前端界面 - 提供用户交互界面和多媒体展示
WebSocket通信 - 连接前后端的实时通信协议
自定义DSL语言 - 简洁的脚本语言用于编写游戏内容

环境要求

Python 3.8+
Godot 4.x
Windows/Linux/macOS

使用方式

GameEngine即为整个游戏引擎（暂无使用UI界面）
按照脚本语法编写. txt脚本（文件夹内包含示例脚本），然后新建一个文件夹用于将媒体资源放入，运行 FictionGame.exe 即可游玩你自己的游戏

文件介绍

Python Engine Code内包含整个后端游戏逻辑支持代码
前端依赖Godot引擎实现，已提供用于链接后端的相应.gd脚本和项目UI节点剧本.tscn文件

# 脚本语言语法指南

## 基础语法规则

- 每条命令以 `;` 结尾
- 字符串用双引号 `"text"`
- 变量用花括号 `{variable}`
- 参数用连字符 `-key=value`
- 注释用井号 `# comment`

## 基础命令

### 对话
```
say:"Hello, world!";
say:"Welcome!" -speaker="角色名";
say:"你有 {health} 点生命值。" -speaker="System";
```

### 变量操作
```
setVar:health=100;
setVar:playerName="玩家";
setVar:score={health + 10};
```

### 用户输入
```
input:playerName;
input:age -prompt="请输入年龄：";
```

### 选择分支
```
choose:
    "向北走":northPath |
    "向南走":southPath -when={hasKey} |
    "休息":rest -when={health < 100}
;
```

### 标签和跳转
```
label:start;
jump:start;
```

### 场景管理
```
changeScene:forest;       # 切换场景
callScene:inventory;      # 调用场景
return;                   # 返回
```

### 骰子系统
```
roll:1d20;
roll:1d6+{strength} -to=attackRoll;
roll:1d20+5 -to=monster_attack;
```

## 多媒体命令

### 图片
```
showImage:"backgrounds/forest.jpg";
hideImage;
```

### 音频
```
playBGM:"music/theme.mp3" -loop=true;
playSFX:"sounds/door.wav";
playVoice:"voice/line1.ogg";
stopBGM;
stopVoice;
```

## 条件表达式

```
{health + 10}                    # 数学运算
{level >= 5}                     # 比较运算
{hasKey and level > 3}           # 逻辑运算
{player_dice == house_dice}      # 等值比较
{gold >= 10}                     # 大于等于
{playerName}                     # 变量引用
```

## 完整示例

```
showImage:"tavern.jpg";
playBGM:"main_theme.mp3" -loop=true;

setVar:health=100;
setVar:gold=50;

input:player_name -prompt="Enter your name: ";
say:"Hello, {player_name}!" -speaker="NPC";

label:main_menu;
say:"You have {gold} gold." -speaker="System";

choose:
    "Enter shop":shop -when={gold >= 10} |
    "Battle":battle |
    "Rest":rest -when={health < 100}
;

label:battle;
roll:1d20+{strength} -to=attack;
say:"Your attack: {attack}" -speaker="System";

choose:
    "Victory!":win -when={attack >= 15} |
    "Defeat...":lose -when={attack < 15}
;

label:win;
setVar:gold={gold + 20};
say:"You won 20 gold!" -speaker="System";
jump:main_menu;

label:lose;
setVar:health={health - 10};
say:"You lost 10 health!" -speaker="System";
jump:main_menu;
```

## 语法要点

1. **冒号语法**：所有命令都用 `命令:参数` 格式
2. **分号结尾**：每条语句必须以 `;` 结尾
3. **参数格式**：用 `-参数名=值` 格式
4. **选择语法**：选项用 `|` 分隔，条件用 `-when={}` 和 `-enable={}`
5. **变量插值**：在字符串中用 `{变量名}` 引用变量
