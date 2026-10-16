"""Copy dependency license texts into a distributable directory."""
import importlib.metadata as metadata
import shutil
import sys
from pathlib import Path


def collect(destination):
    target=Path(destination)/'THIRD-PARTY';target.mkdir(exist_ok=True)
    names=['reportlab','pillow','python-oxmsg','olefile','click','typing_extensions','tzdata','charset-normalizer','pyinstaller']
    lines=['BIOME — embedded components and licenses','Python: https://docs.python.org/3/license.html','PyInstaller bootloader redistribution exception: https://pyinstaller.org/en/stable/license.html','']
    for name in names:
        dist=metadata.distribution(name);lines.append(name+' '+dist.version+' — '+(dist.metadata.get('License-Expression') or dist.metadata.get('License') or 'See package license'))
        for file in dist.files or []:
            if any(part.lower().startswith(('license','copying','notice')) for part in file.parts):
                source=Path(dist.locate_file(file))
                if source.is_file():
                    output=target/name/Path(*file.parts);output.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,output)
    # Python's redistribution license ships with the build interpreter.
    for source in [Path(sys.base_prefix)/'LICENSE.txt',Path(sys.base_prefix)/'LICENSE']:
        if source.exists():shutil.copyfile(source,target/'Python-LICENSE.txt');break
    (target/'COMPONENTS.txt').write_text('\n'.join(lines),encoding='utf-8')

if __name__=='__main__':collect(sys.argv[1])
