# -*- coding: utf-8 -*-

import urllib.parse

from PyQt5 import QtGui, QtCore
from PyQt5.QtWidgets import *

from OpenNumismat.Auctions import AuctionItem
from OpenNumismat.Auctions import _AuctionParser, _NotDoneYetError, _CanceledError
from OpenNumismat.Tools.Converters import stringToMoney


class MolotokParser(_AuctionParser):
    HostName = 'molotok.ru'

    @staticmethod
    def verifyDomain(url):
        return (urllib.parse.urlparse(url).hostname == MolotokParser.HostName)

    def __init__(self, parent=None):
        super(MolotokParser, self).__init__(parent)

    def _parse(self):
        try:
            self.html.get_element_by_id('siBidForm2')
            raise _NotDoneYetError()
        except KeyError:
            pass

        try:
            siWrapper = self.html.get_element_by_id('siWrapper')
        except KeyError:
            # Already moved to archive (after 2 months after done)
            raise _CanceledError()

        alleLink = siWrapper.find_class('alleLink')
        if alleLink:
            bidCount = int(alleLink[0].text_content().split()[0])
            if bidCount < 2:
                QMessageBox.information(self.parent(),
                                    self.tr("Parse auction lot"),
                                    self.tr("Only 1 bid"),
                                    QMessageBox.Ok)
        else:
            raise _CanceledError()

        auctionItem = AuctionItem('Молоток.Ру')

        content = siWrapper.find_class('timeInfo')[0].text_content()
        begin = content.find('(')
        end = content.find(',')
        date = content[begin + 1:end]  # convert 'завершен (19 Январь, 00:34:14)' to '19 января'
        day, month = date.split()
        month = month[0:3].lower()
        date = ' '.join((day, month))
        tmpDate = QtCore.QDate.fromString(date, 'dd MMM')
        currentDate = QtCore.QDate.currentDate()
        auctionItem.date = QtCore.QDate(currentDate.year(), tmpDate.month(),
                                    tmpDate.day()).toString(QtCore.Qt.ISODate)

        saller = siWrapper.find_class('sellerDetails')[0].cssselect('dl dt')[0].text_content()
        auctionItem.saller = saller.split()[0].strip()
        buyer = siWrapper.find_class('buyerInfo')[0].cssselect('strong')[1].text_content()
        auctionItem.buyer = buyer.strip()

        # Remove STYLE element
        for element in self.html.get_element_by_id('user_field').cssselect('style'):
            element.getparent().remove(element)
        info = self.html.get_element_by_id('user_field').text_content()
        auctionItem.info = info.strip() + '\n' + self.url

        index = self.doc.find("$('.galleryWrap').newGallery")
        bIndex = self.doc[index:].find("large:") + index
        bIndex = self.doc[bIndex:].find("[") + bIndex
        eIndex = self.doc[bIndex:].find("]") + bIndex
        images = self.doc[bIndex + 1:eIndex].strip()
        images = images.replace('"', '')
        auctionItem.images = images.split(',')

        content = siWrapper.get_element_by_id('itemFinishBox2').cssselect('strong')[0].text_content()
        auctionItem.price = stringToMoney(content)

        element = siWrapper.get_element_by_id('paymentShipment').cssselect('dd strong')
        if element:
            content = element[0].text_content()
            shipmentPrice = stringToMoney(content)
            auctionItem.totalPayPrice = str(auctionItem.price + shipmentPrice)
        else:
            auctionItem.totalPayPrice = auctionItem.price

        auctionItem.totalSalePrice = self.totalSalePrice(auctionItem)

        return auctionItem

    def totalSalePrice(self, lot):
        price = float(lot.price)
        if price > 50000:
            excess = price - 50000
            commission = 1557.5 + (excess * 2.5 / 100)
        elif price > 10000:
            excess = price - 10000
            commission = 357.5 + (excess * 3 / 100)
        elif lot.price > 500:
            excess = price - 500
            commission = 25 + (excess * 3.5 / 100)
        else:
            commission = price * 5 / 100

        if commission > 3999:
            commission = 3999

        return str(price - commission)


class AuctionSpbParser(_AuctionParser):
    HostNames = ('www.auction.spb.ru', 'auction.spb.ru')
    Categories = [
#            "Все категории",
            "Монеты России до 1917 года (золото, серебро)",
            "Монеты России до 1917 года (медь)",
            "Монеты РСФСР, СССР, России",
            "Допетровские монеты",
            "Боны",
            "Монеты антика, средневековье",
            "Монеты иностранные",
            "Награды, медали, знаки, жетоны, пряжки и т.д.",
        ]

    @staticmethod
    def verifyDomain(url):
        return (urllib.parse.urlparse(url).hostname in AuctionSpbParser.HostNames)

    @staticmethod
    def categories():
        return AuctionSpbParser.Categories

    def __init__(self, parent=None):
        super().__init__(parent)

    def _encoding(self):
        return 'windows-1251'

    def pages(self, auctNo, category):
        self.page_category = category

        page = 0
        while 1:
            yield page
            page = page + 20

    def getPageUrl(self, auctNo, category, page):
        self.page_category = category

        params = urllib.parse.urlencode({'auctID': auctNo, 'catID': category+1, 'order': 'numblot', 'p': page})
        url = "http://auction.spb.ru/?%s" % params
        return url

    def _parsePage(self):
        items = []
        hostname = 'http://' + urllib.parse.urlparse(self.url).hostname
        table = self.html.cssselect('table tr')[4].cssselect('table td')[1].cssselect('table')[0]

        for tr in table.cssselect('tr'):
            tds = tr.cssselect('td')
            if len(tds) >= 9:
                url = hostname + tds[1].cssselect('a')[0].attrib['href']
                denomination = str(tds[2].text_content()).strip()
                year = str(tds[3].text_content())
                mintmark = str(tds[4].text_content())
                material = str(tds[5].text_content())
                grade = _stringToGrade(tds[6].text_content())
                buyer = str(tds[7].text_content())
                bids = int(tds[8].text_content())
                price = stringToMoney(tds[9].text_content())
                totalPayPrice = self.totalPayPrice(price)
                totalSalePrice = self.totalSalePrice(price)
                items.append({
                        'url': url, 'denomination': denomination, 'year': year,
                        'mintmark': mintmark, 'material': material,
                        'grade': grade, 'buyer': buyer, 'bids': bids,
                        'price': price, 'totalPayPrice': totalPayPrice,
                        'totalSalePrice': totalSalePrice})

        return items

    def _parse(self):
        table = self.html.cssselect('table tr')[4].cssselect('table td')[0]
        if table.text_content().find("Торги по лоту завершились") < 0:
            raise _NotDoneYetError()

        item = {}

        content = table.cssselect('strong')[0].text_content()
        item['lotnum'] = content.split('.')[0].split()[-1]

        content = table.cssselect('b')[0].text_content()
        date = content.split()[1]  # convert '12:00:00 05-12-07' to '05-12-07'
        date = QtCore.QDate.fromString(date, 'dd-MM-yyyy')
        if date.year() < 1960:
            date = date.addYears(100)
        item['date'] = date.toString(QtCore.Qt.ISODate)

        content = table.cssselect('strong')[2].text_content()
        item['buyer'] = content.split()[-1]

        content = table.cssselect('strong')[0].text_content()
        if content[-1] == '.':
            content = content[:-1]
        part = content.split('\xA0', 1)[-1]  # remove 'Лот № 8607'
        item['title'] = ' '.join(part.split())  # remove extra spaces
        # Parse Country only for Foreign coins
        if self.page_category == 6:
            parts = part.split('.')
            if len(parts) > 1:
                country = parts[1]
                for ch in '",0123456789':
                    if ch in country:
                        country = country.split(ch)[0]
                country = country.strip()
                if country:
                    if country.split()[-1] == 'г':
                        country = ' '.join(part.split()[:-1])
                    if country:
                        item['country'] = country

#        content = table.cssselect('strong')[1].text_content()
#        grade = content.split()[1]
#        grade = grade.replace('.', '')  # remove end dot
#        item['grade'] = _stringToGrade(grade)

#        item['info'] = self.url

        if len(table.cssselect('table tr')) - 1 < 2:
            print("Only 1 bid")

#        content = table.cssselect('strong')[2].text_content()
#        item['price'] = stringToMoney(content)

#        price = float(item['price'])
#        item['totalPayPrice'] = self.totalPayPrice(price)
#        item['totalSalePrice'] = self.totalSalePrice(price)

        images = []
        content = table.cssselect('a')[0]
        href = content.attrib['href']
        href = urllib.parse.urljoin(self.url, href)
        images.append(href)

        content = table.cssselect('a')[1]
        href = content.attrib['href']
        href = urllib.parse.urljoin(self.url, href)
        images.append(href)
        item['images'] = images

        bidders = {}
        for tr in table.cssselect('table')[0].cssselect('tr')[1:]:
            bidder = tr.cssselect('td')[0].text_content()
            bidders[bidder] = None
        item['bidders'] = len(bidders.keys())

        return item

    def totalSalePrice(self, price):
        commission = price * 15 / 100
        if commission < 35:
            commission = 35

        totalPrice = price - commission
        if totalPrice < 0:
            totalPrice = 0

        return str(totalPrice)

    def totalPayPrice(self, price):
        return str(price + price * 10 / 100)


class ConrosParser(_AuctionParser):
    HostName = 'auction.conros.ru'

    @staticmethod
    def verifyDomain(url):
        return (urllib.parse.urlparse(url).hostname == ConrosParser.HostName)

    def __init__(self, parent=None):
        super(ConrosParser, self).__init__(parent)

    def _encoding(self):
        return 'windows-1251'

    def _parse(self):
        if self.html.cssselect('div#your_rate')[0].text_content().find("Торги по этому лоту завершены") < 0:
            raise _NotDoneYetError()

        auctionItem = AuctionItem('Конрос')

        content = self.html.cssselect('p#lot_state.lot_info_box')[0].text_content()
        date = content.split()[9]  # extract date
        auctionItem.date = QtCore.QDate.fromString(date, 'dd.MM.yyyy').toString(QtCore.Qt.ISODate)

        content = self.html.cssselect('p#lot_state.lot_info_box')[0].cssselect('#leader')[0].text_content()
        auctionItem.buyer = content

        content = self.html.cssselect('div#lot_information')[0].cssselect('p')[1]
        grade = content.cssselect('b')[0].text_content()
        auctionItem.grade = _stringToGrade(grade)

        content = content.text_content()
        index = content.find("Особенности")
        if index > 0:
            auctionItem.info = '\n'.join([content[:index], content[index:], self.url])
        else:
            auctionItem.info = '\n'.join([content, self.url])

        content = self.html.cssselect('p#lot_state.lot_info_box')[0].cssselect('#rate_count')[0].text_content()
        if int(content) < 2:
            QMessageBox.information(self.parent(), self.tr("Parse auction lot"),
                                self.tr("Only 1 bid"),
                                QMessageBox.Ok)

        content = self.html.cssselect('p#lot_state.lot_info_box')[0].cssselect('#price')[0].text_content()
        auctionItem.price = stringToMoney(content)

        price = float(auctionItem.price)
        auctionItem.totalPayPrice = str(price + price * 10 / 100)

        price = float(auctionItem.price)
        auctionItem.totalSalePrice = str(price - price * 15 / 100)

        auctionItem.images = []
        for tag in self.html.cssselect('div#lot_information')[0].cssselect('a'):
            href = tag.attrib['href']
            href = urllib.parse.urljoin(self.url, href)
            auctionItem.images.append(href)

        return auctionItem


class WolmarParser(_AuctionParser):
    HostName = 'www.wolmar.ru'

    @staticmethod
    def verifyDomain(url):
        return (urllib.parse.urlparse(url).hostname == WolmarParser.HostName)

    def __init__(self, parent=None):
        super(WolmarParser, self).__init__(parent)

    def _encoding(self):
        return 'windows-1251'

    def _parse(self):
        for el in self.html.find_class('time_line2')[0].getchildren():
            self.html.find_class('time_line2')[0].remove(el)

        item = self.html.find_class('item')[0]
        if item.text_content().find("Лот закрыт") < 0:
            raise _NotDoneYetError()

        auctionItem = AuctionItem('Wolmar')

        values = item.find_class('values')

        content = values[1].text_content()
        bIndex = content.find("Лидер")
        bIndex = content[bIndex:].find(":") + bIndex
        eIndex = content[bIndex:].find("Количество ставок") + bIndex
        auctionItem.buyer = content[bIndex + 1:eIndex].strip()

        content = values[0].text_content()
        bIndex = content.find("Состояние")
        bIndex = content[bIndex:].find(":") + bIndex
        grade = content[bIndex + 1:].strip()
        auctionItem.grade = _stringToGrade(grade)

        auctionItem.info = self.url

        content = values[1].text_content()
        bIndex = content.find("Количество ставок")
        bIndex = content[bIndex:].find(":") + bIndex
        eIndex = content[bIndex:].find("Лот закрыт") + bIndex
        content = content[bIndex + 1:eIndex].strip()
        if int(content) < 2:
            QMessageBox.information(self.parent(),
                                self.tr("Parse auction lot"),
                                self.tr("Only 1 bid"),
                                QMessageBox.Ok)

        content = values[1].text_content()
        bIndex = content.find("Ставка")
        bIndex = content[bIndex:].find(":") + bIndex
        eIndex = content[bIndex:].find("Лидер") + bIndex
        content = content[bIndex + 1:eIndex].strip()
        auctionItem.price = stringToMoney(content)

        price = float(auctionItem.price)
        auctionItem.totalPayPrice = str(price + price * 10 / 100)

        price = float(auctionItem.price)
        auctionItem.totalSalePrice = str(price - price * 10 / 100)

        storedUrl = self.url

        auctionItem.images = []
        for tag in item.cssselect('a'):
            href = tag.attrib['href']
            url = urllib.parse.urljoin(storedUrl, href)
            self.readHtmlPage(url, 'windows-1251')
            content = self.html.cssselect('div')[0]
            for tag in content.cssselect('div'):
                tag.drop_tree()
            content = content.cssselect('img')[0]
            src = content.attrib['src']
            href = urllib.parse.urljoin(self.url, src)
            auctionItem.images.append(href)

        # Extract date from parent page
        url = urllib.parse.urljoin(storedUrl, '.')[:-1]
        self.readHtmlPage(url, 'windows-1251')
        content = self.html.find_class('content')[0].cssselect('h1 span')[0].text_content()
        date = content.split()[1]  # convert '(Закрыт 29.09.2011 12:30)' to '29.09.2011'
        auctionItem.date = QtCore.QDate.fromString(date, 'dd.MM.yyyy').toString(QtCore.Qt.ISODate)

        return auctionItem


def _stringToGrade(string):
    # Parse VF-XF, XF/AU and XF-
    grade = ''
    for c in string:
        if c in '-+/':
            break
        else:
            grade = grade + c

    return grade
