"""
更多实用工具
- 数据库操作
- Git 操作
- HTTP 请求
- JSON 处理
- 日期时间
"""
import json
import sqlite3
import subprocess
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
import requests

from agents.tools import BaseTool, ToolResult


class DatabaseTool(BaseTool):
    """数据库操作工具"""
    name = "database"
    description = "执行 SQLite 数据库操作"
    
    def execute(self, db_path: str, query: str, 
                params: tuple = None, read_only: bool = False) -> ToolResult:
        try:
            # 安全检查：只允许 SELECT 在只读模式
            if read_only and not query.strip().upper().startswith("SELECT"):
                return ToolResult(
                    success=False,
                    output=None,
                    error="Only SELECT queries allowed in read-only mode"
                )
            
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            # 判断是否是查询
            if query.strip().upper().startswith("SELECT"):
                rows = cursor.fetchall()
                result = [dict(row) for row in rows]
            else:
                conn.commit()
                result = {"rows_affected": cursor.rowcount}
            
            cursor.close()
            conn.close()
            
            return ToolResult(success=True, output=result)
        
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


class GitTool(BaseTool):
    """Git 操作工具"""
    name = "git"
    description = "执行 Git 命令"
    
    def execute(self, command: str, repo_path: str = ".", 
                timeout: int = 30) -> ToolResult:
        try:
            # 白名单检查
            allowed_commands = [
                "status", "log", "diff", "branch", "show", 
                "rev-parse", "describe", "tag", "remote"
            ]
            
            cmd_parts = command.split()
            if cmd_parts[0] not in allowed_commands:
                return ToolResult(
                    success=False,
                    output=None,
                    error=f"Command '{cmd_parts[0]}' is not allowed"
                )
            
            full_command = ["git"] + command.split()
            
            result = subprocess.run(
                full_command,
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            return ToolResult(
                success=True,
                output=result.stdout,
                metadata={
                    "stderr": result.stderr,
                    "returncode": result.returncode
                }
            )
        
        except subprocess.TimeoutExpired:
            return ToolResult(
                success=False,
                output=None,
                error=f"Git command timed out after {timeout}s"
            )
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


class HTTPTool(BaseTool):
    """HTTP 请求工具"""
    name = "http"
    description = "发送 HTTP 请求"
    
    def execute(self, url: str, method: str = "GET", 
                headers: Dict = None, body: Dict = None,
                timeout: int = 30) -> ToolResult:
        try:
            # 安全检查：阻止内网请求
            import socket
            from urllib.parse import urlparse
            
            parsed = urlparse(url)
            hostname = parsed.hostname
            
            # 简单的内网检查
            if hostname:
                try:
                    ip = socket.gethostbyname(hostname)
                    if ip.startswith(("10.", "192.168.", "172.")) or ip == "127.0.0.1":
                        return ToolResult(
                            success=False,
                            output=None,
                            error="Internal network access not allowed"
                        )
                except:
                    pass
            
            method = method.upper()
            
            if method == "GET":
                resp = requests.get(url, headers=headers, timeout=timeout)
            elif method == "POST":
                resp = requests.post(url, json=body, headers=headers, timeout=timeout)
            elif method == "PUT":
                resp = requests.put(url, json=body, headers=headers, timeout=timeout)
            elif method == "DELETE":
                resp = requests.delete(url, headers=headers, timeout=timeout)
            else:
                return ToolResult(
                    success=False,
                    output=None,
                    error=f"Method '{method}' not supported"
                )
            
            return ToolResult(
                success=True,
                output={
                    "status_code": resp.status_code,
                    "headers": dict(resp.headers),
                    "body": resp.text[:10000]  # 限制长度
                }
            )
        
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


class JSONTool(BaseTool):
    """JSON 处理工具"""
    name = "json"
    description = "JSON 数据处理"
    
    def execute(self, operation: str, data: str = None, 
                path: str = None, value: Any = None) -> ToolResult:
        try:
            if operation == "parse":
                parsed = json.loads(data)
                return ToolResult(success=True, output=parsed)
            
            elif operation == "stringify":
                if isinstance(data, str):
                    data = json.loads(data)
                result = json.dumps(data, indent=2, ensure_ascii=False)
                return ToolResult(success=True, output=result)
            
            elif operation == "get":
                parsed = json.loads(data) if isinstance(data, str) else data
                keys = path.split(".")
                
                current = parsed
                for key in keys:
                    if isinstance(current, dict):
                        current = current.get(key)
                    elif isinstance(current, list):
                        current = current[int(key)]
                    else:
                        return ToolResult(
                            success=False,
                            output=None,
                            error=f"Cannot access '{key}' on {type(current)}"
                        )
                
                return ToolResult(success=True, output=current)
            
            elif operation == "validate":
                try:
                    if isinstance(data, str):
                        json.loads(data)
                    return ToolResult(success=True, output={"valid": True})
                except json.JSONDecodeError as e:
                    return ToolResult(
                        success=True,
                        output={"valid": False, "error": str(e)}
                    )
            
            else:
                return ToolResult(
                    success=False,
                    output=None,
                    error=f"Unknown operation: {operation}"
                )
        
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


class DateTimeTool(BaseTool):
    """日期时间工具"""
    name = "datetime"
    description = "日期时间计算和格式化"
    
    def execute(self, operation: str, format_str: str = None,
                days: int = 0, hours: int = 0, minutes: int = 0) -> ToolResult:
        try:
            now = datetime.now()
            
            if operation == "now":
                if format_str:
                    return ToolResult(success=True, output=now.strftime(format_str))
                return ToolResult(success=True, output=now.isoformat())
            
            elif operation == "add":
                delta = timedelta(days=days, hours=hours, minutes=minutes)
                result = now + delta
                if format_str:
                    return ToolResult(success=True, output=result.strftime(format_str))
                return ToolResult(success=True, output=result.isoformat())
            
            elif operation == "subtract":
                delta = timedelta(days=days, hours=hours, minutes=minutes)
                result = now - delta
                if format_str:
                    return ToolResult(success=True, output=result.strftime(format_str))
                return ToolResult(success=True, output=result.isoformat())
            
            elif operation == "parse":
                if not format_str:
                    return ToolResult(
                        success=False,
                        output=None,
                        error="format_str required for parse operation"
                    )
                # 需要从参数中获取要解析的字符串
                parsed = datetime.strptime(days, format_str)  # hack: 用 days 传字符串
                return ToolResult(success=True, output=parsed.isoformat())
            
            elif operation == "timestamp":
                return ToolResult(success=True, output=now.timestamp())
            
            else:
                return ToolResult(
                    success=False,
                    output=None,
                    error=f"Unknown operation: {operation}"
                )
        
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


class WeatherTool(BaseTool):
    """天气查询工具（使用开放 API）"""
    name = "weather"
    description = "查询天气信息（需要 Open-Meteo 或类似服务）"
    
    def execute(self, latitude: float, longitude: float, 
                days: int = 1) -> ToolResult:
        try:
            url = "https://api.open-meteo.com/v1/forecast"
            params = {
                "latitude": latitude,
                "longitude": longitude,
                "current_weather": True,
                "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max",
                "forecast_days": days
            }
            
            resp = requests.get(url, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            
            result = {
                "current": data.get("current_weather", {}),
                "daily": data.get("daily", {})
            }
            
            return ToolResult(success=True, output=result)
        
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


class QRCodeTool(BaseTool):
    """二维码生成工具"""
    name = "qrcode"
    description = "生成二维码（返回数据 URL 或保存到文件）"
    
    def execute(self, content: str, output_path: str = None) -> ToolResult:
        try:
            # 尝试使用 qrcode 库
            try:
                import qrcode
                
                qr = qrcode.QRCode(
                    version=1,
                    box_size=10,
                    border=5
                )
                qr.add_data(content)
                qr.make(fit=True)
                
                img = qr.make_image(fill_color="black", back_color="white")
                
                if output_path:
                    img.save(output_path)
                    return ToolResult(
                        success=True,
                        output=f"QR code saved to {output_path}"
                    )
                else:
                    # 返回 base64
                    from io import BytesIO
                    import base64
                    
                    buffer = BytesIO()
                    img.save(buffer, format="PNG")
                    img_str = base64.b64encode(buffer.getvalue()).decode()
                    
                    return ToolResult(
                        success=True,
                        output=f"data:image/png;base64,{img_str}"
                    )
            
            except ImportError:
                return ToolResult(
                    success=False,
                    output=None,
                    error="qrcode library not installed. Run: pip install qrcode"
                )
        
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


# 注册所有新工具
def register_additional_tools(registry=None):
    """注册额外工具"""
    from agents.tools import get_tool_registry
    
    if registry is None:
        registry = get_tool_registry()
    
    registry.register(DatabaseTool())
    registry.register(GitTool())
    registry.register(HTTPTool())
    registry.register(JSONTool())
    registry.register(DateTimeTool())
    registry.register(WeatherTool())
    try:
        registry.register(QRCodeTool())
    except:
        pass  # qrcode 可能未安装
    
    return registry


if __name__ == "__main__":
    # 测试
    registry = register_additional_tools()
    
    print("可用工具:")
    for tool in registry.list_tools():
        print(f"  - {tool.name}: {tool.description}")
