import fnmatch
import os
from configparser import MissingSectionHeaderError
from configparser import ParsingError
from typing import List
from typing import Type

from SystemdUnitParser import SystemdUnitParser

from systemdlint.cls.error import Error
from systemdlint.cls.error import ErrorInvalidSection
from systemdlint.cls.error import ErrorSectionMissing
from systemdlint.cls.error import ErrorSyntaxError
from systemdlint.cls.helper import Helper
from systemdlint.cls.sectionTemplate import SectionTemplate


class ConfigTemplate():

    def __init__(self, name: str, globs: List[str],
                 upstream_inputs: List[str] = None,
                 mandatory_sections: List[str] = None,
                 version: int = 10e9) -> None:
        self.__name = name
        self.__runversion = version
        self.__applicable_globs = globs
        self.__upstream_generator_inputs = upstream_inputs

        self.__mandatory_sections = mandatory_sections
        self.__sections = self.__load_sections()
        self.__section_map = {
            x.Name: x for x in self.__sections
        }

    def __load_sections(self) -> List[SectionTemplate]:
        def callback(obj: ConfigTemplate, type: Type) -> object:
            if not issubclass(type, SectionTemplate):
                return None
            if type is SectionTemplate:
                return None
            return type(self.__runversion)
        return Helper.GetSubClasses(self, callback, f'_{self.Name}/*/section.py')

    @property
    def Name(self) -> str:
        return self.__name

    @property
    def ApplicableGlobs(self) -> List[str]:
        return self.__applicable_globs

    @property
    def Sections(self) -> List[SectionTemplate]:
        return self.__sections

    @property
    def MandatorySections(self) -> List[str]:
        return self.__mandatory_sections

    @property
    def UpstreamGeneratorInput(self) -> List[str]:
        return self.__upstream_generator_inputs

    def _matches(self, fn) -> bool:
        for pattern in self.ApplicableGlobs:
            if fnmatch.fnmatch(fn, pattern):
                return True
        return False

    def Parse(self, fn) -> List[Error]:
        res = []
        if not self._matches(fn):
            return res
        __stash = SystemdUnitParser()
        if not os.path.isfile(fn):
            return res
        with open(fn) as i:
            try:
                __stash.read_file(i)
            except (MissingSectionHeaderError) as e:
                res.append(ErrorSyntaxError(e.message.split('\n')[0], 1, fn))
                return res
            except (ParsingError) as e:
                res.append(ErrorSyntaxError(e.message.split('\n')[0], 1, fn))
                return res
            except UnicodeDecodeError:
                # This seems to be a binary
                return res

        for item in self.MandatorySections:
            if item not in dict(__stash).keys():
                res.append(ErrorSectionMissing(item, fn))
        for section in dict(__stash).keys():
            if section == 'DEFAULT':
                continue
            res += self.Validate(fn, section, None, None, __stash)
            for k, v in dict(__stash[section]).items():
                res += self.Validate(fn, section, k, v, __stash)
        return res

    def Validate(self, fn: str, section: str, attribute: str, value: str, stash: List[object]) -> List[Error]:
        obj = self.__section_map.get(section, None)
        if obj is None:
            return [ErrorInvalidSection(section, 1, fn)]
        if attribute:
            return obj.Validate(fn, attribute, value, stash)
        return []

    def __repr__(self):
        return f'{self.Name} -> {self.Sections}'
