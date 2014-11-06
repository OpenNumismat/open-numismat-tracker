# -*- coding: utf-8 -*-

import sys
import urllib

from PyQt5 import QtGui, QtCore
from PyQt5.QtWidgets import *

from OpenNumismat.Collection.Collection import Collection
from OpenNumismat.Collection.Description import DescriptionDialog
from OpenNumismat.Collection.Password import PasswordSetDialog
from OpenNumismat.Reference.Reference import Reference
from OpenNumismat.TabView import TabView
from OpenNumismat.Settings import Settings, SettingsDialog
from OpenNumismat.LatestCollections import LatestCollections
from OpenNumismat.Tools.CursorDecorators import waitCursorDecorator
from OpenNumismat.Tools.Gui import createIcon
from OpenNumismat.Reports.Preview import PreviewDialog
from OpenNumismat import version
from OpenNumismat.Tools import Gui
from OpenNumismat.ImportDialog import ImportDialog

from OpenNumismat.Auctions.AuctionParser import AuctionSpbParser


class MainWindow(QMainWindow):
    def __init__(self):
        QMainWindow.__init__(self)

        self.setWindowIcon(createIcon('main.ico'))

        self.createStatusBar()

        settingsAct = QAction(createIcon('cog.png'),
                                    self.tr("Settings..."), self)
        settingsAct.triggered.connect(self.settingsEvent)

        importAct = QAction(self.tr("Import..."), self)
        importAct.triggered.connect(self.importEvent)

        uploadImagesAct = QAction(self.tr("Upload images"), self)
        uploadImagesAct.triggered.connect(self.uploadImagesEvent)

        cancelFilteringAct = QAction(createIcon('funnel.png'),
                                    self.tr("Clear all filters"), self)
        cancelFilteringAct.triggered.connect(self.cancelFilteringEvent)

        exitAct = QAction(createIcon('door_in.png'),
                                self.tr("E&xit"), self)
        exitAct.setShortcut(QtGui.QKeySequence.Quit)
        exitAct.triggered.connect(self.close)

        menubar = self.menuBar()
        file = menubar.addMenu(self.tr("&File"))
        file.addAction(importAct)
        file.addAction(uploadImagesAct)
        file.addSeparator()
        file.addAction(settingsAct)
        file.addSeparator()
        file.addAction(exitAct)

        addCoinAct = QAction(createIcon('add.png'),
                                   self.tr("Add"), self)
        addCoinAct.setShortcut('Insert')
        addCoinAct.triggered.connect(self.addCoin)

        editCoinAct = QAction(createIcon('pencil.png'),
                                   self.tr("Edit..."), self)
        editCoinAct.triggered.connect(self.editCoin)

        style = QApplication.style()
        icon = style.standardIcon(QStyle.SP_TrashIcon)
        deleteCoinAct = QAction(icon,
                                   self.tr("Delete"), self)
        deleteCoinAct.setShortcut(QtGui.QKeySequence.Delete)
        deleteCoinAct.triggered.connect(self.deleteCoin)

        coin = menubar.addMenu(self.tr("Coin"))
        coin.addAction(addCoinAct)
        coin.addAction(editCoinAct)
        coin.addAction(deleteCoinAct)

        viewBrowserAct = QAction(createIcon('page_white_world.png'),
                                   self.tr("View in browser"), self)
        viewBrowserAct.triggered.connect(self.viewBrowser)

        newCollectionAct = QAction(self.tr("&New..."), self)
        newCollectionAct.triggered.connect(self.newCollectionEvent)

        style = QApplication.style()
        icon = style.standardIcon(QStyle.SP_DialogOpenButton)
        openCollectionAct = QAction(icon, self.tr("&Open..."), self)
        openCollectionAct.setShortcut(QtGui.QKeySequence.Open)
        openCollectionAct.triggered.connect(self.openCollectionEvent)

        backupCollectionAct = QAction(
                                    createIcon('database_backup.png'),
                                    self.tr("Backup"), self)
        backupCollectionAct.triggered.connect(self.backupCollectionEvent)

        vacuumCollectionAct = QAction(
                                    createIcon('compress.png'),
                                    self.tr("Vacuum"), self)
        vacuumCollectionAct.triggered.connect(self.vacuumCollectionEvent)

        descriptionCollectionAct = QAction(self.tr("Description"), self)
        descriptionCollectionAct.triggered.connect(
                                            self.descriptionCollectionEvent)

        passwordCollectionAct = QAction(createIcon('key.png'),
                                              self.tr("Set password..."), self)
        passwordCollectionAct.triggered.connect(self.passwordCollectionEvent)

        collectionMenu = menubar.addMenu(self.tr("Collection"))
        collectionMenu.addAction(newCollectionAct)
        collectionMenu.addAction(openCollectionAct)
        collectionMenu.addAction(backupCollectionAct)
        collectionMenu.addAction(vacuumCollectionAct)
        collectionMenu.addAction(passwordCollectionAct)
        collectionMenu.addAction(descriptionCollectionAct)
        collectionMenu.addSeparator()

        self.latestActions = []
        self.__updateLatest(collectionMenu)

        self.viewTab = TabView(self)

        actions = self.viewTab.actions()
        listMenu = menubar.addMenu(self.tr("List"))
        listMenu.addAction(actions['new'])
        listMenu.addMenu(actions['open'])
        listMenu.aboutToShow.connect(self.viewTab.updateOpenPageMenu)
        listMenu.addAction(actions['rename'])
        listMenu.addSeparator()
        listMenu.addAction(actions['select'])
        listMenu.addSeparator()
        listMenu.addAction(actions['close'])
        listMenu.addAction(actions['remove'])

        self.referenceMenu = menubar.addMenu(self.tr("Reference"))

        reportAct = QAction(self.tr("Report..."), self)
        reportAct.setShortcut(QtCore.Qt.CTRL + QtCore.Qt.Key_P)
        reportAct.triggered.connect(self.report)

        saveTableAct = QAction(createIcon('table.png'),
                                     self.tr("Save current list..."), self)
        saveTableAct.triggered.connect(self.saveTable)

        report = menubar.addMenu(self.tr("Report"))
        report.addAction(reportAct)
        report.addAction(saveTableAct)
        report.addAction(viewBrowserAct)

        helpAct = QAction(createIcon('help.png'),
                                self.tr("Online help"), self)
        helpAct.setShortcut(QtGui.QKeySequence.HelpContents)
        helpAct.triggered.connect(self.onlineHelp)
        checkUpdatesAct = QAction(self.tr("Check for updates"), self)
        checkUpdatesAct.triggered.connect(self.manualUpdate)
        aboutAct = QAction(self.tr("About %s") % version.AppName, self)
        aboutAct.triggered.connect(self.about)

        help_ = menubar.addMenu(self.tr("&Help"))
        help_.addAction(helpAct)
        help_.addSeparator()
        help_.addAction(checkUpdatesAct)
        help_.addSeparator()
        help_.addAction(aboutAct)

        toolBar = QToolBar(self.tr("Toolbar"), self)
        toolBar.setMovable(False)
        toolBar.addAction(addCoinAct)
        toolBar.addAction(editCoinAct)
        toolBar.addAction(viewBrowserAct)
        toolBar.addSeparator()
        toolBar.addAction(cancelFilteringAct)
        toolBar.addSeparator()
        toolBar.addAction(settingsAct)
        self.addToolBar(toolBar)

        self.setWindowTitle(version.AppName)

        self.reference = Reference(self)
        self.reference.open(Settings()['reference'])

        if len(sys.argv) > 1:
            fileName = sys.argv[1]
        else:
            latest = LatestCollections(self)
            fileName = latest.latest()

        self.collection = Collection(self.reference, self)
        self.openCollection(fileName)

        self.setCentralWidget(self.viewTab)

        settings = QtCore.QSettings()
        pageIndex = settings.value('tabwindow/page')
        if pageIndex != None:
            self.viewTab.setCurrentIndex(int(pageIndex))

        if settings.value('mainwindow/maximized') == 'true':
            self.setWindowState(self.windowState() | QtCore.Qt.WindowMaximized)
        else:
            size = settings.value('mainwindow/size')
            if size:
                self.resize(size)

        self.autoUpdate()

    def createStatusBar(self):
        self.collectionFileLabel = QLabel()
        self.statusBar().addWidget(self.collectionFileLabel)

    def __updateLatest(self, menu=None):
        if menu:
            self.__menu = menu
        for act in self.latestActions:
            self.__menu.removeAction(act)

        self.latestActions = []
        latest = LatestCollections(self)
        for act in latest.actions():
            self.latestActions.append(act)
            act.latestTriggered.connect(self.openCollection)
            self.__menu.addAction(act)

    def cancelFilteringEvent(self):
        listView = self.viewTab.currentListView()
        listView.clearAllFilters()

    def settingsEvent(self):
        dialog = SettingsDialog(self.collection, self)
        res = dialog.exec_()
        if res == QDialog.Accepted:
            self.__restart()

    def __restart(self):
        result = QMessageBox.question(self, self.tr("Settings"),
                    self.tr("The application will need to restart to apply "
                            "the new settings. Restart it now?"),
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.Yes)
        if result == QMessageBox.Yes:
            self.close()
            program = sys.executable
            argv = []
            if program != sys.argv[0]:
                # Process running as Python arg
                argv.append(sys.argv[0])
            QtCore.QProcess.startDetached(program, argv)

    def addCoin(self):
        model = self.viewTab.currentModel()
        model.addCoin(model.record(), self)

    def editCoin(self):
        listView = self.viewTab.currentListView()
        indexes = listView.selectedRows()
        if len(indexes) == 1:
            listView._edit(indexes[0])
        elif len(indexes) > 1:
            listView._multiEdit(indexes)

    def deleteCoin(self):
        listView = self.viewTab.currentListView()
        indexes = listView.selectedRows()
        if len(indexes):
            listView._delete(indexes)

    def viewBrowser(self):
        listView = self.viewTab.currentListView()
        listView.viewInBrowser()

    def report(self):
        listView = self.viewTab.currentListView()
        indexes = listView.selectedRows()
        model = listView.model()

        records = []
        for index in indexes:
            records.append(model.record(index.row()))

        preview = PreviewDialog(model, records, self)
        preview.exec_()

    def saveTable(self):
        listView = self.viewTab.currentListView()
        listView.saveTable()

    def __workingDir(self):
        fileName = self.collection.fileName
        if not fileName:
            fileName = LatestCollections.DefaultCollectionName
        return QtCore.QFileInfo(fileName).absolutePath()

    def openCollectionEvent(self):
        fileName, _selectedFilter = QFileDialog.getOpenFileName(self,
                self.tr("Open collection"), self.__workingDir(),
                self.tr("Collections (*.db)"))
        if fileName:
            self.openCollection(fileName)

    def newCollectionEvent(self):
        fileName, _selectedFilter = QFileDialog.getSaveFileName(self,
                self.tr("New collection"), self.__workingDir(),
                self.tr("Collections (*.db)"),
                QFileDialog.DontConfirmOverwrite)
        if fileName:
            self.__saveParams()

            if self.collection.create(fileName):
                self.setCollection(self.collection)

    def descriptionCollectionEvent(self, checked):
        dialog = DescriptionDialog(self.collection.getDescription(), self)
        dialog.exec_()

    def passwordCollectionEvent(self, checked):
        dialog = PasswordSetDialog(self.collection, self)
        dialog.exec_()

    def backupCollectionEvent(self, checked):
        self.collection.backup()

    def vacuumCollectionEvent(self, checked):
        self.collection.vacuum()

    def openCollection(self, fileName):
        self.__saveParams()

        if self.collection.open(fileName):
            self.setCollection(self.collection)
        else:
            # Remove wrong collection from latest collections list
            latest = LatestCollections(self)
            latest.delete(fileName)
            self.__updateLatest()

    @waitCursorDecorator
    def setCollection(self, collection):
        self.collectionFileLabel.setText(collection.getFileName())
        title = "%s - %s" % (collection.getCollectionName(), version.AppName)
        self.setWindowTitle(title)

        latest = LatestCollections(self)
        latest.add(collection.getFileName())
        self.__updateLatest()

        self.viewTab.setCollection(collection)

        self.referenceMenu.clear()
        for action in self.collection.referenceMenu(self):
            self.referenceMenu.addAction(action)

    def closeEvent(self, e):
        self.__shutDown()

    def __shutDown(self):
        self.__saveParams()

        settings = QtCore.QSettings()

        if self.collection.fileName:
            self.viewTab.savePagePositions()
            # Save latest opened page
            settings.setValue('tabwindow/page', self.viewTab.currentIndex())

        # Save main window size
        settings.setValue('mainwindow/size', self.size())
        settings.setValue('mainwindow/maximized', self.isMaximized())

    def __saveParams(self):
        if self.collection.pages():
            for param in self.collection.pages().pagesParam():
                param.listParam.save()

    def about(self):
        QMessageBox.about(self, self.tr("About %s") % version.AppName,
                self.tr("%s %s\n\n"
                        "Copyright (C) 2013 Vitaly Ignatov\n\n"
                        "%s is freeware licensed under a GPLv3.") %
                        (version.AppName, version.Version, version.AppName))

    def onlineHelp(self):
        url = QtCore.QUrl(version.Web)

        executor = QtGui.QDesktopServices()
        executor.openUrl(url)

    def autoUpdate(self):
        if Settings()['updates']:
            currentDate = QtCore.QDate.currentDate()

            settings = QtCore.QSettings()
            lastUpdateDateStr = settings.value('mainwindow/last_update')
            if lastUpdateDateStr:
                lastUpdateDate = QtCore.QDate.fromString(lastUpdateDateStr,
                                                         QtCore.Qt.ISODate)
                if lastUpdateDate.addDays(10) < currentDate:
                    self.checkUpdates()
            else:
                self.checkUpdates()

    def manualUpdate(self):
        if not self.checkUpdates():
            QMessageBox.information(self, self.tr("Updates"),
                    self.tr("You already have the latest version."))

    def checkUpdates(self):
        currentDate = QtCore.QDate.currentDate()
        currentDateStr = currentDate.toString(QtCore.Qt.ISODate)
        settings = QtCore.QSettings()
        settings.setValue('mainwindow/last_update', currentDateStr)

        newVersion = self.__getNewVersion()
        if newVersion and newVersion != version.Version:
            result = QMessageBox.question(self, self.tr("New version"),
                        self.tr("New version is available. Download it now?"),
                        QMessageBox.Yes | QMessageBox.No,
                        QMessageBox.Yes)
            if result == QMessageBox.Yes:
                url = QtCore.QUrl(version.Web + 'wiki/MainPage')

                executor = QtGui.QDesktopServices()
                executor.openUrl(url)

            return True
        else:
            return False

    @waitCursorDecorator
    def __getNewVersion(self):
        import urllib.request
        from xml.dom.minidom import parseString

        newVersion = version.Version

        try:
            url = "http://wiki.open-numismat-tracker.googlecode.com/git/data/pad.xml"
            req = urllib.request.Request(url)
            data = urllib.request.urlopen(req).read()
            xml = parseString(data)
            tag = xml.getElementsByTagName('Program_Version')[0]
            newVersion = tag.firstChild.nodeValue
        except:
            return None

        return newVersion

    def uploadImagesEvent(self):
        from PyQt5 import QtSql
        from OpenNumismat.Collection.Collection import Photo

        model = self.collection.model()

        query = QtSql.QSqlQuery(self.collection.db)
        query.prepare("SELECT count(*) FROM photos WHERE ifnull(url,'')<>''")
        query.exec_()
        if query.first():
            count = query.record().value(0)
            progressDlg = Gui.ProgressDialog(self.tr("Uploading images"),
                                self.tr("Cancel"), count, self)

            query = QtSql.QSqlQuery(self.collection.db)
            query.prepare("SELECT id FROM photos WHERE ifnull(url,'')<>''")
            query.exec_()

            while query.next():
                progressDlg.step()
                if progressDlg.wasCanceled():
                    break

                photo = Photo(query.record().value('id'), model)
                photo.uploadImage()

            progressDlg.reset()
            query.clear()

    def importEvent(self):
        from PyQt5 import QtSql
        from OpenNumismat.Collection.Collection import Photo
        
        dialog = ImportDialog(self)
        res = dialog.exec_()
        if res == QDialog.Accepted:
            model = self.collection.model()
    
            parser = AuctionSpbParser()
            categories = [3, ]
            for auctNo in range(dialog.params['from_num'], dialog.params['till_num']+1):
    
                for category in categories:
                    url = parser.getPageUrl(auctNo, category, 0)
                    items = parser.parsePage(url)
                    if not items:
                        continue
    
                    item1 = parser.parse(items[0]['url'])
    
                    query = QtSql.QSqlQuery(self.collection.db)
                    query.prepare("INSERT INTO auctions (number, date, site, place, category)" \
                                  " VALUES (?, ?, ?, ?, ?)")
                    query.addBindValue(auctNo)
                    query.addBindValue(item1['date'])
                    query.addBindValue('Аукцион')
                    query.addBindValue('АукционЪ.СПб')
                    query.addBindValue(parser.category(category))
    
                    query.exec_()
    
                    auct_id = query.lastInsertId()
    
                    for page in parser.pages(auctNo, category):
                        url = parser.getPageUrl(auctNo, category, page)
                        items = parser.parsePage(url)
                        print(len(items))
                        if not items:
                            break
    
                        for item in items:
                            item1 = parser.parse(item['url'])
    
                            record_item = {
                                    'title': item1['title'],
                                    'denomination': item['denomination'],
                                    'year': item['year'],
                                    'mintmark': item['mintmark'],
                                    'category': parser.category(category),
                                    'status': 'pass',
                                    'material': item['material'],
                                    'grade': item['grade'],
                                    'price': item['price'],
                                    'totalpayprice': item['totalPayPrice'],
                                    'totalsaleprice': item['totalSalePrice'],
                                    'buyer': item['buyer'],
                                    'url': item['url'],
                                    'bids': item['bids'],
                                    'bidders': item1['bidders'],
                                    'date': item1['date'],
                                    'lotnum': item1['lotnum'],
                                    'auctionnum': auctNo,
                                    'site': 'Аукцион',
                                    'place': 'АукционЪ.СПб',
                                    'category': parser.category(category),
                            }
                            imageFields = ['photo1', 'photo2', 'photo3', 'photo4']
                            for i, imageUrl in enumerate(item1['images']):
                                if i < len(imageFields):
                                    photo = Photo(None, model)
                                    photo.url = imageUrl
                                    # When error - repeat uploading
                                    for _ in range(5):
                                        if photo.uploadImage():
                                            break
    
                                    photo.changed = True
                                    record_item[imageFields[i]] = photo
    
                            record = model.record()
                            for field, value in record_item.items():
                                record.setValue(field, value)
                            model.appendRecordQuiet(record)
