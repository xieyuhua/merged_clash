# Clash 订阅合并工具

自动获取多个订阅源、测速、合并生成可用的 Clash 配置文件。

## 功能特性

- **多源订阅支持**：支持在线订阅、GitHub Raw、本地文件/文件夹
- **协议解析**：自动解析 vmess、ss、trojan、vless、hysteria2 等协议
- **智能测速**：并发测试节点可用性，支持连接测试和代理测速
- **自动去重**：根据服务器地址和端口自动去重
- **规则生成**：自动生成代理组和分流规则

## 安装依赖

```bash
pip install -r requirements.txt
```

## 快速开始

1. 编辑 `sources.txt`，添加你的订阅源
2. 运行脚本：

```bash
python clash_tools.py
```

3. 生成的文件：
   - `merged_clash.yaml` - Clash 配置文件
   - `merged_clash_nodes.txt` - 节点列表

## 订阅源格式

`sources.txt` 每行一个，支持以下格式：

| 类型 | 示例 | 说明 |
|------|------|------|
| 在线订阅 | `https://example.com/sub` | 标准机场订阅链接 |
| GitHub Raw | `https://raw.githubusercontent.com/...` | GitHub 上的配置文件 |
| 本地 YAML 文件 | `tested_within.yaml` | 单个配置文件 |
| 本地文件夹 | `./configs` | 递归扫描所有 .yaml/.yml 文件 |
| 单个节点链接 | `vmess://xxxxx` | 直接粘贴节点链接 |
| 绝对路径 | `D:/clash/config.yaml` | Windows 绝对路径 |
| 相对路径 | `./my_configs` | 相对于脚本目录 |

### 支持的协议

- **vmess** - V2Ray/Xray 协议
- **ss** - Shadowsocks 协议（支持插件）
- **trojan** - Trojan 协议
- **vless** - VLESS 协议
- **hysteria2** - Hysteria2 协议

### sources.txt 示例

```txt
# 在线订阅
https://your-airport.com/api/v1/client/subscribe?token=xxx

# GitHub 订阅
https://raw.githubusercontent.com/ACL4SSR/ACL4SSR/master/Clash/config/ACL4SSR.ini

# 本地文件夹（会递归扫描）
subscriptions

# 本地单个文件
tested_within.yaml

# 单个节点
vmess://xxxxx
```

## 命令行参数

```bash
python clash_tools.py [选项]

选项:
  -h, --help            显示帮助信息
  -f, --file           订阅源列表文件 (默认: sources.txt)
  -s, --sources        命令行指定订阅源 (多个用空格分隔)
  -o, --output         输出文件路径 (默认: merged_clash.yaml)
  -t, --test-method    测速方式: connect(连接测试) 或 speed(代理测速)
  -n, --name           配置名称 (默认: 合并节点)
```

### 使用示例

```bash
# 使用默认 sources.txt
python clash_tools.py

# 指定订阅源文件
python clash_tools.py -f my_sources.txt

# 命令行直接指定订阅源
python clash_tools.py -s https://example.com/sub1 https://example.com/sub2

# 指定输出文件
python clash_tools.py -o my_config.yaml

# 使用代理测速（需要本地 Clash 运行在 7890 端口）
python clash_tools.py -t speed

# 自定义配置名称
python clash_tools.py -n "我的节点"
```

## 输出文件

运行后会生成以下文件：

```
d:/anmo/clash/
├── merged_clash.yaml       # Clash 配置文件（可直接导入）
├── merged_clash_nodes.txt   # 节点列表（方便查看）
├── sources.txt             # 订阅源列表（编辑此文件）
└── clash_tools.py          # 主脚本
```

## 配置说明

生成 `merged_clash.yaml` 包含以下内容：

### 代理组

| 名称 | 类型 | 说明 |
|------|------|------|
| 合并节点 | url-test | 自动选择最快节点 |
| 自动选择 | url-test | 自动选择最快节点 |
| 故障转移 | fallback | 节点故障时切换 |
| 负载均衡 | load-balance | 均衡分配流量 |
| 🇭🇰 香港节点 | url-test | 仅香港节点 |
| 🇺🇸 美国节点 | url-test | 仅美国节点 |
| 🇯🇵 日本节点 | url-test | 仅日本节点 |
| 🇸🇬 新加坡节点 | url-test | 仅新加坡节点 |
| 🐟 漏网之鱼 | select | 手动选择 |

### 分流规则

- 中国大陆流量直连
- 其他流量走代理

## 注意事项

1. **测速说明**：
   - `connect` 模式：仅测试 TCP 连接，速度较快
   - `speed` 模式：通过本地代理测速，需要 Clash 运行在 7890 端口

2. **节点数量**：节点越多测试时间越长，可适当减少订阅源

3. **隐私提示**：不要分享你的 `sources.txt` 文件，其中可能包含个人信息

## 常见问题

### Q: 测速太慢怎么办？

减少 `sources.txt` 中的订阅源数量，或使用 `connect` 测速模式。

### Q: 提示 "无法识别的源格式"？

检查订阅链接是否正确，确保以 `http://`、`https://` 开头或使用有效的本地路径。

### Q: 生成的配置文件无法使用？

可能是节点协议不被你的 Clash 版本支持，请更新 Clash 或使用支持的协议。

## License

MIT
