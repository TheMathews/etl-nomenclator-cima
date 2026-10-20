"""
module.telemetry
================

Módulo para la recolección de telemetría multiplataforma (Linux/Windows).
Obtiene datos detallados del ejecutable, el usuario, el hardware y el entorno.
Incluye resolución robusta de IP local y nomenclatura estandarizada (snake_case).

Version: 1.1.0
Build date: 2026-04-11
"""

import os
import sys
import hashlib
import socket
import getpass
import platform
import psutil
import distro
import cpuinfo
import time
from datetime import datetime
from typing import Any, Dict

class TelemetryCollector:
    __version__ = "1.1.0"
    __build_date__ = "2026-04-11"

    def __init__(self):
        self.system = platform.system()

    def _result_base(self) -> Dict[str, Any]:
        return {
            "library_version": self.__version__,
            "build_date": self.__build_date__,
            "success": False,
            "data": {},
            "duration": 0.0,
            "error": None,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }

    def collect_all(self) -> Dict[str, Any]:
        result = self._result_base()
        start_time = time.time()
        
        try:
            result["data"] = {
                "app": self._get_executable_info(),
                "user": self._get_user_info(),
                "hardware": self._get_hardware_info()
            }
            result["success"] = True
        except Exception as e:
            result["error"] = str(e)
        
        result["duration"] = round(time.time() - start_time, 4)
        return result

    def _get_local_ip(self) -> str:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
        except Exception:
            ip = "127.0.0.1"
        finally:
            s.close()
        return ip

    def _get_executable_info(self) -> Dict[str, Any]:
        exe_path = os.path.abspath(sys.argv[0])
        stats = os.stat(exe_path)
        
        with open(exe_path, "rb") as f:
            file_hash = hashlib.md5(f.read()).hexdigest().upper()
        
        return {
            "executable_name": os.path.basename(exe_path),
            "executable_path": os.path.dirname(exe_path) + ("\\" if self.system == "Windows" else "/"),
            "md5_hash": file_hash,
            "creation_date": datetime.fromtimestamp(stats.st_ctime).strftime('%d/%m/%Y %H:%M:%S'),
            "size_bytes": stats.st_size,
            "parameters": {
                "count": len(sys.argv) - 1,
                "values": sys.argv[1:]
            },
            "info": {
                "company_name": "Tu Empresa",
                "file_description": "Backend Terminal v3",
                "file_version": "1.0.0.1",
                "product_name": "Nombre de producto"
            }
        }

    def _get_user_info(self) -> Dict[str, Any]:
        return {
            "username": getpass.getuser(),
            "user_domain": os.environ.get('USERDOMAIN', socket.gethostname().split('.')[0]),
            "full_name": getpass.getuser(),
            "is_admin": os.getuid() == 0 if self.system != "Windows" else False,
            "profile_path": os.path.expanduser("~"),
            "language": os.environ.get('LANG', 'es_ES.UTF-8'),
            "timezone_name": datetime.now().astimezone().tzname(),
            "timezone_utc": f"UTC{datetime.now().astimezone().strftime('%z')}",
            "logon_time": datetime.fromtimestamp(psutil.boot_time()).strftime('%d/%m/%Y %H:%M:%S')
        }

    def _get_hardware_info(self) -> Dict[str, Any]:
        return {
            "uuid": self._get_uuid(),
            "hostname": socket.gethostname(),
            "local_ip": self._get_local_ip(),  # <-- IP movida a hardware
            "os_name": distro.name() if self.system == "Linux" else f"Windows {platform.release()}",
            "os_version": platform.version(),
            "processor": cpuinfo.get_cpu_info().get('brand_raw', 'Unknown'),
            "cores": psutil.cpu_count(logical=True),
            "memory_mb": int(psutil.virtual_memory().total / (1024**2)),
            "printers": self._get_printers(),
            "monitors": self._get_monitors()
        }

    def _get_uuid(self) -> str:
        try:
            if self.system == "Windows":
                import subprocess
                return subprocess.check_output('wmic csproduct get uuid').decode().split('\n')[1].strip()
            if os.path.exists("/etc/machine-id"):
                with open("/etc/machine-id", "r") as f: return f.read().strip().upper()
        except: pass
        return "UNKNOWN"

    def _get_printers(self) -> list:
        printers = []
        try:
            if self.system == "Windows":
                import subprocess
                out = subprocess.check_output('wmic printer get name').decode().split('\n')
                printers = [{"name": p.strip()} for p in out[1:] if p.strip()]
            else:
                import subprocess
                out = subprocess.check_output(['lpstat', '-e']).decode().split('\n')
                printers = [{"name": p.strip()} for p in out if p.strip()]
        except: pass
        return printers

    def _get_monitors(self) -> list:
        monitors = []
        try:
            from screeninfo import get_monitors
            for i, m in enumerate(get_monitors()):
                monitors.append({
                    "monitor_id": str(i + 1),
                    "resolution": f"{m.width}x{m.height}"
                })
        except:
            monitors.append({"monitor_id": "1", "resolution": "1920x1080"})
        return monitors