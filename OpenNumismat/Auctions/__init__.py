from PyQt4 import QtCore, QtGui

import urllib.error
import urllib.parse
import urllib.request
try:
    import lxml.html
except ImportError:
    print('lxml module missed. Auction parsing not available')

from OpenNumismat.Tools.CursorDecorators import waitCursorDecorator


class _NotDoneYetError(Exception):
    pass


class _CanceledError(Exception):
    pass


class AuctionItem:
    def __init__(self, place):
        self.place = place
        self.saller = ''
        self.info = ''
        self.grade = ''


class _AuctionParser(QtCore.QObject):
    def __init__(self, parent=None):
        QtCore.QObject.__init__(self, parent)

        self.html = ''

    def category(self, cat):
        return []

    def pages(self, auctNo, category):
        raise NotImplementedError

    def getPageUrl(self, auctNo, category, page):
        raise NotImplementedError

    def parsePage(self, url):
        self.readHtmlPage(url, self._encoding())

        if len(self.doc) == 0:
            return

        try:
            return self._parsePage()
        except _NotDoneYetError:
            print("Auction not done yet")
#            QtGui.QMessageBox.warning(self.parent(),
#                            self.tr("Parse auction lot"),
#                            self.tr("Auction not done yet"),
#                            QtGui.QMessageBox.Ok)
        except _CanceledError:
            print("Auction canceled")
#            QtGui.QMessageBox.warning(self.parent(),
#                            self.tr("Parse auction lot"),
#                            self.tr("Auction canceled"),
#                            QtGui.QMessageBox.Ok)

#    @waitCursorDecorator
    def parse(self, url):
        self.readHtmlPage(url, self._encoding())

        if len(self.doc) == 0:
            return

        try:
            return self._parse()
        except _NotDoneYetError:
            print("Auction not done yet")
#            QtGui.QMessageBox.warning(self.parent(),
#                            self.tr("Parse auction lot"),
#                            self.tr("Auction not done yet"),
#                            QtGui.QMessageBox.Ok)
        except _CanceledError:
            print("Auction canceled")
#            QtGui.QMessageBox.warning(self.parent(),
#                            self.tr("Parse auction lot"),
#                            self.tr("Auction canceled"),
#                            QtGui.QMessageBox.Ok)

    def readHtmlPage(self, url, encoding='utf-8'):
        # TODO: Remove debug output
        print(url)
        try:
            data = urllib.request.urlopen(url).read()

            self.doc = data.decode(encoding, 'ignore')
            self.html = lxml.html.fromstring(self.doc)
            self.url = url
        except (ValueError, urllib.error.URLError):
            print("Error while reading page %s" % url)
            return False

        return True

    def _encoding(self):
        return 'utf-8'

    def _parse(self):
        raise NotImplementedError

    def _parsePage(self):
        raise NotImplementedError


from OpenNumismat.Auctions.AuctionParser import MolotokParser
from OpenNumismat.Auctions.AuctionParser import AuctionSpbParser
from OpenNumismat.Auctions.AuctionParser import ConrosParser
from OpenNumismat.Auctions.AuctionParser import WolmarParser


def getParser(url, parent=None):
    if MolotokParser.verifyDomain(url):
        return MolotokParser(parent)
    elif AuctionSpbParser.verifyDomain(url):
        return AuctionSpbParser(parent)
    elif ConrosParser.verifyDomain(url):
        return ConrosParser(parent)
    elif WolmarParser.verifyDomain(url):
        return WolmarParser(parent)
