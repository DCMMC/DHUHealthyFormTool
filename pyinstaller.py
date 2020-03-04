import PyInstaller.__main__
import os

UPX_PATH = os.environ.get("UPX_PATH")

if UPX_PATH:
    PyInstaller.__main__.run([
            '--noconfirm',
            '--upx-dir=%s' % (UPX_PATH),
            '--log-level=INFO',
            '--onefile',
            '--name=DHUHealthyFormTool',
            "DHU_healthy_form.py",
        ])
else:
    PyInstaller.__main__.run([
            '--noconfirm',
            '--log-level=INFO',
            '--onefile',
            '--name=DHUHealthyFormTool',
            "DHU_healthy_form.py",
        ])

