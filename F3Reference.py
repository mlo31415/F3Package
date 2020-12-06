# A file to define the Reference class
from __future__ import annotations
from typing import Optional
from dataclasses import dataclass

from HelpersPackage import WindowsFilenameToWikiPagename

@dataclass(order=False)
class F3Reference:
    def __init__(self, LinkWikiName: Optional[str]=None, LinkDisplayText: Optional[str]=None, ParentPageName: Optional[str]=None, FanacURL: Optional[str]=None) -> None:
        self._LinkWikiName=LinkWikiName         # The wiki name of the page being linked to if it is a link to Fancy 3 (else None)
                                                # Note that this not the wiki page's canonical name.
        self._LinkDisplayText=LinkDisplayText   # The text actually used on the page for the link [[the stuff between the brackets]]
        self._ParentPageName=ParentPageName     # If from a reference to Fancy, the name of the Fancy page it is on (else None)
        self._FanacURL=FanacURL                 # If a reference to fanac.org, the URL of the page it was on (else None)

    def Copy(self, val):
        if type(val) is F3Reference:
            self._LinkWikiName=val.LinkWikiName
            self._LinkDisplayText=val.LinkText
            self._ParentPageName=val.ParentPageName
            self._FanacURL=val.FanacURL
        return self

    def __hash__(self):
        return self._LinkWikiName.__hash__()+self._LinkDisplayText.__hash__()+self._ParentPageName.__hash__()+self._FanacURL.__hash__()

    def __str__(self) -> str:
        return self._LinkDisplayText+" -> "+WindowsFilenameToWikiPagename(self._LinkWikiName)

    @property
    def LinkText(self) -> str:
        return self._LinkDisplayText

    @property
    def LinkWikiName(self) -> str:
        return self._LinkWikiName

    @property
    def ParentPageName(self) -> str:
        return self._ParentPageName

    @property
    def FanacURL(self) -> str:
        return self._FanacURL