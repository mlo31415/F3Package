# A file to define a class to extract and hold the characteristics of a Fancy 3 page
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, Union

import os
import xml.etree.ElementTree as ET
import re
import concurrent.futures

from F3Reference import F3Reference
from Log import Log
from HelpersPackage import WikiUrlnameToWikiPagename, SearchAndReplace, WikiRedirectToPagename, SearchAndExtractBounded, WikiLinkSplit, WikidotCanonicizeName

@dataclass
class F3Table:
    Headers: list[str]=field(default_factory=list)
    Rows: list[list[str]]=field(default_factory=list)
    Type: str=""              # A string corresponding to one of the F3 page categories

    #...........................
    def __len__(self) -> int:
        return len(self.Rows)

    #...........................
    def __getitem__(self, i: int) -> Optional[list[str]]:
        if len(self.Rows) <= i:
            return None
        return self.Rows[i]



###################################################################################################

class TagSet:
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

    def __len__(self) -> int:
        return len(self._set)

    def __iter__(self):
        for s in self._set:
            yield s

    def add(self, val: Union[list[str], set[str], str]) -> None:
        # Make sure we have a set to add
        if type(val) is list:
            val=set(val)
        elif type(val) is str:
            val={val}
        # If this is a normalized set, normalize the new values before adding them
        if self._normalized:
            temp=set()
            for v in val:
                temp.add(self.NormalizeCertainNames(v))
            val=temp
        self._set=self._set.union(val)

    def __contains__(self, val: str) -> bool:
        # Do a case insensitive compare if the set is normalized
        if self._normalized:
            val = self.NormalizeCertainNames(val)
        return val in self._set

    def NormalizeCertainNames(self, val: str) -> str:
        if len(val) == 1:
            return val.upper()

        v=val[0].upper()+val[1:]
        v=v.replace("_", " ")  # Mediawiki converts underscores to spaces
        if v == "Us":
            v="US"
        elif v == "Uk":
            v="UK"
        elif v == "Nz":
            v="NZ"
        elif v == "Apa":
            v="APA"
        elif v == "Ia":
            v="IA"
        elif v == "First fandom":
            v="First Fandom"
        return v


###################################################################################################


@dataclass(order=False)
class F3Page:
    WikiFilename: str=""                      # The page's Mediawiki "file" name, e.g., Now_Is_the_Time
    DisplayTitle: str=""                      # The title displayed for the page (takes DISPLAYTITLE into account if it has been set; otherwise is Name)
    Name: str=""                              # The page's Mediawiki name (ignores DISPLAYTITLE, so if DISPLAYTITLE is absent is the same as DisplayTitle)  e.g., Now Is the Time
    Redirect: str=""                         # If this is a redirect page, the Wikiname name of the page to which it redirects
    Tags: TagSet=field(default_factory=TagSet)                                 # A list of tags associated with this page. The case has been normalized
    Rawtags: TagSet=field(default_factory=TagSet)              # A list of tags with case unnormalized (as it actually is on the page)
    OutgoingReferences: list[F3Reference]=field(default_factory=list)  # A list of all the references on this page
    WikiUrlname: str=""
    NumRevisions: int=0
    Pageid: int=0
    Revid: int=0
    Edittime: str=""
    Permalink: str=""
    Timestamp: str=""
    User: str=""
    WindowsFilename: str=""
    Tables: list[F3Table]=field(default_factory=list)
    Source: str=""
    LocaleStr: str=""

    def __post_init__(self):
        self.Rawtags._normalized=False

    def __hash__(self):
        return self.WikiFilename.__hash__()+self.DisplayTitle.__hash__()+self.Name.__hash__()+self.Redirect.__hash__()+self.Tags.__hash__()+self.OutgoingReferences.__hash__()

    def __eq__(self, rhs: F3Page) -> bool:
        if self.WikiFilename != rhs.WikiFilename:
            return False
        if self.DisplayTitle != rhs.DisplayTitle:
            return False
        if self.Name != rhs.Name:
            return False
        if self.Redirect != rhs.Redirect:
            return False
        if self.Tags != rhs.Tags:
            return False
        if self.OutgoingReferences != rhs.OutgoingReferences:
            return False
        return True

    # Check for the presence of a single tag or a list of tags
    def HasTag(self, tags: str|[str]) -> bool:
        if type(tags) is str:
            tags=[tags]

        for tag1 in tags:
            for tag2 in self.Tags:
                if tag1.lower() == tag2.lower():
                    return True
        return False


    @property
    def IsPerson(self) -> bool:
        return self.HasTag(["Fan", "Pro"]) and (self.HasTag("Person") or not self.HasTag("Publisher"))    # "Publisher" is an organization, but if the page is marked Person, let it be

    @property
    def IsFan(self) -> bool:
        return self.HasTag("Fan")

    @property
    def IsFanzine(self) -> bool:
        return self.HasTag(["Fanzine", "Newszine", "Apazine", "Clubzine", "Fanthology"])  # When the database is cleaner we'll only need to check Fanzine

    @property
    def IsAPA(self) -> bool:
        return self.HasTag("APA")

    @property
    def IsStore(self) -> bool:
        return self.HasTag("Store")

    @property
    def IsClub(self) -> bool:
        return self.HasTag("Club")

    @property
    def IsConrunning(self) -> bool:
        return self.HasTag("Conrunning")

    @property
    def IsConInstance(self) -> bool:
        return self.HasTag("Convention") and self.HasTag("Inseries")

    @property
    def IsConSeries(self) -> bool:
        return self.HasTag("Convention") and self.HasTag("Conseries")

    @property
    def IsCatchphrase(self) -> bool:
        return self.HasTag("Catchphrase")

    @property
    def IsBook(self) -> bool:
        return self.HasTag("Book")

    @property
    def IsFiction(self) -> bool:
        return self.HasTag("Fiction")

    @property
    def IsPublisher(self) -> bool:
        return self.HasTag("Publisher")

    @property
    def IsNickname(self) -> bool:
        return self.HasTag("Nickname")

    @property
    def IsLocale(self) -> bool:
        return self.HasTag("Locale")

    @property
    def IsMundane(self) -> bool:
        return self.HasTag("Mundane")

    @property
    def IsWikidot(self) -> bool:
        return self.HasTag("Wikidot")


    @property
    def IsRedirectpage(self) -> bool:
        return self.Redirect != ""

    @property
    # Is this page which exists only to redirect old Wikidot-style links to pages named in Mediawiki style?
    # E.g., is of the form Word-word-word (1st char upper case, all other lc, all special characters and spaces turn into single hyphen
    # Note that Dog as a pagename might (or might not) be a Wikidog redirect.  There's not way to tell without resorting to semantics.
    # TODO: Consider checking for similarity of redirect target's name to page's name
    def IsWikidotRedirectPage(self) -> bool:
        # The only way a page could be a redirect to a Wikidot page is if it *already* in Wikidot canonical form.
        if self.Name != WikidotCanonicizeName(self.Name):
            return False

        s=self.Source
        # If it's not a redirect, it can't be a Wikidot redirect
        l, s=SearchAndReplace("(\s*#redirect\s*\[\[[^]]+]])", s, "", caseinsensitive=True)
        if len(l) == 0:
            return False

        # OK, we know it is a redirect and the name is in the Wikidot canonical form
        # If is *is* tagged as a wikidot redirect, then it is one.
        s=s.strip()
        l, s=SearchAndReplace("(\[\[Category:\s*wikidot]])", s, "", caseinsensitive=True)
        if len(l) > 0:
            return True

        # At this point we know the name is in Wikidot form, we know it is a redirect, and we know it lacks the Wikidot tag.
        # We prefer to be conservative in marking pages as Wikidot redirects, so,
        # If the name contains more than one hyphen, we'll call it a Wikidot redirect, otherwise not.
        return self.Name.count("-") > 1     # (Because it's in Wikidot canonical form, we know there are no doubled hyphens ("--") in the name.)


# ==================================================================================
# ==================================================================================
# ==================================================================================
# Read a page and return a FancyPage
# pagePath will be the path to the page's source (i.e., ending in .txt)
def DigestPage(sitepath: str, pagefname: str) -> Optional[F3Page]:

    # In the hope of speeding up the slowest part of this, use multithreading to overlap reading of source and xml files
    def LoadXML(pagePathXml: str) -> Optional[ET]:
        if not os.path.isfile(pagePathXml):
            Log("DigestPage: Couldn't find '"+pagePathXml+"'")
            return None
        # Read the xml file
        try:
            return ET.parse(pagePathXml)
        except ET.ParseError:
            Log(f"ParseError while reading {pagePathXml}")
            return None

    def LoadSource(pagePathTxt: str) -> Optional[str]:
        if not os.path.isfile(pagePathTxt):
            Log("DigestPage: Couldn't find '"+pagePathTxt+"'")
            return None
        # Open and read the page's source
        with open(os.path.join(pagePathTxt), "rb") as f:   # Reading in binary and doing the funny decode is to handle special characters embedded in some sources.
            return f.read().decode("utf8") # decode("cp437") is magic to handle funny foreign characters

    # Concurrently load the source and xml
    with concurrent.futures.ThreadPoolExecutor() as executor:
        tree=executor.submit(LoadXML, os.path.join(sitepath, pagefname)+".xml").result()
        source=executor.submit(LoadSource, os.path.join(sitepath, pagefname)+".txt").result()

    if tree is None or source is None:
        return None

    # Now process the xml
    fp=F3Page()
    root=tree.getroot()
    for child in root:
        if child.tag == "title":        # Must match tags set in FancyDownloader.SaveMetadata()
            fp.Name=child.text
        elif child.tag == "filename":
            fp.WikiFilename=child.text
        elif child.tag == "urlname":
            fp.WikiUrlname=child.text
        elif child.tag == "isredirectpage":
            # assert(True)
            fp.Isredirectpage=child.text
        elif child.tag == "numrevisions":
            fp.NumRevisions=child.text
        elif child.tag == "pageid":
            fp.Pageid=child.text
        elif child.tag == "revid":
            fp.Revid=child.text
        elif child.tag == "editTime" or child.tag == "edittime":
            fp.Edittime=child.text
        elif child.tag == "permalink":
            fp.Permalink=child.text
        elif child.tag == "categories":
            if child.text is not None and len(child.text) > 0:
                fp.Tags.add(re.findall("Category\(\'Category:(.+?)\'\)", child.text))
        elif child.tag == "timestamp":
            fp.Timestamp=child.text
        elif child.tag == "user":
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
    # (We check this before looking at the Categories because the page could be a redirect *to* a category!)
    isredirect=False
    found, source=SearchAndReplace("^#redirect\s*\[\[(.+?)\]\]", source, "", caseinsensitive=True)
    if len(found) > 0:  # Really, it should never be other than 1 or 0...
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

    # Look for locale=text located in a template call.
    # We're looking for |<spaces?>[Ll]ocale=<spaces?><text>[|}]
    m=re.search("\|\s*[Ll]ocale=([a-zA-Z\s.,\-]+)\s*[|}]", source)
    if m is not None:
        if m.groups()[0] is not None:
            fp.LocaleStr=m.groups()[0]

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
                    # Add the 1st line which is column headers
                    f3t=F3Table()
                    f3t.Headers=[l.strip() for l in line.split("||")]
                    continue
                # Add an ordinary line
                f3t.Rows.append([l.strip() for l in line.split("||")])

            fp.Tables.append(f3t)
        # Get the next tab and then loop
        tab, src=SearchAndExtractBounded(src, "<tab(\s+head=[\"]?top[\"]?)?>", "</tab>")

    # Now we scan the source for outgoing links.
    # A link is one of these formats:
    #   [[link]]
    #   [[link|display text]]

    links=set()     # Start out with a set so we don't keep duplicates. Note that we have defined a Reference() hash function, so we can compare sets

    # Extract the simple links
    lnks1, source=SearchAndReplace("\[\[([^\]]+)\]\]", source, "") # Look for [[stuff]] where stuff does not contain any '|'s '['s or ']'s
    for linktext in lnks1:
        linkparts=WikiLinkSplit(linktext)
        links.add(F3Reference(LinkDisplayText=linkparts[2], ParentPageName=pagefname, LinkWikiName=WikiUrlnameToWikiPagename(linkparts[0]), LinkAnchor=linkparts[1]))
        #Log("  Link: '"+linktext+"'", Print=False)

    fp.OutgoingReferences=list(links)       # We need to turn the set into a list
    return fp
