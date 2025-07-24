import os
import sys
import subprocess
import shutil
import platform
import uuid
import glob
import shlex
from datetime import datetime

def create_installer():
    """Создает установщик для NeuroCod Pro"""
    print("Создание установщика для NeuroCod Pro...")
    
    # Конфигурация
    app_name = "NeuroCod Pro"
    main_script = "neurocod_app.py"  # Основной файл приложения
    icon_path = "neurocod.ico"       # Путь к иконке приложения
    version = "4.2"
    build_dir = "build"
    dist_dir = "dist"
    installer_dir = "installer"
    requirements = "requirements.txt"
    
    # Проверка наличия основного файла
    if not os.path.exists(main_script):
        print(f"Ошибка: Основной файл приложения '{main_script}' не найден.")
        return
    
    # Проверка наличия иконки
    if not os.path.exists(icon_path):
        print(f"Предупреждение: Файл иконки '{icon_path}' не найден. Будет использована иконка по умолчанию.")
        icon_path = ""
    
    # Создаем структуру папок
    os.makedirs(build_dir, exist_ok=True)
    os.makedirs(dist_dir, exist_ok=True)
    os.makedirs(installer_dir, exist_ok=True)
    
    # Шаг 1: Установка PyInstaller
    print("Установка PyInstaller...")
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Ошибка установки PyInstaller: {e}")
        return
    
    # Шаг 2: Определяем путь к PyInstaller
    pyinstaller_path = find_pyinstaller()
    if not pyinstaller_path:
        print("Ошибка: PyInstaller не найден после установки.")
        return
    
    print(f"PyInstaller найден по пути: {pyinstaller_path}")
    
    # Шаг 3: Сборка приложения с PyInstaller
    print("Сборка приложения...")
    pyinstaller_cmd = [
        pyinstaller_path,
        "--noconfirm",
        "--onefile",
        "--windowed",
        "--name", app_name,
        "--distpath", dist_dir,
        "--workpath", build_dir,
    ]
    
    if icon_path and os.path.exists(icon_path):
        pyinstaller_cmd.extend(["--icon", icon_path])
    
    pyinstaller_cmd.append(main_script)
    
    try:
        # Для Windows используем shell=True
        subprocess.run(pyinstaller_cmd, check=True, shell=True)
    except subprocess.CalledProcessError as e:
        print(f"Ошибка сборки приложения: {e}")
        return
    
    # Шаг 4: Подготовка дополнительных файлов
    print("Подготовка дополнительных файлов...")
    additional_files = [
        "neurocod_config.json",
        "neurocod_history.json",
        "README.md",
        "LICENSE"
    ]
    
    # Создаем целевую папку
    target_dir = os.path.join(dist_dir, app_name)
    os.makedirs(target_dir, exist_ok=True)
    
    # Копируем файлы
    for file in additional_files:
        if os.path.exists(file):
            shutil.copy(file, target_dir)
        else:
            print(f"Предупреждение: Файл '{file}' не найден и не будет включен.")
    
    # Копируем иконку, если она есть
    if icon_path and os.path.exists(icon_path):
        shutil.copy(icon_path, target_dir)
    
    # Шаг 5: Создание установщика
    if platform.system() == "Windows":
        create_windows_installer(app_name, version, dist_dir, installer_dir, icon_path)
    elif platform.system() == "Darwin":
        create_mac_installer(app_name, version, dist_dir, installer_dir)
    else:
        create_linux_installer(app_name, version, dist_dir, installer_dir)
    
    print(f"\nУстановщик успешно создан в папке: {installer_dir}")

def find_pyinstaller():
    """Находит путь к исполняемому файлу PyInstaller"""
    # Пробуем несколько возможных расположений
    possible_paths = [
        os.path.join(os.path.dirname(sys.executable), "Scripts", "pyinstaller.exe"),
        os.path.join(sys.executable.replace("python.exe", "Scripts"), "pyinstaller.exe"),
        os.path.join(os.path.expanduser("~"), "AppData", "Roaming", "Python", f"Python{sys.version_info.major}{sys.version_info.minor}", "Scripts", "pyinstaller.exe")
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            return path
    
    # Пробуем найти через where
    if platform.system() == "Windows":
        try:
            result = subprocess.run(["where", "pyinstaller"], capture_output=True, text=True, check=True)
            paths = result.stdout.strip().split("\n")
            for path in paths:
                if path.endswith(".exe"):
                    return path
        except:
            pass
    
    return None

def create_windows_installer(app_name, version, dist_dir, installer_dir, icon_path):
    """Создает установщик для Windows с помощью Inno Setup"""
    print("Создание установщика Windows...")
    
    # Проверяем установлен ли Inno Setup
    inno_path = find_inno_setup()
    if not inno_path:
        print("Inno Setup не найден. Установите его с https://jrsoftware.org/isdl.php")
        return
    
    # Создаем скрипт Inno Setup
    iss_content = f"""; Скрипт Inno Setup для {app_name}
#define MyAppName "{app_name}"
#define MyAppVersion "{version}"
#define MyAppPublisher "NeuroCod Team"
#define MyAppURL "https://neurocod.example.com"
#define MyAppExeName "{app_name}.exe"

[Setup]
AppId={{{str(uuid.uuid4())}}}
AppName={{#MyAppName}}
AppVersion={{#MyAppVersion}}
AppPublisher={{#MyAppPublisher}}
AppPublisherURL={{#MyAppURL}}
AppSupportURL={{#MyAppURL}}
AppUpdatesURL={{#MyAppURL}}
DefaultDirName={{autopf}}\\{{#MyAppName}}
DisableProgramGroupPage=yes
LicenseFile=LICENSE
OutputDir={os.path.abspath(installer_dir)}
OutputBaseFilename={app_name}_Setup_{version}
Compression=lzma
SolidCompression=yes
"""
    
    if icon_path and os.path.exists(icon_path):
        iss_content += f"SetupIconFile={os.path.abspath(icon_path)}\n"
    
    iss_content += f"""
UninstallDisplayIcon={{app}}\\{{#MyAppExeName}}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "russian"; MessagesFile: "compiler:Languages\\Russian.isl"

[Tasks]
Name: "desktopicon"; Description: "{{cm:CreateDesktopIcon}}"; GroupDescription: "{{cm:AdditionalIcons}}"

[Files]
Source: "{os.path.abspath(dist_dir)}\\{app_name}\\*"; DestDir: "{{app}}"; Flags: ignoreversion recursesubdirs

[Icons]
Name: "{{autoprograms}}\\{{#MyAppName}}"; Filename: "{{app}}\\{{#MyAppExeName}}"
Name: "{{autodesktop}}\\{{#MyAppName}}"; Filename: "{{app}}\\{{#MyAppExeName}}"; Tasks: desktopicon

[Run]
Filename: "{{app}}\\{{#MyAppExeName}}"; Description: "{{cm:LaunchProgram,{{#MyAppName}}}}"; Flags: nowait postinstall skipifsilent
"""
    
    iss_path = os.path.join(installer_dir, "setup.iss")
    with open(iss_path, "w", encoding="utf-8") as f:
        f.write(iss_content)
    
    # Запускаем компиляцию
    try:
        subprocess.run([inno_path, iss_path], check=True, shell=True)
    except subprocess.CalledProcessError as e:
        print(f"Ошибка компиляции Inno Setup: {e}")
    
    # Создаем README для установщика
    create_readme(installer_dir, "windows")

def find_inno_setup():
    """Находит путь к Inno Setup Compiler"""
    # Проверяем стандартные пути установки
    possible_paths = [
        os.path.join(os.environ.get("ProgramFiles(x86)", ""), "Inno Setup 6", "ISCC.exe"),
        os.path.join(os.environ.get("ProgramFiles", ""), "Inno Setup 6", "ISCC.exe"),
        "C:\\Program Files (x86)\\Inno Setup 6\\ISCC.exe",
        "C:\\Program Files\\Inno Setup 6\\ISCC.exe"
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            return path
    
    # Пробуем найти через реестр
    try:
        import winreg
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\ISCC.exe")
        path = winreg.QueryValue(key, "")
        if os.path.exists(path):
            return path
    except:
        pass
    
    return None

def create_mac_installer(app_name, version, dist_dir, installer_dir):
    """Создает установщик для macOS"""
    print("Создание установщика macOS...")
    # Реализация для macOS...

def create_linux_installer(app_name, version, dist_dir, installer_dir):
    """Создает установщик для Linux"""
    print("Создание установщика Linux...")
    # Реализация для Linux...

def create_readme(installer_dir, platform_type):
    """Создает файл README с инструкциями по установке"""
    readme_content = f"""# NeuroCod Pro - Инструкция по установке

## Для {platform_type.capitalize()}

### Windows
1. Запустите файл `NeuroCod_Pro_Setup_4.2.exe`
2. Следуйте инструкциям установщика
3. После установки приложение будет доступно в меню Пуск и на рабочем столе

### Первый запуск
При первом запуске введите ваш API ключ DeepSeek. Вы можете получить его на сайте:
https://platform.deepseek.com/api-keys

## Поддержка
По всем вопросам пишите на support@neurocod.example.com
"""
    
    readme_path = os.path.join(installer_dir, "INSTALL.md")
    with open(readme_path, "w", encoding="utf-8") as f:
        f.write(readme_content)

if __name__ == "__main__":
    create_installer()