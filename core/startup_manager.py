import os
import subprocess
from core.logger import logger


def _ps_escape(value):
    return str(value).replace("`", "``").replace('"', '`"')


def get_startup_programs():
    programs = []
    startup_dirs = [
        os.path.join(os.environ.get("APPDATA", ""), "Microsoft", "Windows",
                     "Start Menu", "Programs", "Startup"),
        os.path.join(os.environ.get("PROGRAMDATA", ""), "Microsoft", "Windows",
                     "Start Menu", "Programs", "Startup"),
    ]
    for startup_dir in startup_dirs:
        if not os.path.exists(startup_dir):
            continue
        for f in os.listdir(startup_dir):
            fp = os.path.join(startup_dir, f)
            programs.append({
                "name": os.path.splitext(f)[0],
                "path": fp,
                "type": "file",
                "enabled": True,
                "source": "startup_folder",
            })
    reg_paths = [
        (r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run", "HKCU"),
        (r"SOFTWARE\Microsoft\Windows\CurrentVersion\RunOnce", "HKCU"),
        (r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run", "HKLM"),
        (r"SOFTWARE\Microsoft\Windows\CurrentVersion\RunOnce", "HKLM"),
    ]
    for reg_path, hive in reg_paths:
        try:
            ps_script = (
                f'$props = Get-ItemProperty -Path "{hive}:{reg_path}" -ErrorAction SilentlyContinue; '
                "if ($props) { "
                "$props.PSObject.Properties | "
                "Where-Object { $_.Name -notlike 'PS*' -and $_.Name -ne '(default)' } | "
                "ForEach-Object { [PSCustomObject]@{Name=$_.Name; Value=$_.Value} } | "
                "ConvertTo-Json -Compress "
                "} "
            )
            result = subprocess.run(
                ["powershell", "-Command", ps_script],
                capture_output=True, text=True, timeout=15, creationflags=0x08000000
            )
            if result.returncode == 0 and result.stdout.strip():
                import json
                raw = result.stdout.strip()
                parsed = json.loads(raw)
                if isinstance(parsed, dict):
                    parsed = [parsed]
                for prop in parsed:
                    v = prop.get("Value")
                    k = prop.get("Name")
                    if not k or not isinstance(v, str):
                        continue
                    if "\\exe" in v.lower() or v.lower().endswith(".exe"):
                        programs.append({
                            "name": k,
                            "path": v,
                            "type": "registry",
                            "enabled": True,
                            "source": f"registry_{hive}",
                            "reg_path": f"{hive}:{reg_path}",
                        })
        except Exception:
            pass
    return programs


def disable_startup_program(program):
    if program.get("type") == "file":
        try:
            fp = program["path"]
            disabled_path = fp + ".disabled"
            os.rename(fp, disabled_path)
            program["path"] = disabled_path
            program["enabled"] = False
            logger.info(f"Автозагрузка отключена: {program['name']}")
            return True
        except Exception as e:
            logger.error(f"Ошибка отключения {program['name']}: {e}")
            return False
    elif program.get("type") == "registry":
        try:
            reg_path = program.get("reg_path", "")
            name = program.get("name", "")
            if not reg_path or not name:
                return False
            safe_path = _ps_escape(reg_path)
            safe_name = _ps_escape(name)
            cmd = f'Remove-ItemProperty -Path "{safe_path}" -Name "{safe_name}" -Force -ErrorAction SilentlyContinue'
            subprocess.run(
                ["powershell", "-Command", cmd],
                capture_output=True, timeout=15, creationflags=0x08000000
            )
            program["enabled"] = False
            logger.info(f"Реестр автозагрузки отключён: {name}")
            return True
        except Exception as e:
            logger.error(f"Ошибка: {e}")
            return False
    return False


def enable_startup_program(program):
    if program.get("type") == "file":
        try:
            fp = program["path"]
            if fp.endswith(".disabled"):
                enabled_path = fp[:-9]
                os.rename(fp, enabled_path)
                program["path"] = enabled_path
                program["enabled"] = True
                logger.info(f"Автозагрузка включена: {program['name']}")
                return True
        except Exception as e:
            logger.error(f"Ошибка: {e}")
            return False
    return False


def _ps_escape_str(value):
    return str(value).replace("'", "''")


def uninstall_program(program_name):
    try:
        safe_name = _ps_escape_str(program_name)
        ps_script = (
            "$uninst = $null; "
            "foreach ($p in @("
            "'HKLM:\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\*', "
            "'HKLM:\\Software\\WOW6432Node\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\*', "
            "'HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\*')) { "
            "Get-ItemProperty $p -ErrorAction SilentlyContinue | "
            "Where-Object { $_.DisplayName -eq '" + safe_name + "' } | "
            "ForEach-Object { $uninst = $_.UninstallString } "
            "}; "
            "if ($uninst) { "
            "$uninst = $uninst -replace '/I\\{', '/X{' -replace '/i\\{', '/X{'; "
            "cmd /c \"$uninst\" "
            "} else { exit 2 }"
        )
        result = subprocess.run(
            ["powershell", "-Command", ps_script],
            capture_output=True, text=True, timeout=300, creationflags=0x08000000
        )
        if result.returncode == 0:
            logger.info(f"Программа удалена: {program_name}")
            return True, result.stdout
        return False, result.stderr or "Uninstall command finished with errors."
    except Exception as e:
        logger.error(f"Ошибка удаления {program_name}: {e}")
        return False, str(e)


def get_installed_programs():
    programs = []
    try:
        result = subprocess.run(
            ["powershell", "-Command",
             "Get-ItemProperty HKLM:\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\*, HKLM:\\Software\\WOW6432Node\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\* | Select-Object DisplayName, DisplayVersion, Publisher, InstallDate, EstimatedSize | Where-Object {$_.DisplayName} | ConvertTo-Json"],
            capture_output=True, text=True, timeout=30, creationflags=0x08000000
        )
        if result.returncode == 0 and result.stdout.strip():
            import json
            data = json.loads(result.stdout.strip())
            if isinstance(data, dict):
                data = [data]
            for item in data:
                programs.append({
                    "name": item.get("DisplayName", ""),
                    "version": item.get("DisplayVersion", ""),
                    "publisher": item.get("Publisher", ""),
                    "install_date": item.get("InstallDate", ""),
                    "size_mb": round((item.get("EstimatedSize", 0) or 0) / 1024, 1),
                })
            programs.sort(key=lambda p: p["name"].lower())
    except Exception as e:
        logger.error(f"Ошибка получения списка программ: {e}")
    return programs
