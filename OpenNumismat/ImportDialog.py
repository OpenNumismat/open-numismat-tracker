# -*- coding: utf-8 -*-

from PyQt5 import QtSql
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import *

from OpenNumismat.Auctions.AuctionParser import AuctionSpbParser, ConrosParser

class ImportDialog(QDialog):
    params = {}

    def __init__(self, model, parent=None):
        super().__init__(parent,
                         Qt.WindowCloseButtonHint | Qt.WindowSystemMenuHint)

        self.db = model.database()

        self.setWindowTitle(self.tr("Import"))

        form = QFormLayout()
        form.setRowWrapPolicy(QFormLayout.WrapLongRows)

        self.auctionSelector = QComboBox(self)
        for auc in ['АукционЪ.СПб', 'Конрос']:
            self.auctionSelector.addItem(auc)
        self.auctionSelector.setSizePolicy(QSizePolicy.Fixed,
                                           QSizePolicy.Fixed)
        self.auctionSelector.currentIndexChanged.connect(self.__updateAuc)
        form.addRow(self.tr("Auction"), self.auctionSelector)

        self.categorySelector = QComboBox(self)
        self.categorySelector.addItem(self.tr("All categories"))
        self.categorySelector.setSizePolicy(QSizePolicy.Fixed,
                                            QSizePolicy.Fixed)
        self.categorySelector.currentIndexChanged.connect(self.__updateNum)
        form.addRow(self.tr("Category"), self.categorySelector)

        groupBox = QGroupBox(self.tr("Period"));
        vbox = QFormLayout(self)

        self.fromNum = QSpinBox(self)
        self.fromNum.setMinimum(1)
        self.fromNum.setMaximum(10000)
        vbox.addRow(self.tr("From"), self.fromNum)

        self.tillNum = QSpinBox(self)
        self.tillNum.setMinimum(1)
        self.tillNum.setMaximum(10000)
        vbox.addRow(self.tr("Till"), self.tillNum)

        groupBox.setLayout(vbox)
        form.addRow(groupBox)

        self.downloadImages = QCheckBox(self.tr("Download images"), self)
        form.addRow(self.downloadImages)

        buttonBox = QDialogButtonBox(Qt.Horizontal)
        buttonBox.addButton(QDialogButtonBox.Ok)
        buttonBox.addButton(QDialogButtonBox.Cancel)
        buttonBox.accepted.connect(self.start)
        buttonBox.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttonBox)

        self.setLayout(layout)

        query = QtSql.QSqlQuery(self.db)
        query.prepare("SELECT place, category FROM auctions LIMIT 1")
        query.exec_()
        if query.first():
            place = query.record().value(0)
            self.auctionSelector.setCurrentText(place)
            category = query.record().value(1)
            self.categorySelector.setCurrentText(category)

        self.__updateAuc()

        self.setFixedSize(self.sizeHint())

    def start(self):
        self.params['download_images'] = self.downloadImages.isChecked()
        self.params['from_num'] = self.fromNum.value()
        self.params['till_num'] = self.tillNum.value()
        self.params['category'] = self.categorySelector.currentIndex() + 1
        self.params['auction'] = self.auctionSelector.currentText()

        if self.params['till_num'] < self.params['from_num']:
            QMessageBox.critical(self, self.tr("Import"),
                self.tr("Auction number From should be less or equal to Till"))
            return

        lastNum = self.__getMaxNum()
        if self.params['from_num'] <= lastNum:
            result = QMessageBox.question(self, self.tr("Import"),
                self.tr("Auction number %d already imported.\nContinue anyway?") % self.params['from_num'],
                QMessageBox.Yes | QMessageBox.Cancel,
                QMessageBox.Cancel)
            if result == QMessageBox.Cancel:
                return

        self.accept()

    def __updateNum(self):
        lastNum = self.__getMaxNum()
        self.fromNum.setValue(lastNum + 1)
        self.tillNum.setValue(lastNum + 1)

    def __updateAuc(self):
        self.categorySelector.clear()
        auc_name = self.auctionSelector.currentText()
        categories = []
        if auc_name == 'АукционЪ.СПб':
            categories = AuctionSpbParser.categories()
        elif auc_name == 'Конрос':
            categories = ConrosParser.categories()

        for cat in categories:
            self.categorySelector.addItem(cat)

        lastNum = self.__getMaxNum()
        self.fromNum.setValue(lastNum + 1)
        self.tillNum.setValue(lastNum + 1)

    def __getMaxNum(self):
        query = QtSql.QSqlQuery(self.db)
        query.prepare("SELECT MAX(number) FROM auctions WHERE place = ? AND category = ?")
        query.addBindValue(self.auctionSelector.currentText())
        query.addBindValue(self.categorySelector.currentText())
        query.exec_()
        if query.first():
            lastNum = query.record().value(0)
            if lastNum:
                return lastNum

        return 0
