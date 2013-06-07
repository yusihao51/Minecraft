### How to bring a new language to pyCraft

* Create a directory named the code of your language
* Copy `pycraft.pot` to the directory, rename `pycraft.pot` to `pycraft.po`
* Edit `pycraft.po` with a po editor

### How to use

* `msgfmt /path/to/your/po/file -o pycraft.mo` you should see a file named `pycraft.mo` in your working directory
* Create a directory `pycraft/locale/your_language_code/LC_MESSAGES` and copy the .mo file to this directory
* Set `Localization.language` to your language code in `game.cfg`




