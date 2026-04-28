#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Clash 订阅获取、测速与合并脚本
功能：
1. 解析多个 GitHub Clash 仓库地址或订阅链接
2. 测速所有节点
3. 合并可用节点生成新的 clash.yaml
"""

import requests
import base64
import yaml
import json
import re
import time
import concurrent.futures
import argparse
import os
from urllib.parse import urlparse
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
import sys

# 配置区域
DEFAULT_TIMEOUT = 10  # 请求超时时间（秒）
SPEED_TEST_URL = "https://www.google.com/generate_204"  # 测速目标URL
SPEED_TEST_TIMEOUT = 5  # 单次测速超时（秒）
MAX_WORKERS = 20  # 并发测速线程数

@dataclass
class ProxyNode:
    """代理节点"""
    name: str
    type: str
    server: str
    port: int
    cipher: Optional[str] = None
    password: Optional[str] = None
    uuid: Optional[str] = None
    alterId: Optional[int] = None
    network: Optional[str] = None
    ws_path: Optional[str] = None
    ws_headers: Optional[Dict] = None
    tls: Optional[str] = None
    skip_cert_verify: Optional[bool] = None
    reality_public_key: Optional[str] = None
    reality_short_id: Optional[str] = None
    sni: Optional[str] = None
    plugin: Optional[str] = None
    plugin_opts: Optional[Dict] = None
    raw_config: Optional[Dict] = None
    speed: Optional[float] = None  # 速度测试结果（秒）

    @classmethod
    def from_dict(cls, data: Dict, raw: bool = False):
        """从字典创建节点"""
        if raw:
            return cls(
                name=data.get('name', 'Unknown'),
                type=data.get('type', 'unknown'),
                server=data.get('server', ''),
                port=data.get('port', 0),
                raw_config=data
            )
        
        node_type = data.get('type', '').lower()
        
        if node_type == 'vmess':
            return cls(
                name=data.get('name', 'Unknown'),
                type='vmess',
                server=data.get('server', ''),
                port=data.get('port', 0),
                uuid=data.get('uuid', ''),
                alterId=data.get('alterId', 0),
                cipher=data.get('cipher', 'auto'),
                network=data.get('network', 'tcp'),
                ws_path=data.get('ws-path', ''),
                ws_headers=data.get('ws-headers', None),
                tls=data.get('tls', ''),
                skip_cert_verify=data.get('skip-cert-verify', False),
                raw_config=data
            )
        elif node_type == 'ss':
            return cls(
                name=data.get('name', 'Unknown'),
                type='ss',
                server=data.get('server', ''),
                port=data.get('port', 0),
                cipher=data.get('cipher', ''),
                password=data.get('password', ''),
                plugin=data.get('plugin', ''),
                plugin_opts=data.get('plugin-opts', {}),
                raw_config=data
            )
        elif node_type == 'trojan':
            return cls(
                name=data.get('name', 'Unknown'),
                type='trojan',
                server=data.get('server', ''),
                port=data.get('port', 0),
                password=data.get('password', ''),
                sni=data.get('sni', ''),
                skip_cert_verify=data.get('skip-cert-verify', False),
                raw_config=data
            )
        elif node_type == 'vless':
            return cls(
                name=data.get('name', 'Unknown'),
                type='vless',
                server=data.get('server', ''),
                port=data.get('port', 0),
                uuid=data.get('uuid', ''),
                network=data.get('network', 'tcp'),
                ws_path=data.get('ws-path', ''),
                tls=data.get('tls', ''),
                sni=data.get('sni', ''),
                skip_cert_verify=data.get('skip-cert-verify', False),
                raw_config=data
            )
        elif node_type == 'hysteria2' or node_type == 'hy2':
            return cls(
                name=data.get('name', 'Unknown'),
                type='hysteria2',
                server=data.get('server', ''),
                port=data.get('port', 0),
                password=data.get('password', ''),
                sni=data.get('sni', ''),
                skip_cert_verify=data.get('skip-cert-verify', False),
                reality_short_id=data.get('short-id', ''),
                raw_config=data
            )
        else:
            return cls(
                name=data.get('name', 'Unknown'),
                type=node_type,
                server=data.get('server', ''),
                port=data.get('port', 0),
                raw_config=data
            )

    def to_dict(self) -> Dict:
        """转换为字典"""
        if self.raw_config:
            return self.raw_config
        
        result = {
            'name': self.name,
            'type': self.type,
            'server': self.server,
            'port': self.port
        }
        
        if self.type == 'vmess':
            result.update({
                'uuid': self.uuid,
                'alterId': self.alterId,
                'cipher': self.cipher,
                'network': self.network,
            })
            if self.ws_path:
                result['ws-path'] = self.ws_path
            if self.ws_headers:
                result['ws-headers'] = self.ws_headers
            if self.tls:
                result['tls'] = self.tls
            if self.skip_cert_verify is not None:
                result['skip-cert-verify'] = self.skip_cert_verify
        elif self.type == 'ss':
            result.update({
                'cipher': self.cipher,
                'password': self.password,
            })
            if self.plugin:
                result['plugin'] = self.plugin
                if self.plugin_opts:
                    result['plugin-opts'] = self.plugin_opts
        elif self.type == 'trojan':
            result['password'] = self.password
            if self.sni:
                result['sni'] = self.sni
            if self.skip_cert_verify is not None:
                result['skip-cert-verify'] = self.skip_cert_verify
        elif self.type == 'vless':
            result['uuid'] = self.uuid
            if self.network:
                result['network'] = self.network
            if self.ws_path:
                result['ws-path'] = self.ws_path
            if self.tls:
                result['tls'] = self.tls
            if self.sni:
                result['sni'] = self.sni
            if self.skip_cert_verify is not None:
                result['skip-cert-verify'] = self.skip_cert_verify
        elif self.type == 'hysteria2':
            result['password'] = self.password
            if self.sni:
                result['sni'] = self.sni
            if self.skip_cert_verify is not None:
                result['skip-cert-verify'] = self.skip_cert_verify
            # short-id 必须是 8 个十六进制字符或为空
            if self.reality_short_id:
                import re
                if re.match(r'^[0-9a-fA-F]{1,8}$', self.reality_short_id):
                    result['short-id'] = self.reality_short_id.lower()
                else:
                    # 无效的 short-id，清除它
                    pass
        
        return result

    def __hash__(self):
        """用于去重"""
        return hash((self.type, self.server, self.port))


def parse_vmess_link(vmess_str: str) -> Optional[Dict]:
    """解析 vmess 链接"""
    try:
        if not vmess_str.startswith('vmess://'):
            return None
        
        # 移除 vmess:// 前缀并解码
        vmess_base64 = vmess_str[8:]
        # 添加 padding 如果需要
        padding = 4 - len(vmess_base64) % 4
        if padding != 4:
            vmess_base64 += '=' * padding
        
        decoded = base64.b64decode(vmess_base64).decode('utf-8')
        data = json.loads(decoded)
        
        # 转换为标准格式
        return {
            'name': data.get('ps', 'Unknown'),
            'type': 'vmess',
            'server': data.get('add', data.get('address', '')),
            'port': int(data.get('port', 0)),
            'uuid': data.get('id', ''),
            'alterId': int(data.get('aid', 0)),
            'cipher': data.get('scy', 'auto'),
            'network': data.get('net', 'tcp'),
            'ws-path': data.get('path', ''),
            'ws-headers': {'Host': data.get('host', '')} if data.get('host') else None,
            'tls': 'tls' if data.get('tls') == 'tls' else '',
            'skip-cert-verify': data.get('verify', True),
        }
    except Exception as e:
        print(f"解析 vmess 链接失败: {e}")
        return None


def parse_shadowsocks_link(ss_str: str) -> Optional[Dict]:
    """解析 ss 链接"""
    try:
        if not ss_str.startswith('ss://'):
            return None
        
        # 移除 ss:// 前缀
        ss_part = ss_str[5:]
        
        # 分离 userinfo 和剩余部分
        if '#' in ss_part:
            ss_part, name = ss_part.split('#', 1)
            name = base64.b64decode(name.replace('-', '+').replace('_', '/') + '==').decode('utf-8')
        else:
            name = 'Unknown'
        
        if '@' in ss_part:
            userinfo, server_part = ss_part.split('@')
            
            # 解码 userinfo
            userinfo = base64.b64decode(userinfo + '==').decode('utf-8')
            cipher, password = userinfo.split(':', 1)
            
            # 解析服务器信息
            server_part = base64.b64decode(server_part + '==').decode('utf-8')
            if ':' in server_part:
                server, port = server_part.rsplit(':', 1)
            else:
                return None
            
            return {
                'name': name,
                'type': 'ss',
                'server': server,
                'port': int(port),
                'cipher': cipher,
                'password': password,
            }
        else:
            return None
    except Exception as e:
        print(f"解析 ss 链接失败: {e}")
        return None


def parse_trojan_link(trojan_str: str) -> Optional[Dict]:
    """解析 trojan 链接"""
    try:
        if not trojan_str.startswith('trojan://'):
            return None
        
        # 移除 trojan:// 前缀
        trojan_part = trojan_str[9:]
        
        # 分离密码和服务器信息
        if '@' in trojan_part:
            password, server_part = trojan_part.split('@', 1)
            
            # 分离服务器和参数
            if '#' in server_part:
                server_part, name = server_part.split('#', 1)
                name = base64.b64decode(name.replace('-', '+').replace('_', '/') + '==').decode('utf-8')
            else:
                name = 'Unknown'
            
            # 解析服务器信息
            if '?' in server_part:
                server_port, params = server_part.split('?', 1)
            else:
                server_port = server_part
                params = ''
            
            if ':' in server_port:
                server, port = server_port.rsplit(':', 1)
            else:
                return None
            
            # 解析参数
            sni = ''
            skip_cert_verify = False
            for param in params.split('&'):
                if '=' in param:
                    key, value = param.split('=', 1)
                    if key == 'sni':
                        sni = value
                    elif key == 'allowInsecure':
                        skip_cert_verify = value == '1' or value.lower() == 'true'
            
            return {
                'name': name,
                'type': 'trojan',
                'server': server,
                'port': int(port),
                'password': password,
                'sni': sni,
                'skip-cert-verify': skip_cert_verify,
            }
        return None
    except Exception as e:
        print(f"解析 trojan 链接失败: {e}")
        return None


def parse_vless_link(vless_str: str) -> Optional[Dict]:
    """解析 vless 链接"""
    try:
        if not vless_str.startswith('vless://'):
            return None
        
        # 移除 vless:// 前缀
        vless_part = vless_str[8:]
        
        # 分离 uuid 和服务器信息
        if '@' in vless_part:
            uuid, server_part = vless_part.split('@', 1)
            
            # 分离服务器和参数
            if '#' in server_part:
                server_port, name_b64 = server_part.split('#', 1)
                name = base64.b64decode(name_b64.replace('-', '+').replace('_', '/') + '==').decode('utf-8')
            else:
                server_port = server_part
                name = 'Unknown'
            
            # 解析服务器信息
            if '?' in server_port:
                server_port, params = server_port.split('?', 1)
            else:
                params = ''
            
            if ':' in server_port:
                server, port = server_port.rsplit(':', 1)
            else:
                return None
            
            # 解析参数
            network = 'tcp'
            ws_path = ''
            tls = ''
            sni = ''
            skip_cert_verify = False
            
            for param in params.split('&'):
                if '=' in param:
                    key, value = param.split('=', 1)
                    if key == 'type':
                        network = value
                    elif key == 'path':
                        ws_path = value
                    elif key == 'security':
                        tls = value
                    elif key == 'sni':
                        sni = value
                    elif key == 'allowInsecure':
                        skip_cert_verify = value == '1' or value.lower() == 'true'
            
            return {
                'name': name,
                'type': 'vless',
                'server': server,
                'port': int(port),
                'uuid': uuid,
                'network': network,
                'ws-path': ws_path,
                'tls': tls,
                'sni': sni,
                'skip-cert-verify': skip_cert_verify,
            }
        return None
    except Exception as e:
        print(f"解析 vless 链接失败: {e}")
        return None


def parse_hysteria_link(hysteria_str: str) -> Optional[Dict]:
    """解析 hysteria 链接"""
    try:
        if not hysteria_str.startswith('hysteria://') and not hysteria_str.startswith('hy2://'):
            return None
        
        # 移除 hysteria:// 或 hy2:// 前缀
        hysteria_part = hysteria_str.replace('hysteria://', '').replace('hy2://', '')
        
        # 分离服务器信息和参数
        if '#' in hysteria_part:
            server_part, name = hysteria_part.split('#', 1)
            name = base64.b64decode(name.replace('-', '+').replace('_', '/') + '==').decode('utf-8')
        else:
            server_part = hysteria_part
            name = 'Hysteria'
        
        # 解析服务器信息
        if '@' in server_part:
            password, server_info = server_part.split('@', 1)
        else:
            password = ''
            server_info = server_part
        
        # 解析参数
        if '?' in server_info:
            server_port, params = server_info.split('?', 1)
        else:
            server_port = server_info
            params = ''
        
        if ':' in server_port:
            server, port = server_port.rsplit(':', 1)
        else:
            server = server_port
            port = 443
        
        # 解析额外参数
        sni = ''
        skip_cert_verify = False
        
        for param in params.split('&'):
            if '=' in param:
                key, value = param.split('=', 1)
                if key == 'sni':
                    sni = value
                elif key == 'insecure':
                    skip_cert_verify = value == '1' or value.lower() == 'true'
        
        return {
            'name': name,
            'type': 'hysteria2',
            'server': server,
            'port': int(port),
            'password': password,
            'sni': sni,
            'skip-cert-verify': skip_cert_verify,
        }
    except Exception as e:
        print(f"解析 hysteria 链接失败: {e}")
        return None


def fetch_subscription(url: str) -> List[ProxyNode]:
    """获取订阅内容并解析节点"""
    nodes = []
    
    try:
        print(f"正在获取订阅: {url}")
        headers = {
            'User-Agent': 'ClashForAndroid/2.5.12'
        }
        response = requests.get(url, headers=headers, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        
        content = response.text.strip()
        
        # 判断是 base64 编码还是纯文本
        try:
            # 尝试 base64 解码
            padding = 4 - len(content) % 4
            if padding != 4:
                content += '=' * padding
            decoded = base64.b64decode(content).decode('utf-8')
            
            # 如果解码后是 YAML 格式，则尝试作为 YAML 解析
            if decoded.startswith('port:'):
                config = yaml.safe_load(decoded)
                if 'proxies' in config:
                    for proxy in config['proxies']:
                        nodes.append(ProxyNode.from_dict(proxy))
                    print(f"  解码 YAML，获取到 {len(config['proxies'])} 个节点")
                    return nodes
                elif 'servers' in config:
                    for proxy in config['servers']:
                        nodes.append(ProxyNode.from_dict(proxy))
                    print(f"  解码 YAML，获取到 {len(config['servers'])} 个节点")
                    return nodes
            
            # 如果解码后包含节点链接
            if 'vmess://' in decoded or 'ss://' in decoded or 'trojan://' in decoded or 'vless://' in decoded:
                content = decoded
        except:
            pass
        
        # 解析节点链接
        lines = content.split('\n')
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            node_data = None
            if line.startswith('vmess://'):
                node_data = parse_vmess_link(line)
            elif line.startswith('ss://'):
                node_data = parse_shadowsocks_link(line)
            elif line.startswith('trojan://'):
                node_data = parse_trojan_link(line)
            elif line.startswith('vless://'):
                node_data = parse_vless_link(line)
            elif line.startswith('hysteria://') or line.startswith('hy2://'):
                node_data = parse_hysteria_link(line)
            
            if node_data:
                nodes.append(ProxyNode.from_dict(node_data))
        
        print(f"  获取到 {len(nodes)} 个节点")
        
    except requests.exceptions.RequestException as e:
        print(f"  获取订阅失败: {e}")
    except Exception as e:
        print(f"  解析订阅失败: {e}")
    
    return nodes


def fetch_github_raw(raw_url: str) -> List[ProxyNode]:
    """从 GitHub Raw 获取配置文件"""
    return fetch_subscription(raw_url)


def fetch_local_yaml(filepath: str) -> List[ProxyNode]:
    """从本地 YAML 文件读取节点"""
    nodes = []
    
    try:
        print(f"正在读取本地 YAML 文件: {filepath}")
        
        if not os.path.exists(filepath):
            print(f"  文件不存在: {filepath}")
            return nodes
        
        with open(filepath, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        if not config:
            print(f"  文件为空或解析失败")
            return nodes
        
        # 尝试不同的 key 名称
        proxy_list = None
        if 'proxies' in config:
            proxy_list = config['proxies']
        elif 'servers' in config:
            proxy_list = config['servers']
        elif 'Proxy' in config:
            proxy_list = config['Proxy']
        elif 'proxy' in config:
            proxy_list = config['proxy']
        
        if proxy_list:
            for proxy in proxy_list:
                if isinstance(proxy, dict):
                    nodes.append(ProxyNode.from_dict(proxy))
            print(f"  从 YAML 获取到 {len(proxy_list)} 个节点")
        else:
            print(f"  未找到代理节点配置")
            
    except yaml.YAMLError as e:
        print(f"  YAML 解析失败: {e}")
    except Exception as e:
        print(f"  读取文件失败: {e}")
    
    return nodes


def scan_yaml_folder(folder_path: str) -> List[str]:
    """扫描文件夹中的所有 YAML 文件"""
    yaml_files = []
    
    try:
        if not os.path.exists(folder_path):
            print(f"  文件夹不存在: {folder_path}")
            return yaml_files
        
        if not os.path.isdir(folder_path):
            print(f"  不是文件夹: {folder_path}")
            return yaml_files
        
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                if file.endswith('.yaml') or file.endswith('.yml'):
                    full_path = os.path.join(root, file)
                    yaml_files.append(full_path)
        
        print(f"  在文件夹中找到 {len(yaml_files)} 个 YAML 文件")
        
    except Exception as e:
        print(f"  扫描文件夹失败: {e}")
    
    return yaml_files


def parse_source(source: str) -> List[ProxyNode]:
    """解析订阅源，支持 URL、本地 YAML 文件/文件夹、单个节点链接"""
    nodes = []
    
    # 检查是否是 URL
    if source.startswith('http://') or source.startswith('https://'):
        nodes = fetch_subscription(source)
        return nodes
    
    # 检查是否是本地文件/文件夹
    if os.path.exists(source):
        # 如果是文件夹，扫描其中的 YAML 文件
        if os.path.isdir(source):
            yaml_files = scan_yaml_folder(source)
            for yaml_file in yaml_files:
                file_nodes = fetch_local_yaml(yaml_file)
                nodes.extend(file_nodes)
            return nodes
        
        # 如果是 YAML 文件
        if source.endswith('.yaml') or source.endswith('.yml'):
            nodes = fetch_local_yaml(source)
            return nodes
        
        # 如果是文本文件，读取每行作为源
        if source.endswith('.txt'):
            try:
                with open(source, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            nodes.extend(parse_source(line))
            except Exception as e:
                print(f"  读取文件失败: {e}")
            return nodes
        
        # 尝试作为 YAML 解析
        nodes = fetch_local_yaml(source)
        return nodes
    
    # 检查是否是单个节点链接
    if source.startswith('vmess://'):
        node_data = parse_vmess_link(source)
        if node_data:
            nodes.append(ProxyNode.from_dict(node_data))
        return nodes
    elif source.startswith('ss://'):
        node_data = parse_shadowsocks_link(source)
        if node_data:
            nodes.append(ProxyNode.from_dict(node_data))
        return nodes
    elif source.startswith('trojan://'):
        node_data = parse_trojan_link(source)
        if node_data:
            nodes.append(ProxyNode.from_dict(node_data))
        return nodes
    elif source.startswith('vless://'):
        node_data = parse_vless_link(source)
        if node_data:
            nodes.append(ProxyNode.from_dict(node_data))
        return nodes
    elif source.startswith('hysteria://') or source.startswith('hy2://'):
        node_data = parse_hysteria_link(source)
        if node_data:
            nodes.append(ProxyNode.from_dict(node_data))
        return nodes
    
    print(f"  无法识别的源格式: {source}")
    return nodes


def test_node_speed(node: ProxyNode) -> Optional[float]:
    """测试单个节点速度（使用 HTTP 代理）"""
    try:
        proxy_url = None
        
        if node.type == 'vmess':
            # 构建 vmess 代理 URL
            vmess_config = {
                'name': node.name,
                'type': 'vmess',
                'server': node.server,
                'port': node.port,
                'uuid': node.uuid,
                'alterId': node.alterId,
                'cipher': node.cipher,
            }
            if node.network:
                vmess_config['network'] = node.network
            if node.ws_path:
                vmess_config['ws-path'] = node.ws_path
            if node.tls:
                vmess_config['tls'] = node.tls
                
            # 使用 HTTP 代理（需要本地运行 clash）
            proxy_url = f"http://127.0.0.1:7890"  # 默认 Clash 代理端口
        elif node.type == 'ss':
            proxy_url = f"socks5://127.0.0.1:7890"
        elif node.type == 'trojan':
            proxy_url = f"http://127.0.0.1:7890"
        elif node.type == 'vless':
            proxy_url = f"http://127.0.0.1:7890"
        else:
            return None
        
        start_time = time.time()
        
        # 尝试通过代理访问
        proxies = {
            'http': proxy_url,
            'https': proxy_url,
        }
        
        response = requests.get(
            SPEED_TEST_URL,
            proxies=proxies,
            timeout=SPEED_TEST_TIMEOUT,
            allow_redirects=True
        )
        
        elapsed = time.time() - start_time
        
        # 状态码必须为 200 才算可用
        if response.status_code == 200:
            return elapsed
        return None
        
    except Exception as e:
        return None


def test_node_connectivity(node: ProxyNode) -> bool:
    """测试节点连接性（简化版，不依赖本地代理）"""
    import socket
    import ssl
    
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(SPEED_TEST_TIMEOUT)
        
        result = sock.connect_ex((node.server, node.port))
        sock.close()
        
        return result == 0
    except Exception:
        return False


def test_all_nodes(nodes: List[ProxyNode], test_method: str = 'connect') -> List[ProxyNode]:
    """并发测试所有节点"""
    print(f"\n开始测速，共 {len(nodes)} 个节点...")
    
    # 移除重复节点
    unique_nodes = []
    seen = set()
    for node in nodes:
        key = (node.type, node.server, node.port)
        if key not in seen:
            seen.add(key)
            unique_nodes.append(node)
    
    print(f"去重后剩余 {len(unique_nodes)} 个节点")
    
    tested_nodes = []
    failed_count = 0
    
    if test_method == 'connect':
        # 使用连接测试
        with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            future_to_node = {
                executor.submit(test_node_connectivity, node): node 
                for node in unique_nodes
            }
            
            for i, future in enumerate(concurrent.futures.as_completed(future_to_node)):
                node = future_to_node[future]
                try:
                    is_connected = future.result()
                    if is_connected:
                        tested_nodes.append(node)
                        print(f"\r测速进度: {i+1}/{len(unique_nodes)}, 可用: {len(tested_nodes)}", end='')
                    else:
                        failed_count += 1
                        print(f"\r测速进度: {i+1}/{len(unique_nodes)}, 可用: {len(tested_nodes)}", end='')
                except Exception as e:
                    failed_count += 1
                    print(f"\r测速进度: {i+1}/{len(unique_nodes)}, 可用: {len(tested_nodes)}", end='')
    else:
        # 使用代理测速（需要本地 Clash）
        with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            future_to_node = {
                executor.submit(test_node_speed, node): node 
                for node in unique_nodes
            }
            
            for i, future in enumerate(concurrent.futures.as_completed(future_to_node)):
                node = future_to_node[future]
                try:
                    speed = future.result()
                    if speed is not None:
                        node.speed = speed
                        tested_nodes.append(node)
                        print(f"\r测速进度: {i+1}/{len(unique_nodes)}, 可用: {len(tested_nodes)}", end='')
                    else:
                        failed_count += 1
                        print(f"\r测速进度: {i+1}/{len(unique_nodes)}, 可用: {len(tested_nodes)}", end='')
                except Exception as e:
                    failed_count += 1
                    print(f"\r测速进度: {i+1}/{len(unique_nodes)}, 可用: {len(tested_nodes)}", end='')
    
    print(f"\n测试完成！可用节点: {len(tested_nodes)}, 不可用: {failed_count}")
    
    # 按速度排序（可选）
    if test_method == 'speed':
        tested_nodes.sort(key=lambda x: x.speed if x.speed else 999)
    
    return tested_nodes


def generate_clash_config(nodes: List[ProxyNode], output_path: str, config_name: str = "Merged Config"):
    """生成 clash.yaml 配置文件（兼容 Clash/Mihomo 传统格式）"""
    
    # 添加代理节点
    proxies = []
    for node in nodes:
        proxies.append(node.to_dict())
    
    # 获取所有节点名称
    all_proxy_names = [p['name'] for p in proxies]
    
    # 辅助函数：筛选地区节点，如果为空则使用所有节点
    def filter_region(proxy_list, keywords):
        filtered = [p['name'] for p in proxy_list if any(kw in p['name'] for kw in keywords)]
        return filtered if filtered else all_proxy_names
    
    # 添加代理组（传统 Clash 格式）
    proxy_groups = [
        {
            'name': config_name,
            'type': 'url-test',
            'proxies': all_proxy_names,
            'url': 'http://www.gstatic.com/generate_204',
            'interval': 300,
            'tolerance': 50
        },
        {
            'name': '自动选择',
            'type': 'url-test',
            'proxies': all_proxy_names,
            'url': 'http://www.gstatic.com/generate_204',
            'interval': 300,
            'tolerance': 50
        },
        {
            'name': '故障转移',
            'type': 'fallback',
            'proxies': all_proxy_names,
            'url': 'http://www.gstatic.com/generate_204',
            'interval': 300
        },
        {
            'name': '负载均衡',
            'type': 'load-balance',
            'proxies': all_proxy_names,
            'url': 'http://www.gstatic.com/generate_204',
            'interval': 300,
            'strategy': 'consistent-hashing'
        },
        {
            'name': 'HK',
            'type': 'url-test',
            'proxies': filter_region(proxies, ['香港', 'HK', 'HongKong', 'hongkong']),
            'url': 'http://www.gstatic.com/generate_204',
            'interval': 300
        },
        {
            'name': 'US',
            'type': 'url-test',
            'proxies': filter_region(proxies, ['美国', 'US', 'America', 'USA']),
            'url': 'http://www.gstatic.com/generate_204',
            'interval': 300
        },
        {
            'name': 'JP',
            'type': 'url-test',
            'proxies': filter_region(proxies, ['日本', 'JP', 'Japan']),
            'url': 'http://www.gstatic.com/generate_204',
            'interval': 300
        },
        {
            'name': 'SG',
            'type': 'url-test',
            'proxies': filter_region(proxies, ['新加坡', 'SG', 'Singapore']),
            'url': 'http://www.gstatic.com/generate_204',
            'interval': 300
        },
        {
            'name': 'Other',
            'type': 'select',
            'proxies': ['DIRECT'] + all_proxy_names
        }
    ]
    
    # 规则
    rules = [
        'GEOIP,CN,DIRECT',
        'MATCH,Other'
    ]
    
    # 生成完整配置（简化为 Clash Premium/Mihomo 兼容格式）
    clash_config = {
        'port': 7890,
        'socks-port': 7891,
        'redir-port': 7892,
        'mixed-port': 7893,
        'allow-lan': True,
        'mode': 'rule',
        'log-level': 'info',
        'external-controller': '127.0.0.1:9090',
        'proxies': proxies,
        'proxy-groups': proxy_groups,
        'rules': rules
    }
    
    # 写入文件
    with open(output_path, 'w', encoding='utf-8') as f:
        yaml.dump(clash_config, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
    
    print(f"\n配置文件已保存到: {output_path}")
    print(f"节点数量: {len(proxies)}")
    print(f"代理组数量: {len(proxy_groups)}")
    
    return clash_config


def load_sources_from_file(filepath: str) -> List[str]:
    """从文本文件加载订阅源"""
    sources = []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                # 跳过空行和注释行
                if line and not line.startswith('#'):
                    sources.append(line)
        print(f"从文件加载了 {len(sources)} 个订阅源")
    except FileNotFoundError:
        print(f"文件不存在: {filepath}")
    except Exception as e:
        print(f"读取文件失败: {e}")
    return sources


def main():
    parser = argparse.ArgumentParser(description='Clash 订阅获取、测速与合并工具')
    parser.add_argument('-f', '--file', default='sources.txt', help='订阅源列表文件路径 (默认: sources.txt)')
    parser.add_argument('-s', '--sources', nargs='+', help='订阅源 URL (命令行方式)')
    parser.add_argument('-o', '--output', default='merged_clash.yaml', help='输出文件路径')
    parser.add_argument('-t', '--test-method', choices=['connect', 'speed'], default='connect', 
                        help='测速方式: connect(连接测试) 或 speed(通过代理测速，需要本地Clash运行在7890端口)')
    parser.add_argument('-n', '--name', default='合并节点', help='配置名称')
    
    args = parser.parse_args()
    
    all_nodes = []
    
    # 优先使用命令行参数
    if args.sources:
        for source in args.sources:
            nodes = parse_source(source)
            all_nodes.extend(nodes)
    else:
        # 从文件读取订阅源
        sources = load_sources_from_file(args.file)
        if not sources:
            print("\n请在 sources.txt 文件中输入订阅链接，每行一个")
            print("支持以下格式:")
            print("  - 标准订阅链接 (https://example.com/sub)")
            print("  - GitHub Raw 链接 (https://raw.githubusercontent.com/...)")
            print("  - 本地 YAML 文件 (config.yaml, ./path/to/file.yaml)")
            print("  - 单个节点链接 (vmess://..., ss://..., trojan://..., vless://...)")
            print("\n或者直接使用命令行参数:")
            print("  python clash_tools.py -s https://example.com/sub1 https://example.com/sub2")
            print("  python clash_tools.py -s config.yaml other.yaml")
            return
        
        for source in sources:
            nodes = parse_source(source)
            all_nodes.extend(nodes)
    
    # 测试节点
    if all_nodes:
        tested_nodes = test_all_nodes(all_nodes, test_method=args.test_method)
        
        if tested_nodes:
            # 生成配置文件
            generate_clash_config(tested_nodes, args.output, args.name)
            
            # 保存可用节点列表
            node_list_path = args.output.replace('.yaml', '_nodes.txt')
            with open(node_list_path, 'w', encoding='utf-8') as f:
                for node in tested_nodes:
                    f.write(f"{node.name} ({node.type}) - {node.server}:{node.port}\n")
            print(f"节点列表已保存到: {node_list_path}")
        else:
            print("\n没有可用的节点！")


if __name__ == '__main__':
    main()
