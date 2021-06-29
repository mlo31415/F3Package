# A file to define the Reference class
from __future__ import annotations
from dataclasses import dataclass

from HelpersPackage import WindowsFilenameToWikiPagename

@dataclass(order=False)
class F3Reference:
    #def __init__(self, LinkWikiName: Optional[str]=None, LinkDisplayText: Optional[str]=None, ParentPageName: Optional[str]=None, FanacURL: Optional[str]=None) -> None:
    LinkWikiName: str=""        # The name of the wiki page linked to.  For simple links it is the same as LinkDisplayText
    LinkDisplayText: str=""     # The text displayed for the link on the wiki page.  For simple links it is the same as LinkWikiName
    ParentPageName: str=""      # If from a reference to Fancy, the name of the Fancy page it is on (else None)
    FanacURL: str=""            # If a reference to fanac.org, the URL of the page it was on (else None)

    def Copy(self, val: F3Reference):
        if type(val) is F3Reference:
            self._LinkWikiName=val.LinkWikiName
            self._LinkDisplayText=val.LinkDisplayText
            self._ParentPageName=val.ParentPageName
            self._FanacURL=val.FanacURL
        assert False  # See if this ever happens
        #return self

    def __hash__(self):
        return self.LinkWikiName.__hash__()+self.LinkDisplayText.__hash__()+self.ParentPageName.__hash__()+self.FanacURL.__hash__()

    def __str__(self) -> str:
        return self.LinkDisplayText+" -> "+WindowsFilenameToWikiPagename(self.LinkWikiName)