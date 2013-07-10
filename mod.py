# Imports, sorted alphabetically.

# Python packages
import importlib
import os
import sys

# Third-party packages

# Modules from this project
import globals as G
from debug import log_info

__all__ = ('load_modules')

def load_modules(server=False):
	mod_dir = os.path.join(G.game_dir, 'mods')

	if not os.path.isdir(mod_dir):
		if os.path.exists(mod_dir):
			os.remove(mod_dir)
		os.makedirs(mod_dir)

	sys.path.append(mod_dir)

	log_info('Mod loader has identified %d mods to load' % (len(os.listdir(mod_dir))))
	for name in os.listdir(mod_dir):
		module = importlib.import_module(name)
		module.initialize(server)
