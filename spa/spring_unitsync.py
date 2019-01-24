import logging
import os
import shutil

from conf import settings
from spa.unitsync import Unitsync

log = logging.getLogger(__name__)


class SpringUnitsync(object):
    def __init__(self, server):
        self.server = server
        self.Maps = {}
        self.Mods = {}
        self.load()

    def load(self):
        log.info('loading spring unitsync wrapper')
        self.Unitsync = Unitsync(settings.UNITSYNC_PATH)
        self.Unitsync.UnInit()
        self.Unitsync.Init(1)

        self.load_maps()
        self.load_mods()
        return True

    def reload_mods(self):
        if not self.Unitsync:
            self.load()
        else:
            self.Unitsync.Init(1)
            self.server.SpringUnitsync.load_mods()

    def load_maps(self):
        log.info('loading spring maps')
        self.Maps = {}
        for iMap in range(0, self.Unitsync.GetMapCount()):
            Map = self.Unitsync.GetMapName(iMap)
            log.info('Load map::' + str(Map))
            self.Maps[Map] = {
                'Hash': self.sign_int(self.Unitsync.GetMapChecksum(iMap)),
                'X': self.Unitsync.GetMapWidth(iMap),
                'Y': self.Unitsync.GetMapHeight(iMap),
                'Description': self.Unitsync.GetMapDescription(iMap),
            }
            if self.Unitsync.GetMapPosCount(iMap):
                self.Maps[Map]['StartPos'] = {}
                for iPos in range(0, self.Unitsync.GetMapPosCount(iMap)):
                    self.Maps[Map]['StartPos'][iPos] = {
                        'X': self.Unitsync.GetMapPosX(iMap, iPos),
                        'Y': self.Unitsync.GetMapPosZ(iMap, iPos),
                    }
            if self.Unitsync.GetMapOptionCount(Map):
                self.Maps[Map]['Options'] = {}
                for iOpt in range(0, self.Unitsync.GetMapOptionCount(Map)):
                    option = self.load_option(iOpt)
                    if len(option) > 0:
                        self.Maps[Map]['Options'][option['Key']] = option

    def load_mods(self):
        log.info('loading spring mods')
        self.Mods = {}
        for i_mod in range(0, self.Unitsync.GetPrimaryModCount()):
            self.Unitsync.RemoveAllArchives()
            mod_archive = self.Unitsync.GetPrimaryModArchive(i_mod)
            mod_archive_path = os.path.expanduser(os.path.join(settings.MODS_PATH, mod_archive))
            mod_public_path = os.path.expanduser(settings.MODS_PUBLIC_PATH)
            if os.path.isfile(mod_archive_path) and os.path.exists(mod_public_path):
                try:
                    shutil.copy2(mod_archive_path, mod_public_path)
                except PermissionError:
                    log.exception("Error while copying mod archive to public path")
            self.Unitsync.AddAllArchives(mod_archive)
            mod = self.Unitsync.GetPrimaryModName(i_mod)
            log.info('Load mod::' + str(mod))
            self.Mods[mod] = {
                'Hash': self.sign_int(self.Unitsync.GetPrimaryModChecksum(i_mod)),
                'Title': mod,
                'Archive': mod_archive,
                'Sides': {},
                'Options': {},
                'AI': {},
                'Units': {},
            }
            if self.Unitsync.GetSideCount():
                for i_side in range(self.Unitsync.GetSideCount()):
                    self.Mods[mod]['Sides'][i_side] = self.Unitsync.GetSideName(i_side)
            if self.Unitsync.GetModOptionCount():
                for i_opt in range(self.Unitsync.GetModOptionCount()):
                    option = self.load_option(i_opt)
                    if len(option) > 0:
                        self.Mods[mod]['Options'][option['Key']] = option
            if self.Unitsync.GetSkirmishAICount():
                for i_AI in range(0, self.Unitsync.GetSkirmishAICount()):
                    self.Mods[mod]['AI'][i_AI] = {}
                    for iAII in range(0, self.Unitsync.GetSkirmishAIInfoCount(i_AI)):
                        self.Mods[mod]['AI'][i_AI][self.Unitsync.GetInfoKey(iAII)] = self.Unitsync.GetInfoValue(
                            iAII)
            self.Unitsync.ProcessUnits()
            if self.Unitsync.GetUnitCount():
                for i_unit in range(0, self.Unitsync.GetUnitCount()):
                    self.Mods[mod]['Units'][self.Unitsync.GetUnitName(i_unit)] = self.Unitsync.GetFullUnitName(i_unit)

    def load_option(self, i_opt):
        data = {}
        if self.Unitsync.GetOptionType(i_opt) == 1:
            data = {
                'Key': self.Unitsync.GetOptionKey(i_opt),
                'Title': self.Unitsync.GetOptionName(i_opt),
                'Type': 'Boolean',
                'Default': self.Unitsync.GetOptionBoolDef(i_opt),
                'Description': self.Unitsync.GetOptionDesc(i_opt),
            }
        elif self.Unitsync.GetOptionType(i_opt) == 2:
            data = {
                'Key': self.Unitsync.GetOptionKey(i_opt),
                'Title': self.Unitsync.GetOptionName(i_opt),
                'Type': 'Select',
                'Default': self.Unitsync.GetOptionListDef(i_opt),
                'Description': self.Unitsync.GetOptionDesc(i_opt),
                'Options': {},
            }
            if self.Unitsync.GetOptionListCount(i_opt):
                for iItem in range(0, self.Unitsync.GetOptionListCount(i_opt)):
                    options = "{0} ({1})".format(self.Unitsync.GetOptionListItemName(i_opt, iItem), self.Unitsync.GetOptionListItemDesc(i_opt, iItem))
                    data['Options'][self.Unitsync.GetOptionListItemKey(i_opt, iItem)] = options
        elif self.Unitsync.GetOptionType(i_opt) == 3:
            data = {
                'Key': self.Unitsync.GetOptionKey(i_opt),
                'Title': self.Unitsync.GetOptionName(i_opt),
                'Type': 'Numeric',
                'Default': self.convert_float(self.Unitsync.GetOptionNumberDef(i_opt)),
                'Min': self.convert_float(self.Unitsync.GetOptionNumberMin(i_opt)),
                'Max': self.convert_float(self.Unitsync.GetOptionNumberMax(i_opt)),
                'Step': self.convert_float(self.Unitsync.GetOptionNumberStep(i_opt)),
                'Description': self.Unitsync.GetOptionDesc(i_opt),
            }
        elif self.Unitsync.GetOptionType(i_opt) == 4:
            data = {
                'Key': self.Unitsync.GetOptionKey(i_opt),
                'Title': self.Unitsync.GetOptionName(i_opt),
                'Type': 'String',
                'Default': self.Unitsync.GetOptionStringDef(i_opt),
                'MaxLength': self.Unitsync.GetOptionStringMaxLen(i_opt),
                'Description': self.Unitsync.GetOptionDesc(i_opt),
            }
        elif self.Unitsync.GetOptionType(i_opt) == 5:
            Ignore = 1  # Group header
        else:
            log.error('Unknown options type (' + str(self.Unitsync.GetOptionType(i_opt)) + ')')
        return data

    def sign_int(self, value):
        if value > 2147483648:
            value = value - 2147483648 * 2
        return value

    def convert_float(self, value):
        if type(value) is float:
            return round(value, 5)
        else:
            return value
