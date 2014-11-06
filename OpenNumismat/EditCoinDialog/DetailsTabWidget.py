from PyQt5 import QtGui
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import *

from OpenNumismat.EditCoinDialog.FormItems import DoubleValidator
from OpenNumismat.EditCoinDialog.BaseFormLayout import BaseFormLayout, BaseFormGroupBox, ImageFormLayout
from OpenNumismat.EditCoinDialog.BaseFormLayout import FormItem
from OpenNumismat.Collection.CollectionFields import FieldTypes as Type
from OpenNumismat.Tools.Converters import stringToMoney


class DetailsTabWidget(QTabWidget):
    Direction = QBoxLayout.LeftToRight
    Stretch = 'stretch item'

    def __init__(self, model, parent=None):
        super(DetailsTabWidget, self).__init__(parent)

        self.model = model

        self.createItems()
        self.createPages()

    def createPages(self):
        self.createCoinPage()
        self.createTrafficPage()
        self.createParametersPage()

    def createCoinPage(self):
        main = self.mainDetailsLayout()
        state = self.stateLayout()
        title = QApplication.translate('DetailsTabWidget', "Coin")
        self.addTabPage(title, [main, self.Stretch, state])

    def createTrafficPage(self):
        pass1 = self.pass1Layout()
        pass2 = self.pass2Layout()
        title = QApplication.translate('DetailsTabWidget', "Traffic")
        self.addTabPage(title, [pass1, self.Stretch, pass2])

    def createParametersPage(self):
        parameters = self.parametersLayout()

        catalogue = self.catalogueLayout()
        rarity = self.rarityLayout()
        variation = self.variationLayout()

        title = QApplication.translate('DetailsTabWidget', "Parameters")
        self.addTabPage(title, [parameters, self.Stretch, catalogue, rarity,
                                variation])

    def _layoutToWidget(self, layout):
        widget = QWidget(self)
        widget.setLayout(layout)
        return widget

    def createTabPage(self, parts):
        # Remove all empty parts
        for part in parts:
            if isinstance(part, BaseFormGroupBox):
                if part.isEmpty():
                    parts.remove(part)

        if self.Direction == QBoxLayout.LeftToRight:
            newParts = []
            layout = QVBoxLayout()
            stretchNeeded = True
            count = 0
            for part in parts:
                if part == self.Stretch:
                    if count > 0:
                        newParts.append(layout)
                        if stretchNeeded:
                            layout.insertStretch(-1)
                        layout = QVBoxLayout()
                    stretchNeeded = True
                    count = 0
                else:
                    if isinstance(part, QWidget):
                        layout.addWidget(part)
                        if part.sizePolicy().verticalPolicy() == QSizePolicy.Preferred:
                            stretchNeeded = False
                    else:
                        layout.addLayout(part)
                    count = count + 1
            if count > 0:
                newParts.append(layout)
                if stretchNeeded:
                    layout.insertStretch(-1)
            parts = newParts
        else:
            for part in parts:
                if part == self.Stretch:
                    parts.remove(part)

        pageLayout = QBoxLayout(self.Direction, self)
        # Fill layout with it's parts
        stretchNeeded = True
        for part in parts:
            if isinstance(part, QWidget):
                pageLayout.addWidget(part)
                if part.sizePolicy().verticalPolicy() == QSizePolicy.Preferred:
                    stretchNeeded = False
            else:
                pageLayout.addLayout(part)
                if isinstance(part, ImageFormLayout):
                    stretchNeeded = False

        if self.Direction == QBoxLayout.TopToBottom and stretchNeeded:
            pageLayout.insertStretch(-1)

        return self._layoutToWidget(pageLayout)

    def addTabPage(self, title, parts):
        page = self.createTabPage(parts)
        index = self.addTab(page, title)
        # Disable if empty
        if len(parts) == 0:
            self.setTabEnabled(index, False)

    def addItem(self, field):
        # Skip image fields for not a form
        if field.type in Type.ImageTypes:
            return

        item = FormItem(field.name, field.title, field.type | Type.Disabled)
        if not field.enabled:
            item.setHidden()
        self.items[field.name] = item

    def createItems(self):
        self.items = {}

        fields = self.model.fields
        for field in fields:
            if field not in fields.systemFileds:
                self.addItem(field)

    def fillItems(self, record):
        if not record.isEmpty():
            # Fields with commission dependent on status field and should be
            # filled after it and in right order
            ordered_item_keys = ['status', 'price', 'totalpayprice',
                                 'totalsaleprice']
            for key in ordered_item_keys:
                if key in self.items:
                    item = self.items[key]
                    self._fillItem(record, item)

            for item in self.items.values():
                if item.field() in ordered_item_keys:
                    continue

                self._fillItem(record, item)

    def _fillItem(self, record, item):
        if not record.isNull(item.field()):
            value = record.value(item.field())
            item.setValue(value)
        else:
            item.widget().clear()

    def clear(self):
        for item in self.items.values():
            item.widget().clear()

    def mainDetailsLayout(self, parent=None):
        title = QApplication.translate('DetailsTabWidget', "Main details")
        layout = BaseFormGroupBox(title, parent)

        layout.addRow(self.items['title'])
        layout.addRow(self.items['country'])
        layout.addRow(self.items['period'])
        layout.addRow(self.items['denomination'])
        layout.addRow(self.items['year'], self.items['mintmark'])
        layout.addRow(self.items['category'])
        layout.addRow(self.items['subject'])

        return layout

    def stateLayout(self, parent=None):
        title = QApplication.translate('DetailsTabWidget', "State")
        layout = BaseFormGroupBox(title, parent)

        layout.addRow(self.items['grade'])
        layout.addRow(self.items['quantity'])

        return layout

    def pass1Layout(self, parent=None):
        title = QApplication.translate('DetailsTabWidget', "Pass")
        layout = BaseFormGroupBox(title, parent)

        layout.addRow(self.items['price'], self.items['date'])

        layout.addRow(self.items['bids'], self.items['bidders'])
        layout.addRow(self.items['place'], self.items['site'])
        layout.addRow(self.items['auctionnum'], self.items['lotnum'])
        layout.addRow(self.items['url'])

        return layout

    def pass2Layout(self, parent=None):
        title = QApplication.translate('DetailsTabWidget', "Pass details")
        layout = BaseFormGroupBox(title, parent)

        # Add auxiliary field
        item = self.addPayCommission()
        layout.addRow(self.items['totalpayprice'], item)

        # Add auxiliary field
        item = self.addSaleCommission()
        layout.addRow(self.items['totalsaleprice'], item)

        layout.addRow(self.items['saller'], self.items['buyer'])

        layout.addRow(self.items['info'])

        return layout

    def parametersLayout(self, parent=None):
        title = QApplication.translate('DetailsTabWidget', "Parameters")
        layout = BaseFormGroupBox(title, parent)

        layout.addRow(self.items['material'])
        layout.addRow(self.items['fineness'], self.items['weight'])
        layout.addRow(self.items['diameter'])

        return layout

    def rarityLayout(self, parent=None):
        layout = BaseFormLayout(parent)

        item = self.items['rarity']
        layout.addWidget(item.label(), 1, 0)
        layout.addWidget(item.widget(), 1, 1)
        layout.addWidget(QWidget(), 1, 2)
        item.widget().setSizePolicy(QSizePolicy.Preferred,
                                    QSizePolicy.Fixed)

        return layout

    def catalogueLayout(self, parent=None):
        title = QApplication.translate('DetailsTabWidget', "Catalogue")
        layout = BaseFormGroupBox(title, parent)

        layout.addRow(self.items['catalognum'])

        return layout

    def variationLayout(self, parent=None):
        title = QApplication.translate('DetailsTabWidget', "Variation")
        layout = BaseFormGroupBox(title, parent)

        layout.addRow(self.items['variety'])

        return layout

    def addPayCommission(self):
        title = QApplication.translate('DetailsTabWidget', "Commission")
        self.payComission = FormItem(None, title, Type.Money)

        self.items['price'].widget().textChanged.connect(self.payPriceChanged)
        self.items['totalpayprice'].widget().textChanged.connect(self.payPriceChanged)

        return self.payComission

    def payPriceChanged(self, text):
        price = textToFloat(self.items['price'].value())
        totalPrice = textToFloat(self.items['totalpayprice'].value())
        self.payComission.widget().setText(floatToText(totalPrice - price))

    def addSaleCommission(self):
        title = QApplication.translate('DetailsTabWidget', "Commission")
        self.saleComission = FormItem(None, title, Type.Money)

        self.items['price'].widget().textChanged.connect(self.salePriceChanged)
        self.items['totalsaleprice'].widget().textChanged.connect(self.salePriceChanged)

        return self.saleComission

    def salePriceChanged(self, text):
        price = textToFloat(self.items['price'].value())
        totalPrice = textToFloat(self.items['totalsaleprice'].value())
        self.saleComission.widget().setText(floatToText(price - totalPrice))


class FormDetailsTabWidget(DetailsTabWidget):
    Direction = QBoxLayout.TopToBottom

    def __init__(self, model, parent=None, usedFields=None):
        self.usedFields = usedFields
        self.reference = model.reference

        super(FormDetailsTabWidget, self).__init__(model, parent)

    def createPages(self):
        self.createCoinPage()
        self.createTrafficPage()
        self.createParametersPage()
        self.createImagePage()

    def createImagePage(self):
        if self.usedFields:
            self.addTabPage(self.tr("Images"), [])
        else:
            images = self.imagesLayout()
            self.addTabPage(self.tr("Images"), [images, ])

    def addItem(self, field):
        checkable = 0
        if self.usedFields:
            checkable = Type.Checkable

        refSection = None
        if self.reference:
            refSection = self.reference.section(field.name)

        item = FormItem(field.name, field.title, field.type | checkable, refSection)
        if not field.enabled:
            item.setHidden()
        self.items[field.name] = item

    def createItems(self):
        super(FormDetailsTabWidget, self).createItems()

        if self.reference:
            widget = self.items['country'].widget()
            widget.addDependent(self.items['period'].widget())

    def fillItems(self, record):
        super(FormDetailsTabWidget, self).fillItems(record)

        if self.usedFields:
            for item in self.items.values():
                if self.usedFields[record.indexOf(item.field())]:
                    item.label().setCheckState(Qt.Checked)

    def mainDetailsLayout(self, parent=None):
        layout = BaseFormGroupBox(self.tr("Main details"), parent)

        layout.addRow(self.items['title'])
        layout.addRow(self.items['country'])
        layout.addRow(self.items['period'])
        layout.addRow(self.items['denomination'])
        layout.addRow(self.items['year'], self.items['mintmark'])
        layout.addRow(self.items['category'])
        layout.addRow(self.items['subject'])

        return layout

    def imagesLayout(self, parent=None):
        layout = ImageFormLayout(parent)
        layout.addImages([self.items['photo1'], self.items['photo2'],
                          self.items['photo3'], self.items['photo4']])
        return layout

    def _createTrafficParts(self, index=0):
        self.items['price'].widget().textChanged.disconnect(self.payCommissionChanged)
        self.items['totalpayprice'].widget().textChanged.disconnect(self.payTotalPriceChanged)
        self.payCommission.textChanged.disconnect(self.payCommissionChanged)
        self.items['totalsaleprice'].widget().textChanged.disconnect(self.saleTotalPriceChanged)
        self.saleCommission.textChanged.disconnect(self.saleCommissionChanged)

        pageParts = self.passLayout()

        self.oldTrafficIndex = index

        return pageParts

    def addPayCommission(self):
        item = FormItem(None, self.tr("Commission"), Type.Money)
        self.payCommission = item.widget()

        validator = CommissionValidator(0, 9999999999, 2, self)
        validator.setNotation(QtGui.QDoubleValidator.StandardNotation)
        self.payCommission.setValidator(validator)

        self.items['price'].widget().textChanged.connect(self.payCommissionChanged)
        self.payCommission.textChanged.connect(self.payCommissionChanged)
        self.items['totalpayprice'].widget().textChanged.connect(self.payTotalPriceChanged)

        return item

    def addSaleCommission(self):
        item = FormItem(None, self.tr("Commission"), Type.Money)
        self.saleCommission = item.widget()

        validator = CommissionValidator(0, 9999999999, 2, self)
        validator.setNotation(QtGui.QDoubleValidator.StandardNotation)
        self.saleCommission.setValidator(validator)

        self.items['price'].widget().textChanged.connect(self.saleCommissionChanged)
        self.saleCommission.textChanged.connect(self.saleCommissionChanged)
        self.items['totalsaleprice'].widget().textChanged.connect(self.saleTotalPriceChanged)

        return item

    def payCommissionChanged(self, text):
        self.items['totalpayprice'].widget().textChanged.disconnect(self.payTotalPriceChanged)

        price = textToFloat(self.items['price'].value())
        text = self.payCommission.text().strip()
        if len(text) > 0 and text[-1] == '%':
            commission = price * textToFloat(text[0:-1]) / 100
        else:
            commission = textToFloat(text)
        self.items['totalpayprice'].widget().setText(floatToText(price + commission))

        self.items['totalpayprice'].widget().textChanged.connect(self.payTotalPriceChanged)

    def payTotalPriceChanged(self, text):
        self.payCommission.textChanged.disconnect(self.payCommissionChanged)

        if text:
            price = textToFloat(self.items['price'].value())
            totalPrice = textToFloat(self.items['totalpayprice'].value())
            self.payCommission.setText(floatToText(totalPrice - price))
        else:
            self.payCommission.clear()

        self.payCommission.textChanged.connect(self.payCommissionChanged)

    def saleCommissionChanged(self, text):
        self.items['totalsaleprice'].widget().textChanged.disconnect(self.saleTotalPriceChanged)

        price = textToFloat(self.items['price'].value())
        text = self.saleCommission.text().strip()
        if len(text) > 0 and text[-1] == '%':
            commission = price * textToFloat(text[0:-1]) / 100
        else:
            commission = textToFloat(text)
        self.items['totalsaleprice'].widget().setText(floatToText(price - commission))

        self.items['totalsaleprice'].widget().textChanged.connect(self.saleTotalPriceChanged)

    def saleTotalPriceChanged(self, text):
        self.saleCommission.textChanged.disconnect(self.saleCommissionChanged)

        if text:
            price = textToFloat(self.items['price'].value())
            totalPrice = textToFloat(self.items['totalsaleprice'].value())
            self.saleCommission.setText(floatToText(price - totalPrice))
        else:
            self.saleCommission.clear()

        self.saleCommission.textChanged.connect(self.saleCommissionChanged)


def textToFloat(text):
    if text:
        return stringToMoney(text)
    else:
        return 0


def floatToText(value):
    if value > 0:
        return str(int((value) * 100 + 0.5) / 100)
    else:
        return str(int((value) * 100 - 0.5) / 100)


# Reimplementing DoubleValidator for replace comma with dot and accept %
class CommissionValidator(DoubleValidator):
    def __init__(self, bottom, top, decimals, parent=None):
        super(CommissionValidator, self).__init__(bottom, top, decimals, parent)

    def validate(self, input_, pos):
        hasPercent = False
        numericValue = input_
        if len(input_) > 0 and input_[-1] == '%':
            numericValue = input_[0:-1]  # trim percent sign
            hasPercent = True
        state, validatedValue, pos = super(CommissionValidator, self).validate(numericValue, pos)
        if hasPercent:
            validatedValue = validatedValue + '%'  # restore percent sign
        return state, validatedValue, pos
