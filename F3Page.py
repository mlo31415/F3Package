# A file to define a class to extract and hold the characteristics of a Fancy 3 page
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, List, Union, Set, Any
import os
import xml.etree.ElementTree as ET
import re
import concurrent.futures

from F3Reference import F3Reference

from Log import Log
from HelpersPackage import IsInt, WikiUrlnameToWikiPagename, SearchAndReplace, WikiRedirectToPagename, SearchAndExtractBounded

class F3Table:
    def __init__(self):
        self._headers: Optional[List[str]]=None
        self._rows: Optional[List[List[str]]]=None
        self._type: Optional[str]=None              # A string corresponding to one of the F3 page categories

    #...........................
    @property
    def Headers(self) -> Optional[List[str]]:
        return self._headers
    @Headers.setter
    def Headers(self, val: Optional[List[str]]):
        self._headers=val

    #...........................
    @property
    def Type(self) -> Optional[str]:
        return self._type
    @Type.setter
    def Type(self, val: Optional[str]):
        self._type=val

    #...........................
    @property
    def Rows(self) -> List[List[str]]:
        return self._rows
    @Rows.setter
    def Rows(self, val: Optional[List[List[str]]]):
        self._rows=val

    def AppendRow(self, val: List[str]):
        if self._rows is None:
            self._rows=[]
        self._rows.append(val)

    def __len__(self) -> int:
        if self._rows is None:
            return 0
        return len(self._rows)

    #...........................
    def __getitem__(self, i: int) -> Optional[List[str]]:
        if self._rows is None or len(self._rows) <= i:
            return None
        return self._rows[i]



###################################################################################################
def normalize(val: str) -> str:
    if len(val) == 1:
        return val.upper()

    v=val[0].upper()+val[1:]
    v=v.replace("_", " ")   # Mediawiki converts underscores to spaces
    if v == "Us":
        v="US"
    elif v == "Uk":
        v="UK"
    elif v == "Nz":
        v="NZ"
    elif v == "Apa":
        v="APA"
    elif v == "Ia":
        v = "IA"
    elif v == "First fandom":
        v="First Fandom"
    return v

class TagSet():
    def __init__(self, tag: Optional[str]=None, Normalized=True) -> None:
        self._set=set()
        self._normalized=Normalized
        if tag is not None:
            self._set.add(tag)

    # List the tags in alphabetic order
    def __str__(self) -> str:
        s=""
        if self._set is None or len(self._set) == 0:
            return ""
        lst=sorted(list(self._set))
        for x in lst:
            if len(s) > 0:
                s+=", "
            s+=x
        return s

    def __iter__(self):
        for s in self._set:
            yield s

    def add(self, val: Union[List[str], Set[str], str]):
        # Make sure we have a set to add
        if type(val) is list:
            val=set(val)
        elif type(val) is str:
            val={val}
        # If this is a normalized set, normalize the new values before adding them
        if self._normalized:
            temp=set()
            for v in val:
                temp.add(normalize(v))
            val=temp
        self._set=self._set.union(val)

    def __contains__(self, val: str) -> bool:
        # Do a case insensitive compare if the set is normalized
        if self._normalized:
            val = normalize(val)
        return val in self._set


###################################################################################################
@dataclass(order=False)
class F3Page:
    def __init__(self):
        self._WikiFilename: Optional[str]=None                      # The page's Mediawiki "file" name, e.g., Now_Is_the_Time
        self._DisplayTitle: Optional[str]=None                      # The title displayed for the page (takes DISPLAYTITLE into account if it has been set; otherwise is Name)
        self._Name: Optional[str]=None                              # The page's Mediawiki name (ignores DISPLAYTITLE, so if DISPLAYTITLE is absent is the same as DisplayTitle)  e.g., Now Is the Time
        self._Redirect: Optional[str]=None                          # If this is a redirect page, the Wikiname name of the page to which it redirects
        self._Tags: TagSet=TagSet()                                 # A list of tags associated with this page. The case has been normalized
        self._Rawtags: TagSet=TagSet(Normalized=False)              # A list of tags with case unnormalized (as it actually is on the page)
        self._OutgoingReferences: Optional[List[F3Reference]]=None  # A list of all the references on this page
        self._WikiUrlname: Optional[str]=None
        self._NumRevisions: Optional[int]=None
        self._Pageid: Optional[str]=None
        self._Revid: Optional[str]=None
        self._Edittime: Optional[str]=None
        self._Permalink: Optional[str]=None
        self._Timestamp: Optional[str]=None
        self._User: Optional[str]=None
        self._WindowsFilename: Optional[str]=None
        self._Table: List[F3Table]=[]
        self._Source: Optional[str]=None

    def __hash__(self):
        return self._WikiFilename.__hash__()+self._DisplayTitle.__hash__()+self._Name.__hash__()+self._Redirect.__hash__()+self._Tags.__hash__()+self._OutgoingReferences.__hash__()

    def __eq__(self, rhs: F3Page) -> bool:
        if self._WikiFilename != rhs._WikiFilename:
            return False
        if self._DisplayTitle != rhs._DisplayTitle:
            return False
        if self._Name != rhs._Name:
            return False
        if self._Redirect != rhs._Redirect:
            return False
        if self._Tags != rhs._Tags:
            return False
        if self._OutgoingReferences != rhs._OutgoingReferences:
            return False
        return True

    def IsPerson(self) -> bool:
        return self._Tags is not None and ("Fan" in self._Tags or "Pro" in self._Tags) and \
               ("Person" in self._Tags or "Publisher" not in self._Tags)    # "Publisher" is an organization, but if the page is marked Person, let it be


    @property
    def DisplayTitle(self) -> str:
        if self._DisplayTitle is not None:
            return self._DisplayTitle
        return self._Name
    @DisplayTitle.setter
    def DisplayTitle(self, val: Optional[str]):
        self._DisplayTitle=val


    @property
    def WikiUrlname(self) -> str:
        return self._WikiUrlname
    @WikiUrlname.setter
    def WikiUrlname(self, val: Optional[str]):
        self._WikiUrlname=val


    @property
    def Name(self) -> str:
        return self._Name
    @Name.setter
    def Name(self, val: Optional[str]):
        self._Name=val


    @property
    def Redirect(self) -> str:
        return self._Redirect
    @Redirect.setter
    def Redirect(self, val: Optional[str]):
        self._Redirect=val


    @property
    def UltimateRedirect(self) -> Optional[str]:
        if self.IsRedirectpage:
            return self.Redirect
        return self.Name
    # There is no setter since this is computer

    @property
    def IsRedirectpage(self) -> bool:
        return self._Redirect is not None and len(self._Redirect) > 0

    @property
    def Tags(self) -> TagSet[str]:
        return self._Tags
    @Tags.setter
    def Tags(self, val: Any):
        assert(True)
    @property
    def Rawtags(self) -> TagSet[str]:
        return self._Rawtags


    @property
    def OutgoingReferences(self) -> List[F3Reference]:
        return self._OutgoingReferences
    @OutgoingReferences.setter
    def OutgoingReferences(self, val: Optional[str]):
        self._OutgoingReferences=val


    @property
    def WikiFilename(self) -> Optional[str]:
        return self._WikiFilename
    @WikiFilename.setter
    def WikiFilename(self, val: Optional[str]):
        self._WikiFilename=val


    @property
    def NumRevisions(self) -> Optional[int]:
        return self._NumRevisions
    @NumRevisions.setter
    def NumRevisions(self, val: Union[str, int]):
        if isinstance(val, int):
            self._NumRevisions=val
        elif isinstance(val, str):
            if IsInt(val):
                self._NumRevisions=int(val)
            else:
                Log("F3Page.NumRevisions setter: not an int: '"+val+"'", isError=True)
        else:
            self._NumRevisions=None


    @property
    def Pageid(self) -> Optional[int]:
        return self._Pageid
    @Pageid.setter
    def Pageid(self, val: Union[str, int]):
        if isinstance(val, int):
            self._Pageid=val
        elif isinstance(val, str):
            if IsInt(val):
                self._Pageid=int(val)
            else:
                Log("F3Page.Pageid setter: not an int: '"+val+"'", isError=True)
        else:
            self._Pageid=None


    @property
    def Revid(self) -> Optional[int]:
        return self._Revid
    @Revid.setter
    def Revid(self, val: Union[str, int]):
        if isinstance(val, int):
            self._Revid=val
        elif isinstance(val, str):
            if IsInt(val):
                self._Revid=int(val)
            else:
                Log("F3Page.Revid setter: not an int: '"+val+"'", isError=True)
        else:
            self._Revid=None


    @property
    def Edittime(self) -> Optional[str]:
        return self._Edittime
    @Edittime.setter
    def Edittime(self, val: Optional[str]):
        self._Edittime=val


    @property
    def Permalink(self) -> Optional[str]:
        return self._Permalink
    @Permalink.setter
    def Permalink(self, val: Optional[str]):
        self._Permalink=val


    @property
    def Timestamp(self) -> Optional[str]:
        return self._Timestamp
    @Timestamp.setter
    def Timestamp(self, val: Optional[str]):
        self._Timestamp=val


    @property
    def User(self) -> Optional[str]:
        return self._User
    @User.setter
    def User(self, val: Optional[str]):
        self._User=val


    @property
    def WindowsFilename(self) -> Optional[str]:
        return self._WindowsFilename
    @WindowsFilename.setter
    def WindowsFilename(self, val: Optional[str]):
        self._WindowsFilename=val


    @property
    def Table(self) -> List[F3Table]:
        return self._Table
    @Table.setter
    def Table(self, val: List[F3Table]):
        self._Table=val


    @property
    def Source(self) -> Optional[str]:
        return self._Source
    @Source.setter
    def Source(self, val: Optional[str]):
        self._Source=val


# ==================================================================================
# ==================================================================================
# ==================================================================================
# Read a page and return a FancyPage
# pagePath will be the path to the page's source (i.e., ending in .txt)
def DigestPage(sitepath: str, pagefname: str) ->Optional[F3Page]:

    pagePathTxt=os.path.join(sitepath, pagefname)+".txt"
    pagePathXml=os.path.join(sitepath, pagefname)+".xml"

    if not os.path.isfile(pagePathTxt):
        Log("DigestPage: Couldn't find '"+pagePathTxt+"'")
        return None
    if not os.path.isfile(pagePathXml):
        Log("DigestPage: Couldn't find '"+pagePathXml+"'")
        return None

    fp=F3Page()

    # In the hope of speeding up the slowest part of this, use multithreading to overlap reading of source and xml files
    def LoadXML(pagePathXml: str) -> ET:
        # Read the xml file
        return ET.parse(pagePathXml)
    def LoadSource(pagePathTxt: str) -> str:
        # Open and read the page's source
        with open(os.path.join(pagePathTxt), "rb") as f:   # Reading in binary and doing the funny decode is to handle special characters embedded in some sources.
            return f.read().decode("utf8") # decode("cp437") is magic to handle funny foreign characters
    with concurrent.futures.ThreadPoolExecutor() as executor:
        tree=executor.submit(LoadXML, pagePathXml).result()
        source=executor.submit(LoadSource, pagePathTxt).result()

    # Now process the xml
    root=tree.getroot()
    for child in root:
        if child.tag == "title":        # Must match tags set in FancyDownloader.SaveMetadata()
            fp.Name=child.text
        if child.tag == "filename":
            fp.WikiFilename=child.text
        if child.tag == "urlname":
            fp.WikiUrlname=child.text
        if child.tag == "isredirectpage":
            # assert(True)
            fp.Isredirectpage=child.text
        if child.tag == "numrevisions":
            fp.NumRevisions=child.text
        if child.tag == "pageid":
            fp.Pageid=child.text
        if child.tag == "revid":
            fp.Revid=child.text
        if child.tag == "editTime" or child.tag == "edittime":
            fp.Edittime=child.text
        if child.tag == "permalink":
            fp.Permalink=child.text

        if child.tag == "categories":
            if child.text is not None and len(child.text) > 0:
                fp.Tags.add(re.findall("Category\(\'Category:(.+?)\'\)", child.text))

        if child.tag == "timestamp":
            fp.Timestamp=child.text
        if child.tag == "user":
            fp.User=child.text

    fp.WindowsFilename=pagefname

    #Log("Page: "+fp.Name, Print=False)

    # Now process the page sources
    if len(source) == 0:
        return None
    fp.Source=source

    # Remove some bits of code that are not relevant and might confuse by replacing them with the empty string
    found, source=SearchAndReplace("^{{displaytitle:\s*(.+?)\}\}", source, "", caseinsensitive=True) # Note use of lazy quantifier
    if len(found) == 1:
        fp.DisplayTitle=found[0]
        #Log("  DISPLAYTITLE found: '"+found[0]+"'", Print=False)

    # Is this a redirect page?
    # (We check this before looking for Categories because it could be a redirect *to* a category!)
    isredirect=False
    found, source=SearchAndReplace("^#redirect\s*\[\[(.+?)\]\]", source, "", caseinsensitive=True)        # Ugly way to handle UC/lc, but it needs to be in the pattern
    if len(found) == 1: # If we found a redirect, then there's no point in looking for links, also, so we're done.
        fp.Redirect=WikiRedirectToPagename(found[0])
        isredirect=True

    # Look for Category statements
    found, source=SearchAndReplace("\[\[category:\s*(.+?)\s*\]\]", source, "", caseinsensitive=True)
    if len(found) > 0:
        for f in found:
            # A "|" indicates that the category sortorder was over-ridden.  The "|" and everything following should be ignored here.
            if "|" in f:
                f=f[:f.index("|")]
            if f not in fp.Tags:
                Log("In page '"+fp.Name+"' tag '"+f+"' was found in [[Category:]] but not in the metadata")
        fp.Tags.add(found)
        #Log("  Category(s) found:"+" | ".join(found), Print=False)

    # If the page was a redirect, we're done.
    if isredirect:
        return fp

    # Some kinds of wiki markup show up as [[html]]...[[/html]] and we want to ignore all this
    found, source=SearchAndReplace('\[\[html\]\].*?\[\[/html\]\]', source, "", numGroups=0, caseinsensitive=True)

    #--------------
    # Look for tables in the page (there really should only be one, but sometimes...)
    # It will begin with "<tab head=top>" (or sometimes just "<tab>" and end with "</tab>"
    # Look for the start and end
    tab, src=SearchAndExtractBounded(source, "<tab(\s+head=[\"]?top[\"]?)?>", "</tab>")
    while tab is not None:
        # If a table was found, split it into an array of lines
        tab=tab.split("\n")
        # The structure of a table is:
        #   <tab head=top>
        #   Header line xx||xx||xx||xx...
        #   one or more row lins
        #   </tab>
        if len(tab) > 1:    # Gotta have a header and at least one row
            f3t=None
            for line in tab:
                if len(line) == 0:
                    continue
                if f3t is None:
                    f3t=F3Table()
                    f3t.Headers=[l.strip() for l in line.split("||")]
                    continue
                f3t.AppendRow([l.strip() for l in line.split("||")])
            fp.Table.append(f3t)
        tab, src=SearchAndExtractBounded(src, "<tab(\s+head=[\"]?top[\"]?)?>", "</tab>")

    # Now we scan the source for outgoing links.
    # A link is one of these formats:
    #   [[link]]
    #   [[link|display text]]

    links=set()     # Start out with a set so we don't keep duplicates. Note that we have defined a Reference() hash function, so we can compare sets

    # Extract the simple links
    lnks1, source=SearchAndReplace("\[\[([^\|\[\]]+?)\]\]", source, "") # Look for [[stuff]] where stuff does not contain any '|'s '['s or ']'s
    for linktext in lnks1:
        links.add(F3Reference(LinkDisplayText=linktext.strip(), ParentPageName=pagefname, LinkWikiName=WikiUrlnameToWikiPagename(linktext.strip())))
        #Log("  Link: '"+linktext+"'", Print=False)

    # Now extract the links containing a '|' and add them to the set of output References
    lnks2, source=SearchAndReplace("\[\[([^\|\[\]]+?\|[^\|\[\]]+?)\]\]", source, "") # Look for [[stuff|morestuff]] where stuff and morestuff does not contain any '|'s '['s or ']'s
    for linktext in lnks2:  # Process the links of the form [[xxx|yyy]]
        #Log("   "+pagefname+" has a link: '"+linktext+"'")
        # Now look at the possibility of the link containing display text.  If there is a "|" in the link, then only the text to the left of the "|" is the link
        if "|" in linktext:
            linktext=linktext.split("|")
            if len(linktext) > 2:
                Log("Page("+pagefname+") has a link '"+"|".join(linktext)+"' with more than two components", isError=True)
            links.add(F3Reference(LinkDisplayText=linktext[1].strip(), ParentPageName=pagefname, LinkWikiName=WikiUrlnameToWikiPagename(linktext[0].strip())))
        else:
            Log("***Page("+pagefname+"}: No '|' found in alleged double link: '"+linktext+"'", isError=True)

    fp.OutgoingReferences=list(links)       # We need to turn the set into a list
    return fp
