from PyQt4 import QtGui
from PyQt4.QtCore import Qt

from OpenNumismat.EditCoinDialog.DetailsTabWidget import FormDetailsTabWidget
from OpenNumismat.Tools.DialogDecorators import storeDlgSizeDecorator


@storeDlgSizeDecorator
class EditCoinDialog(QtGui.QDialog):
    def __init__(self, model, record, parent=None, usedFields=None):
        super(EditCoinDialog, self).__init__(parent, Qt.WindowSystemMenuHint)

        self.clickedButton = QtGui.QDialogButtonBox.Abort

        self.usedFields = usedFields
        self.record = record
        self.model = model

        self.tab = FormDetailsTabWidget(model, self, usedFields)
        self.items = self.tab.items

        self.textChangedTitle()
        self.tab.items['title'].widget().textChanged.connect(
                                                        self.textChangedTitle)
        self.tab.fillItems(record)

        self.buttonBox = QtGui.QDialogButtonBox(Qt.Horizontal)
        self.buttonBox.addButton(QtGui.QDialogButtonBox.Save)
        self.buttonBox.addButton(QtGui.QDialogButtonBox.Cancel)
        self.buttonBox.accepted.connect(self.save)
        self.buttonBox.rejected.connect(self.reject)
        self.buttonBox.clicked.connect(self.clicked)

        layout = QtGui.QVBoxLayout(self)
        layout.addWidget(self.tab)
        layout.addWidget(self.buttonBox)

        self.setLayout(layout)

    def clicked(self, button):
        buttons = [QtGui.QDialogButtonBox.Save, QtGui.QDialogButtonBox.SaveAll,
                   QtGui.QDialogButtonBox.Cancel, QtGui.QDialogButtonBox.Abort]
        for btn in buttons:
            if self.buttonBox.button(btn) == button:
                self.clickedButton = btn

    # Enable 'Save all' button
    def setManyCoins(self, many=True):
        if many:
            self.buttonBox.addButton(QtGui.QDialogButtonBox.SaveAll)
            self.buttonBox.addButton(QtGui.QDialogButtonBox.Abort)

    def textChangedTitle(self, text=''):
        if self.usedFields:
            title = [self.tr("Multi edit"), ]
        elif self.record.isNull('id'):
            title = [self.tr("New"), ]
        else:
            title = [self.tr("Edit"), ]

        if text:
            title.insert(0, text)
        self.setWindowTitle(' - '.join(title))

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.reject()

    def save(self):
        # Clear unused fields
        if not self.usedFields:
            if not self.items['title'].value():
                result = QtGui.QMessageBox.warning(self, self.tr("Save"),
                            self.tr("Coin title not set. Save without title?"),
                            QtGui.QMessageBox.Save | QtGui.QMessageBox.No,
                            QtGui.QMessageBox.No)
                if result != QtGui.QMessageBox.Save:
                    return

        # Checking that TotalPrice not less than Price
        payprice = self.items['price'].value()
        totalpayprice = self.items['paid'].value()
        if totalpayprice and float(totalpayprice) < 0:
            result = QtGui.QMessageBox.warning(self, self.tr("Save"),
                            self.tr("Total paid price is negative. Save?"),
                            QtGui.QMessageBox.Save | QtGui.QMessageBox.No,
                            QtGui.QMessageBox.No)
            if result != QtGui.QMessageBox.Save:
                return
        if payprice and totalpayprice:
            if float(totalpayprice) < float(payprice):
                result = QtGui.QMessageBox.warning(self, self.tr("Save"),
                            self.tr("Pay price is great than total "
                                    "paid price. Save?"),
                            QtGui.QMessageBox.Save | QtGui.QMessageBox.No,
                            QtGui.QMessageBox.No)
                if result != QtGui.QMessageBox.Save:
                    return
        saleprice = self.items['price'].value()
        totalsaleprice = self.items['bailed'].value()
        if totalsaleprice and float(totalsaleprice) < 0:
            result = QtGui.QMessageBox.warning(self, self.tr("Save"),
                            self.tr("Total bailed price is negative. Save?"),
                            QtGui.QMessageBox.Save | QtGui.QMessageBox.No,
                            QtGui.QMessageBox.No)
            if result != QtGui.QMessageBox.Save:
                return
        if saleprice and totalsaleprice:
            if float(saleprice) < float(totalsaleprice):
                result = QtGui.QMessageBox.warning(self, self.tr("Save"),
                            self.tr("Sale price is less than total "
                                    "bailed price. Save?"),
                            QtGui.QMessageBox.Save | QtGui.QMessageBox.No,
                            QtGui.QMessageBox.No)
                if result != QtGui.QMessageBox.Save:
                    return

        for item in self.items.values():
            value = item.value()
            if isinstance(value, str):
                value = value.strip()
            self.record.setValue(item.field(), value)

        self.accept()

    def getUsedFields(self):
        for item in self.items.values():
            index = self.record.indexOf(item.field())
            self.usedFields[index] = item.label().checkState()
        return self.usedFields

    def getRecord(self):
        return self.record
