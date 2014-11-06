# -*- coding: utf-8 -*-

from PyQt5 import QtCore, QtGui
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import *

import OpenNumismat
from OpenNumismat.Tools.DialogDecorators import storeDlgSizeDecorator
from OpenNumismat.Auctions.AuctionParser import AuctionSpbParser

#@storeDlgSizeDecorator
class ImportDialog(QDialog):
    params = {}
    
    def __init__(self, parent=None):
        super().__init__(parent,
                         Qt.WindowCloseButtonHint | Qt.WindowSystemMenuHint)

        self.setWindowTitle(self.tr("Import"))

        form = QFormLayout()
        form.setRowWrapPolicy(QFormLayout.WrapLongRows)

        self.auctionSelector = QComboBox(self)
        for lang in ['АукционЪ.СПб']:
            self.auctionSelector.addItem(lang)
        self.auctionSelector.setSizePolicy(QSizePolicy.Fixed,
                                           QSizePolicy.Fixed)
        form.addRow(self.tr("Auction"), self.auctionSelector)

        self.categorySelector = QComboBox(self)
        for cat in [AuctionSpbParser().category(3)]:
            self.categorySelector.addItem(cat)
        self.categorySelector.setSizePolicy(QSizePolicy.Fixed,
                                            QSizePolicy.Fixed)
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
        
        self.setFixedSize(self.sizeHint())

    def start(self):
        self.params['download_images'] = self.downloadImages.isChecked()
        self.params['from_num'] = self.fromNum.value()
        self.params['till_num'] = self.tillNum.value()
        self.accept()
