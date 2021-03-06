import ctypes
import os
from ctypes import POINTER, c_ushort, c_int, c_uint, c_float, Structure, create_string_buffer, cast, pointer


class c_char_p(ctypes.c_char_p):
    @classmethod
    def _check_retval_(cls, result):
        value = result.value
        return value.decode('utf-8')


class StartPos(Structure):
    _fields_ = [('x', c_int), ('y', c_int)]

    def __str__(self):
        return '(%i, %i)' % (self.x, self.y)


class MapInfo(Structure):
    def __init__(self):
        # BUG: author field shows up as empty, probably something to do with the fact it's after the startpos structs
        self.author = cast(create_string_buffer(200), c_char_p)
        self.description = cast(create_string_buffer(255), c_char_p)

    _fields_ = [('description', c_char_p),
                ('tidalStrength', c_int),
                ('gravity', c_int),
                ('maxMetal', c_float),
                ('extractorRadius', c_int),
                ('minWind', c_int),
                ('maxWind', c_int),
                ('width', c_int),
                ('height', c_int),
                ('posCount', c_int),
                ('StartPos', StartPos * 16),
                ('author', c_char_p)]


class Unitsync(object):
    def has(self, name):
        """query whether the loaded unitsync exports a particular procedure."""
        return hasattr(self.unitsync, name)

    def _init(self, name, restype):
        """Load a procedure from unitsync and assign its return type."""
        if self.has(name):
            getattr(self.unitsync, name).restype = restype

    def __init__(self, location):
        """Load unitsync from location and attempt to load all known procedures.
        Location must end with .so (Linux), .dylib(MacOS) or .dll (Windows)"""
        if location.endswith('.so') or location.endswith('.dylib'):
            self.unitsync = ctypes.cdll.LoadLibrary(location)
        elif location.endswith('.dll'):
            locationdir = os.path.dirname(location)
            # load devil first, to avoid dll conflicts
            ctypes.windll.LoadLibrary(locationdir + "/devil.dll")
            # load other dependencies, in case the spring dir is not in PATH
            ctypes.windll.LoadLibrary(locationdir + "/ILU.dll")
            ctypes.windll.LoadLibrary(locationdir + "/SDL.dll")
            self.unitsync = ctypes.windll.LoadLibrary(location)

        self._init("GetNextError", c_char_p)
        self._init("GetSpringVersion", c_char_p)
        self._init("Init", c_int)
        self._init("GetWritableDataDirectory", c_char_p)
        self._init("ProcessUnits", c_int)
        self._init("ProcessUnitsNoChecksum", c_int)
        self._init("GetUnitCount", c_int)
        self._init("GetUnitName", c_char_p)
        self._init("GetFullUnitName", c_char_p)
        self._init("GetArchiveChecksum", c_uint)
        self._init("GetArchivePath", c_char_p)
        self._init("GetMapInfoEx", c_int)
        self._init("GetMapInfo", c_int)
        self._init("GetMapCount", c_int)
        self._init("GetMapName", c_char_p)
        self._init("GetMapFileName", c_char_p)
        self._init("GetMapDescription", c_char_p)
        self._init("GetMapAuthor", c_char_p)
        self._init("GetMapWidth", c_int)
        self._init("GetMapHeight", c_int)
        self._init("GetMapTidalStrength", c_int)
        self._init("GetMapWindMin", c_int)
        self._init("GetMapWindMax", c_int)
        self._init("GetMapGravity", c_int)
        self._init("GetMapResourceCount", c_int)
        self._init("GetMapResourceName", c_char_p)
        self._init("GetMapResourceMax", c_float)
        self._init("GetMapResourceExtractorRadius", c_int)
        self._init("GetMapPosCount", c_int)
        self._init("GetMapPosX", c_float)
        self._init("GetMapPosZ", c_float)
        self._init("GetMapMinHeight", c_float)
        self._init("GetMapMaxHeight", c_float)
        self._init("GetMapArchiveCount", c_int)
        self._init("GetMapArchiveName", c_char_p)
        self._init("GetMapChecksum", c_uint)
        self._init("GetMapChecksumFromName", c_uint)
        self._init("GetMinimap", POINTER(c_ushort))
        self._init("GetInfoMapSize", c_int)
        self._init("GetInfoMap", c_int)
        self._init("GetSkirmishAICount", c_int)
        self._init("GetSkirmishAIInfoCount", c_int)
        self._init("GetInfoKey", c_char_p)
        self._init("GetInfoValue", c_char_p)
        self._init("GetInfoDescription", c_char_p)
        self._init("GetSkirmishAIOptionCount", c_int)
        self._init("GetPrimaryModCount", c_int)
        self._init("GetPrimaryModName", c_char_p)
        self._init("GetPrimaryModShortName", c_char_p)
        self._init("GetPrimaryModVersion", c_char_p)
        self._init("GetPrimaryModMutator", c_char_p)
        self._init("GetPrimaryModGame", c_char_p)
        self._init("GetPrimaryModShortGame", c_char_p)
        self._init("GetPrimaryModDescription", c_char_p)
        self._init("GetPrimaryModArchive", c_char_p)
        self._init("GetPrimaryModArchiveCount", c_int)
        self._init("GetPrimaryModArchiveList", c_char_p)
        self._init("GetPrimaryModIndex", c_int)
        self._init("GetPrimaryModChecksum", c_uint)
        self._init("GetPrimaryModChecksumFromName", c_uint)
        self._init("GetSideCount", c_int)
        self._init("GetSideName", c_char_p)
        self._init("GetSideStartUnit", c_char_p)
        self._init("GetMapOptionCount", c_int)
        self._init("GetModOptionCount", c_int)
        self._init("GetCustomOptionCount", c_int)
        self._init("GetOptionKey", c_char_p)
        self._init("GetOptionScope", c_char_p)
        self._init("GetOptionName", c_char_p)
        self._init("GetOptionSection", c_char_p)
        self._init("GetOptionStyle", c_char_p)
        self._init("GetOptionDesc", c_char_p)
        self._init("GetOptionType", c_int)
        self._init("GetOptionBoolDef", c_int)
        self._init("GetOptionNumberDef", c_float)
        self._init("GetOptionNumberMin", c_float)
        self._init("GetOptionNumberMax", c_float)
        self._init("GetOptionNumberStep", c_float)
        self._init("GetOptionStringDef", c_char_p)
        self._init("GetOptionStringMaxLen", c_int)
        self._init("GetOptionListCount", c_int)
        self._init("GetOptionListDef", c_char_p)
        self._init("GetOptionListItemKey", c_char_p)
        self._init("GetOptionListItemName", c_char_p)
        self._init("GetOptionListItemDesc", c_char_p)
        self._init("GetModValidMapCount", c_int)
        self._init("GetModValidMap", c_char_p)
        self._init("OpenFileVFS", c_int)
        self._init("ReadFileVFS", c_int)
        self._init("FileSizeVFS", c_int)
        self._init("InitFindVFS", c_int)
        self._init("InitDirListVFS", c_int)
        self._init("InitSubDirsVFS", c_int)
        self._init("FindFilesVFS", c_int)
        self._init("OpenArchive", c_int)
        self._init("OpenArchiveType", c_int)
        self._init("FindFilesArchive", c_int)
        self._init("OpenArchiveFile", c_int)
        self._init("ReadArchiveFile", c_int)
        self._init("SizeArchiveFile", c_int)
        self._init("GetSpringConfigFile", c_char_p)
        self._init("GetSpringConfigString", c_char_p)
        self._init("GetSpringConfigInt", c_int)
        self._init("GetSpringConfigFloat", c_float)
        self._init("lpOpenFile", c_int)
        self._init("lpOpenSource", c_int)
        self._init("lpExecute", c_int)
        self._init("lpErrorLog", c_char_p)
        self._init("lpRootTable", c_int)
        self._init("lpRootTableExpr", c_int)
        self._init("lpSubTableInt", c_int)
        self._init("lpSubTableStr", c_int)
        self._init("lpSubTableExpr", c_int)
        self._init("lpGetKeyExistsInt", c_int)
        self._init("lpGetKeyExistsStr", c_int)
        self._init("lpGetIntKeyType", c_int)
        self._init("lpGetStrKeyType", c_int)
        self._init("lpGetIntKeyListCount", c_int)
        self._init("lpGetIntKeyListEntry", c_int)
        self._init("lpGetStrKeyListCount", c_int)
        self._init("lpGetStrKeyListEntry", c_char_p)
        self._init("lpGetIntKeyIntVal", c_int)
        self._init("lpGetStrKeyIntVal", c_int)
        self._init("lpGetIntKeyBoolVal", c_int)
        self._init("lpGetStrKeyBoolVal", c_int)
        self._init("lpGetIntKeyFloatVal", c_float)
        self._init("lpGetStrKeyFloatVal", c_float)
        self._init("lpGetIntKeyStrVal", c_char_p)
        self._init("lpGetStrKeyStrVal", c_char_p)

    def GetNextError(self):
        return self.unitsync.GetNextError()

    def GetSpringVersion(self):
        return self.unitsync.GetSpringVersion()

    def Init(self, id):
        return self.unitsync.Init(True, id)

    def UnInit(self):
        return self.unitsync.UnInit()

    def GetWritableDataDirectory(self):
        return self.unitsync.GetWritableDataDirectory()

    def ProcessUnits(self):
        return self.unitsync.ProcessUnits()

    def ProcessUnitsNoChecksum(self):
        return self.unitsync.ProcessUnitsNoChecksum()

    def GetUnitCount(self):
        return self.unitsync.GetUnitCount()

    def GetUnitName(self, unit):
        return self.unitsync.GetUnitName(unit)

    def GetFullUnitName(self, unit):
        return self.unitsync.GetFullUnitName(unit)

    def AddArchive(self, name):
        return self.unitsync.AddArchive(name)

    def AddAllArchives(self, root):
        return self.unitsync.AddAllArchives(root.encode('utf-8'))

    def RemoveAllArchives(self):
        return self.unitsync.RemoveAllArchives()

    def GetArchiveChecksum(self, arname):
        return self.unitsync.GetArchiveChecksum(arname)

    def GetArchivePath(self, arname):
        return self.unitsync.GetArchivePath(arname)

    def GetMapInfoEx(self, mapName, outInfo, version):
        return self.unitsync.GetMapInfoEx(mapName, pointer(outInfo), version)

    def GetMapInfo(self, mapName, outInfo):
        return self.unitsync.GetMapInfo(mapName, pointer(outInfo))

    def GetMapCount(self):
        return self.unitsync.GetMapCount()

    def GetMapName(self, index):
        return self.unitsync.GetMapName(index)

    def GetMapFileName(self, index):
        return self.unitsync.GetMapFileName(index)

    def GetMapDescription(self, index):
        return self.unitsync.GetMapDescription(index)

    def GetMapAuthor(self, index):
        return self.unitsync.GetMapAuthor(index)

    def GetMapWidth(self, index):
        return self.unitsync.GetMapWidth(index)

    def GetMapHeight(self, index):
        return self.unitsync.GetMapHeight(index)

    def GetMapTidalStrength(self, index):
        return self.unitsync.GetMapTidalStrength(index)

    def GetMapWindMin(self, index):
        return self.unitsync.GetMapWindMin(index)

    def GetMapWindMax(self, index):
        return self.unitsync.GetMapWindMax(index)

    def GetMapGravity(self, index):
        return self.unitsync.GetMapGravity(index)

    def GetMapResourceCount(self, index):
        return self.unitsync.GetMapResourceCount(index)

    def GetMapResourceName(self, index, resourceIndex):
        return self.unitsync.GetMapResourceName(index, resourceIndex)

    def GetMapResourceMax(self, index, resourceIndex):
        return self.unitsync.GetMapResourceMax(index, resourceIndex)

    def GetMapResourceExtractorRadius(self, index, resourceIndex):
        return self.unitsync.GetMapResourceExtractorRadius(index, resourceIndex)

    def GetMapPosCount(self, index):
        return self.unitsync.GetMapPosCount(index)

    def GetMapPosX(self, index, posIndex):
        return self.unitsync.GetMapPosX(index, posIndex)

    def GetMapPosZ(self, index, posIndex):
        return self.unitsync.GetMapPosZ(index, posIndex)

    def GetMapMinHeight(self, mapName):
        return self.unitsync.GetMapMinHeight(mapName)

    def GetMapMaxHeight(self, mapName):
        return self.unitsync.GetMapMaxHeight(mapName)

    def GetMapArchiveCount(self, mapName):
        return self.unitsync.GetMapArchiveCount(mapName)

    def GetMapArchiveName(self, index):
        return self.unitsync.GetMapArchiveName(index)

    def GetMapChecksum(self, index):
        return self.unitsync.GetMapChecksum(index)

    def GetMapChecksumFromName(self, mapName):
        return self.unitsync.GetMapChecksumFromName(mapName)

    def GetMinimap(self, filename, miplevel):
        return self.unitsync.GetMinimap(filename, miplevel)

    def GetInfoMapSize(self, mapName, name, width, height):
        return self.unitsync.GetInfoMapSize(mapName, name, width, height)

    def GetInfoMap(self, mapName, name, data, typeHint):
        return self.unitsync.GetInfoMap(mapName, name, pointer(data), typeHint)

    def GetSkirmishAICount(self):
        return self.unitsync.GetSkirmishAICount()

    def GetSkirmishAIInfoCount(self, index):
        return self.unitsync.GetSkirmishAIInfoCount(index)

    def GetInfoKey(self, index):
        return self.unitsync.GetInfoKey(index)

    def GetInfoValue(self, index):
        return self.unitsync.GetInfoValue(index)

    def GetInfoDescription(self, index):
        return self.unitsync.GetInfoDescription(index)

    def GetSkirmishAIOptionCount(self, index):
        return self.unitsync.GetSkirmishAIOptionCount(index)

    def GetPrimaryModCount(self):
        return self.unitsync.GetPrimaryModCount()

    def GetPrimaryModName(self, index):
        return self.unitsync.GetPrimaryModName(index)

    def GetPrimaryModShortName(self, index):
        return self.unitsync.GetPrimaryModShortName(index)

    def GetPrimaryModVersion(self, index):
        return self.unitsync.GetPrimaryModVersion(index)

    def GetPrimaryModMutator(self, index):
        return self.unitsync.GetPrimaryModMutator(index)

    def GetPrimaryModGame(self, index):
        return self.unitsync.GetPrimaryModGame(index)

    def GetPrimaryModShortGame(self, index):
        return self.unitsync.GetPrimaryModShortGame(index)

    def GetPrimaryModDescription(self, index):
        return self.unitsync.GetPrimaryModDescription(index)

    def GetPrimaryModArchive(self, index):
        return self.unitsync.GetPrimaryModArchive(index)

    def GetPrimaryModArchiveCount(self, index):
        return self.unitsync.GetPrimaryModArchiveCount(index)

    def GetPrimaryModArchiveList(self, arnr):
        return self.unitsync.GetPrimaryModArchiveList(arnr)

    def GetPrimaryModIndex(self, name):
        return self.unitsync.GetPrimaryModIndex(name)

    def GetPrimaryModChecksum(self, index):
        return self.unitsync.GetPrimaryModChecksum(index)

    def GetPrimaryModChecksumFromName(self, name):
        return self.unitsync.GetPrimaryModChecksumFromName(name)

    def GetSideCount(self):
        return self.unitsync.GetSideCount()

    def GetSideName(self, side):
        return self.unitsync.GetSideName(side)

    def GetSideStartUnit(self, side):
        return self.unitsync.GetSideStartUnit(side)

    def GetMapOptionCount(self, mapName):
        return self.unitsync.GetMapOptionCount(mapName.encode('utf-8'))

    def GetModOptionCount(self):
        return self.unitsync.GetModOptionCount()

    def GetCustomOptionCount(self, filename):
        return self.unitsync.GetCustomOptionCount(filename)

    def GetOptionKey(self, optIndex):
        return self.unitsync.GetOptionKey(optIndex)

    def GetOptionScope(self, optIndex):
        return self.unitsync.GetOptionScope(optIndex)

    def GetOptionName(self, optIndex):
        return self.unitsync.GetOptionName(optIndex)

    def GetOptionSection(self, optIndex):
        return self.unitsync.GetOptionSection(optIndex)

    def GetOptionStyle(self, optIndex):
        return self.unitsync.GetOptionStyle(optIndex)

    def GetOptionDesc(self, optIndex):
        return self.unitsync.GetOptionDesc(optIndex)

    def GetOptionType(self, optIndex):
        return self.unitsync.GetOptionType(optIndex)

    def GetOptionBoolDef(self, optIndex):
        return self.unitsync.GetOptionBoolDef(optIndex)

    def GetOptionNumberDef(self, optIndex):
        return self.unitsync.GetOptionNumberDef(optIndex)

    def GetOptionNumberMin(self, optIndex):
        return self.unitsync.GetOptionNumberMin(optIndex)

    def GetOptionNumberMax(self, optIndex):
        return self.unitsync.GetOptionNumberMax(optIndex)

    def GetOptionNumberStep(self, optIndex):
        return self.unitsync.GetOptionNumberStep(optIndex)

    def GetOptionStringDef(self, optIndex):
        return self.unitsync.GetOptionStringDef(optIndex)

    def GetOptionStringMaxLen(self, optIndex):
        return self.unitsync.GetOptionStringMaxLen(optIndex)

    def GetOptionListCount(self, optIndex):
        return self.unitsync.GetOptionListCount(optIndex)

    def GetOptionListDef(self, optIndex):
        return self.unitsync.GetOptionListDef(optIndex)

    def GetOptionListItemKey(self, optIndex, itemIndex):
        return self.unitsync.GetOptionListItemKey(optIndex, itemIndex)

    def GetOptionListItemName(self, optIndex, itemIndex):
        return self.unitsync.GetOptionListItemName(optIndex, itemIndex)

    def GetOptionListItemDesc(self, optIndex, itemIndex):
        return self.unitsync.GetOptionListItemDesc(optIndex, itemIndex)

    def GetModValidMapCount(self):
        return self.unitsync.GetModValidMapCount()

    def GetModValidMap(self, index):
        return self.unitsync.GetModValidMap(index)

    def OpenFileVFS(self, name):
        return self.unitsync.OpenFileVFS(name)

    def CloseFileVFS(self, handle):
        return self.unitsync.CloseFileVFS(handle)

    def ReadFileVFS(self, handle, buf, length):
        return self.unitsync.ReadFileVFS(handle, pointer(buf), length)

    def FileSizeVFS(self, handle):
        return self.unitsync.FileSizeVFS(handle)

    def InitFindVFS(self, pattern):
        return self.unitsync.InitFindVFS(pattern)

    def InitDirListVFS(self, path, pattern, modes):
        return self.unitsync.InitDirListVFS(path, pattern, modes)

    def InitSubDirsVFS(self, path, pattern, modes):
        return self.unitsync.InitSubDirsVFS(path, pattern, modes)

    def FindFilesVFS(self, handle, nameBuf, size):
        return self.unitsync.FindFilesVFS(handle, nameBuf, size)

    def OpenArchive(self, name):
        return self.unitsync.OpenArchive(name)

    def OpenArchiveType(self, name, type):
        return self.unitsync.OpenArchiveType(name, type)

    def CloseArchive(self, archive):
        return self.unitsync.CloseArchive(archive)

    def FindFilesArchive(self, archive, cur, nameBuf, size):
        return self.unitsync.FindFilesArchive(archive, cur, nameBuf, size)

    def OpenArchiveFile(self, archive, name):
        return self.unitsync.OpenArchiveFile(archive, name)

    def ReadArchiveFile(self, archive, handle, buffer, numBytes):
        return self.unitsync.ReadArchiveFile(archive, handle, pointer(buffer), numBytes)

    def CloseArchiveFile(self, archive, handle):
        return self.unitsync.CloseArchiveFile(archive, handle)

    def SizeArchiveFile(self, archive, handle):
        return self.unitsync.SizeArchiveFile(archive, handle)

    def SetSpringConfigFile(self, filenameAsAbsolutePath):
        return self.unitsync.SetSpringConfigFile(filenameAsAbsolutePath)

    def GetSpringConfigFile(self):
        return self.unitsync.GetSpringConfigFile()

    def GetSpringConfigString(self, name, defvalue):
        return self.unitsync.GetSpringConfigString(name, defvalue)

    def GetSpringConfigInt(self, name, defvalue):
        return self.unitsync.GetSpringConfigInt(name, defvalue)

    def GetSpringConfigFloat(self, name, defvalue):
        return self.unitsync.GetSpringConfigFloat(name, defvalue)

    def SetSpringConfigString(self, name, value):
        return self.unitsync.SetSpringConfigString(name, value)

    def SetSpringConfigInt(self, name, value):
        return self.unitsync.SetSpringConfigInt(name, value)

    def SetSpringConfigFloat(self, name, value):
        return self.unitsync.SetSpringConfigFloat(name, value)

    def lpClose(self):
        return self.unitsync.lpClose()

    def lpOpenFile(self, filename, fileModes, accessModes):
        return self.unitsync.lpOpenFile(filename, fileModes, accessModes)

    def lpOpenSource(self, source, accessModes):
        return self.unitsync.lpOpenSource(source, accessModes)

    def lpExecute(self):
        return self.unitsync.lpExecute()

    def lpErrorLog(self):
        return self.unitsync.lpErrorLog()

    def lpAddTableInt(self, key, override):
        return self.unitsync.lpAddTableInt(key, override)

    def lpAddTableStr(self, key, override):
        return self.unitsync.lpAddTableStr(key, override)

    def lpEndTable(self):
        return self.unitsync.lpEndTable()

    def lpAddIntKeyIntVal(self, key, val):
        return self.unitsync.lpAddIntKeyIntVal(key, val)

    def lpAddStrKeyIntVal(self, key, val):
        return self.unitsync.lpAddStrKeyIntVal(key, val)

    def lpAddIntKeyBoolVal(self, key, val):
        return self.unitsync.lpAddIntKeyBoolVal(key, val)

    def lpAddStrKeyBoolVal(self, key, val):
        return self.unitsync.lpAddStrKeyBoolVal(key, val)

    def lpAddIntKeyFloatVal(self, key, val):
        return self.unitsync.lpAddIntKeyFloatVal(key, val)

    def lpAddStrKeyFloatVal(self, key, val):
        return self.unitsync.lpAddStrKeyFloatVal(key, val)

    def lpAddIntKeyStrVal(self, key, val):
        return self.unitsync.lpAddIntKeyStrVal(key, val)

    def lpAddStrKeyStrVal(self, key, val):
        return self.unitsync.lpAddStrKeyStrVal(key, val)

    def lpRootTable(self):
        return self.unitsync.lpRootTable()

    def lpRootTableExpr(self, expr):
        return self.unitsync.lpRootTableExpr(expr)

    def lpSubTableInt(self, key):
        return self.unitsync.lpSubTableInt(key)

    def lpSubTableStr(self, key):
        return self.unitsync.lpSubTableStr(key)

    def lpSubTableExpr(self, expr):
        return self.unitsync.lpSubTableExpr(expr)

    def lpPopTable(self):
        return self.unitsync.lpPopTable()

    def lpGetKeyExistsInt(self, key):
        return self.unitsync.lpGetKeyExistsInt(key)

    def lpGetKeyExistsStr(self, key):
        return self.unitsync.lpGetKeyExistsStr(key)

    def lpGetIntKeyType(self, key):
        return self.unitsync.lpGetIntKeyType(key)

    def lpGetStrKeyType(self, key):
        return self.unitsync.lpGetStrKeyType(key)

    def lpGetIntKeyListCount(self):
        return self.unitsync.lpGetIntKeyListCount()

    def lpGetIntKeyListEntry(self, index):
        return self.unitsync.lpGetIntKeyListEntry(index)

    def lpGetStrKeyListCount(self):
        return self.unitsync.lpGetStrKeyListCount()

    def lpGetStrKeyListEntry(self, index):
        return self.unitsync.lpGetStrKeyListEntry(index)

    def lpGetIntKeyIntVal(self, key, defVal):
        return self.unitsync.lpGetIntKeyIntVal(key, defVal)

    def lpGetStrKeyIntVal(self, key, defVal):
        return self.unitsync.lpGetStrKeyIntVal(key, defVal)

    def lpGetIntKeyBoolVal(self, key, defVal):
        return self.unitsync.lpGetIntKeyBoolVal(key, defVal)

    def lpGetStrKeyBoolVal(self, key, defVal):
        return self.unitsync.lpGetStrKeyBoolVal(key, defVal)

    def lpGetIntKeyFloatVal(self, key, defVal):
        return self.unitsync.lpGetIntKeyFloatVal(key, defVal)

    def lpGetStrKeyFloatVal(self, key, defVal):
        return self.unitsync.lpGetStrKeyFloatVal(key, defVal)

    def lpGetIntKeyStrVal(self, key, defVal):
        return self.unitsync.lpGetIntKeyStrVal(key, defVal)

    def lpGetStrKeyStrVal(self, key, defVal):
        return self.unitsync.lpGetStrKeyStrVal(key, defVal)
