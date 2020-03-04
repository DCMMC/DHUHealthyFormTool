import PyInstaller.__main__
import os
import platform

UPX_PATH = os.environ.get("UPX_PATH")
pyinstall_args = [
    '--noconfirm',
    '--log-level=INFO',
    '--onefile',
    '--name=DHUHealthyFormTool',
]
if UPX_PATH:
    pyinstall_args.append('--upx-dir=%s' % (UPX_PATH))
system = platform.system()
exe_name = 'DHUHealthyFormTool'
print('#'*60, 'DEBUG: System:', system)
if system == 'Linux':
    exe_name += '_Linux_amd64.bin'
elif system == 'Windows':
    pyinstall_args.append('--console')
    exe_name += '_Windows_amd64.exe'
elif system == 'Darwin':
    exe_name += '_macOS_amd64.app'
    pyinstall_args.append('--console')

pyinstall_args.append('--name=' + exe_name)
pyinstall_args.append("DHU_healthy_form.py")

if __name__ == '__main__':
    PyInstaller.__main__.run(pyinstall_args)
