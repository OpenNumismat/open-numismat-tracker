import locale
import os
import uuid

from PyQt4 import QtGui, QtCore
from PyQt4.QtCore import Qt, pyqtSignal
from PyQt4.QtSql import QSqlTableModel, QSqlDatabase, QSqlQuery, QSqlField

from OpenNumismat.Collection.CollectionFields import FieldTypes as Type
from OpenNumismat.Collection.CollectionFields import CollectionFields
from OpenNumismat.Collection.CollectionPages import CollectionPages
from OpenNumismat.Collection.Password import cryptPassword, PasswordDialog
from OpenNumismat.Collection.Description import CollectionDescription
from OpenNumismat.Reference.Reference import CrossReferenceSection
from OpenNumismat.Reference.ReferenceDialog import AllReferenceDialog
from OpenNumismat.EditCoinDialog.EditCoinDialog import EditCoinDialog
from OpenNumismat.Collection.VersionUpdater import updateCollection
from OpenNumismat.Tools.CursorDecorators import waitCursorDecorator
from OpenNumismat.Tools import Gui
from OpenNumismat.Settings import Settings, BaseSettings
from OpenNumismat import version


class CollectionModel(QSqlTableModel):
    rowInserted = pyqtSignal(object)
    modelChanged = pyqtSignal()
    IMAGE_FORMAT = 'jpg'

    def __init__(self, collection, parent=None):
        super(CollectionModel, self).__init__(parent, collection.db)

        self.intFilter = ''
        self.extFilter = ''

        fileName = collection.fileName
        self.workingDir = QtCore.QFileInfo(fileName).absolutePath()
        self.collectionName = collection.getCollectionName()

        self.reference = collection.reference
        self.fields = collection.fields
        self.description = collection.description

        self.proxy = None

        self.rowsInserted.connect(self.rowsInsertedEvent)

    def rowsInsertedEvent(self, parent, start, end):
        self.insertedRowIndex = self.index(end, 0)

    def data(self, index, role=Qt.DisplayRole):
        if role == Qt.DisplayRole:
            # Localize values
            data = super(CollectionModel, self).data(index, role)
            field = self.fields.fields[index.column()]
            try:
                if field.type == Type.BigInt:
                    text = locale.format("%d", int(data), grouping=True)
                elif field.type == Type.Money:
                    text = locale.format("%.2f", float(data), grouping=True)
                    dp = locale.localeconv()['decimal_point']
                    text = text.rstrip('0').rstrip(dp)
                elif field.type == Type.Value:
                    text = locale.format("%.3f", float(data), grouping=True)
                    dp = locale.localeconv()['decimal_point']
                    text = text.rstrip('0').rstrip(dp)
                elif field.type == Type.Date:
                    date = QtCore.QDate.fromString(data, Qt.ISODate)
                    text = date.toString(Qt.SystemLocaleShortDate)
                elif field.type == Type.Photo:
                    raise NotImplementedError
                    if data:
                        idIndex = self.fieldIndex('id')
                        index_id = self.index(index.row(), idIndex)
                        # TODO: Get via super(CollectionModel, self).data(index, Qt.DisplayRole)
                        id_ = index_id.data()
                        if id_:
                            print(id_, index.column(), field.name)
                        return self.getPhoto(data)
                    else:
                        return None
                elif field.type == Type.Image:
                    if data:
                        return self.getImage(data)
                    else:
                        return None
                elif field.type == Type.DateTime:
                    date = QtCore.QDateTime.fromString(data, Qt.ISODate)
                    # Timestamp in DB stored in UTC
                    date.setTimeSpec(Qt.UTC)
                    date = date.toLocalTime()
                    text = date.toString(Qt.SystemLocaleShortDate)
                else:
                    return data
            except (ValueError, TypeError):
                return data
            return text
        elif role == Qt.UserRole:
            return super(CollectionModel, self).data(index, Qt.DisplayRole)
        elif role == Qt.TextAlignmentRole:
            field = self.fields.fields[index.column()]
            if field.type == Type.BigInt:
                return Qt.AlignRight | Qt.AlignVCenter

        return super(CollectionModel, self).data(index, role)

    def dataDisplayRole(self, index):
        return super(CollectionModel, self).data(index, Qt.DisplayRole)

    def addCoin(self, record, parent=None):
        record.setNull('id')  # remove ID value from record
        dialog = EditCoinDialog(self, record, parent)
        result = dialog.exec_()
        if result == QtGui.QDialog.Accepted:
            self.appendRecord(record)

    def appendRecord(self, record):
        rowCount = self.rowCount()

        self.insertRecord(-1, record)
        self.submitAll()

        if rowCount < self.rowCount():  # inserted row visible in current model
            if self.insertedRowIndex.isValid():
                self.rowInserted.emit(self.insertedRowIndex)

    def appendRecordQuiet(self, record):
        self.insertRecord(-1, record)
        self.submitAll()

    def generatePhotoPath(self, file_title, create_folder=False):
        path = os.path.join(self.workingDir, '%s_images' % self.collectionName,
                            file_title[0:2], file_title[2:4])
        if create_folder:
            os.makedirs(path, exist_ok=True)
        file_name = os.path.join(path, file_title)

        return file_name

    def insertRecord(self, row, record):
        self._updateRecord(record)
        record.setNull('id')  # remove ID value from record
        record.setValue('createdat', record.value('updatedat'))

        if not record.isNull('image'):
            query = QSqlQuery(self.database())
            query.prepare("INSERT INTO images (image) VALUES (?)")
            query.addBindValue(record.value('image'))
            query.exec_()

            img_id = query.lastInsertId()
            record.setValue('image_id', img_id)
        else:
            record.setNull('image_id')

        # TODO: Check result
        res = super(CollectionModel, self).insertRecord(row, record)
        self.submitAll()
        coin_id = self.query().lastInsertId()

        for i in range(4):
            field = "photo%d" % (i + 1)
            if not record.isNull(field):
                file_title = str(uuid.uuid1()) + '.jpg'
                file_name = self.generatePhotoPath(file_title, True)
                file = open(file_name, "wb")
                file.write(record.value(field))
                file.close()

                query = QSqlQuery(self.database())
                query.prepare("""INSERT INTO photos (file, url, position, coin_id)
                                 VALUES (?, ?, ?, ?)""")
                query.addBindValue(file_title)
                url = record.value(field + '_url')
                query.addBindValue(url)
                query.addBindValue(i)
                query.addBindValue(coin_id)
                query.exec_()

        return res

    def setRecord(self, row, record):
        self._updateRecord(record)

        img_id = record.value('image_id')
        if not record.isNull('image'):
            if record.isNull('image_id'):
                query = QSqlQuery(self.database())
                query.prepare("INSERT INTO images (image) VALUES (?)")
                query.addBindValue(record.value('image'))
                query.exec_()

                img_id = query.lastInsertId()
            else:
                query = QSqlQuery(self.database())
                query.prepare("UPDATE images SET image=? WHERE id=?")
                query.addBindValue(record.value('image'))
                query.addBindValue(img_id)
                query.exec_()

            record.setValue('image_id', img_id)
        else:
            if not record.isNull('image_id'):
                query = QSqlQuery(self.database())
                query.prepare("DELETE FROM images WHERE id=?")
                query.addBindValue(img_id)
                query.exec_()

            record.setNull('image_id')

        coin_id = record.value('id')

        for i in range(4):
            field = "photo%d" % (i + 1)
            if not record.isNull(field):
                if record.isNull(field + '_id'):
                    file_title = str(uuid.uuid1()) + '.jpg'
                    file_name = self.generatePhotoPath(file_title, True)
                    file = open(file_name, "wb")
                    file.write(record.value(field))
                    file.close()

                    query = QSqlQuery(self.database())
                    query.prepare("""INSERT INTO photos (file, url, position, coin_id)
                                     VALUES (?, ?, ?)""")
                    query.addBindValue(file_title)
                    url = record.value(field + '_url')
                    query.addBindValue(url)
                    query.addBindValue(i)
                    query.addBindValue(coin_id)
                    query.exec_()
                else:
                    file_title = record.value(field + '_file')
                    file_name = self.generatePhotoPath(file_title)
#                    os.remove(file_name)
                    file = open(file_name, "wb")
                    file.write(record.value(field))
                    file.close()
            else:
                if not record.isNull(field + '_id'):
                    file_title = record.value(field + '_file')
                    file_name = self.generatePhotoPath(file_title)
                    os.remove(file_name)

                    query = QSqlQuery(self.database())
                    query.prepare("DELETE FROM photos WHERE id=?")
                    query.addBindValue(record.value(field + '_id'))
                    query.exec_()

        return super(CollectionModel, self).setRecord(row, record)

    def record(self, row= -1):
        if row >= 0:
            record = super(CollectionModel, self).record(row)
        else:
            record = super(CollectionModel, self).record()

        record.append(QSqlField('image'))
        if not record.isNull('image'):
            img_id = record.value('image_id')
            data = self.getImage(img_id)
            record.setValue('image', data)

        for i in range(4):
            field = "photo%d" % (i + 1)
            record.append(QSqlField(field))
            record.append(QSqlField(field + '_id'))
            record.append(QSqlField(field + '_url'))
            record.append(QSqlField(field + '_file'))

            if not record.isNull('id'):
                query = QSqlQuery(self.database())
                query.prepare("SELECT id, url, file FROM photos WHERE " \
                              "coin_id=? AND position=?")
                query.addBindValue(record.value('id'))
                query.addBindValue(i)
                query.exec_()
                if query.first():
                    img_id = query.record().value('id')
                    record.setValue(field + '_id', img_id)

                    url = query.record().value('url')
                    record.setValue(field + '_url', url)

                    file = query.record().value('file')
                    record.setValue(field + '_file', file)

                    data = self.getPhoto(file)
                    record.setValue(field, data)

        return record

    def getPhotoFiles(self, row):
        record = self.record(row)
        if not record.isNull('id'):
            query = QSqlQuery(self.database())
            query.prepare("SELECT file FROM photos WHERE " \
                          "coin_id=? ORDER BY position")
            query.addBindValue(record.value('id'))
            query.exec_()
            while query.next():
                file_title = query.record().value('file')
                yield file_title

    def removeRow(self, row):
        for file_title in self.getPhotoFiles(row):
            file_name = self.generatePhotoPath(file_title)
            os.remove(file_name)

        record = super(CollectionModel, self).record(row)

        # Cascading delete isn't supported until Sqlite version 3.6.19
        # Version since Qt 4.8.0 is 3.7.7.1
        query = QSqlQuery(self.database())
        query.prepare("DELETE FROM photos WHERE coin_id=?")
        query.addBindValue(record.value('id'))
        query.exec_()

        if not record.isNull('image_id'):
            query = QSqlQuery(self.database())
            query.prepare("DELETE FROM images WHERE id=?")
            query.addBindValue(record.value('image_id'))
            query.exec_()

        return super(CollectionModel, self).removeRow(row)

    def _updateRecord(self, record):
        if self.proxy:
            self.proxy.setDynamicSortFilter(False)

        obverseImage = QtGui.QImage()
        reverseImage = QtGui.QImage()
        for field in self.fields.userFields:
            if field.type == Type.Photo:
                # Convert image to DB format
                data = record.value(field.name)
                if isinstance(data, QtGui.QImage):
                    ba = QtCore.QByteArray()
                    buffer = QtCore.QBuffer(ba)
                    buffer.open(QtCore.QIODevice.WriteOnly)

                    # Resize big images for storing in DB
                    sideLen = Settings()['ImageSideLen']
                    maxWidth = sideLen
                    maxHeight = sideLen
                    image = data
                    if image.width() > maxWidth or image.height() > maxHeight:
                        scaledImage = image.scaled(maxWidth, maxHeight,
                                Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    else:
                        scaledImage = image

                    if field.name == 'photo1':
                        obverseImage = scaledImage
                    if field.name == 'photo2':
                        reverseImage = scaledImage

                    scaledImage.save(buffer, self.IMAGE_FORMAT)
                    record.setValue(field.name, ba)

        # Creating preview image for list
        if record.isNull('photo1') and record.isNull('photo2'):
            record.setNull('image')
        else:
            # Get height of list view for resizing images
            tmp = QtGui.QTableView()
            height = int(tmp.verticalHeader().defaultSectionSize() * 1.5 - 1)

            if not record.isNull('photo1') and obverseImage.isNull():
                obverseImage.loadFromData(record.value('photo1'))
            if not obverseImage.isNull():
                obverseImage = obverseImage.scaledToHeight(height,
                                                    Qt.SmoothTransformation)
            if not record.isNull('photo2') and reverseImage.isNull():
                reverseImage.loadFromData(record.value('photo2'))
            if not reverseImage.isNull():
                reverseImage = reverseImage.scaledToHeight(height,
                                                    Qt.SmoothTransformation)

            image = QtGui.QImage(obverseImage.width() + reverseImage.width(),
                                 height, QtGui.QImage.Format_RGB32)
            image.fill(QtGui.QColor(Qt.white).rgb())

            paint = QtGui.QPainter(image)
            if not record.isNull('photo1'):
                paint.drawImage(QtCore.QRectF(0, 0, obverseImage.width(), height), obverseImage,
                                QtCore.QRectF(0, 0, obverseImage.width(), height))
            if not record.isNull('photo2'):
                paint.drawImage(QtCore.QRectF(obverseImage.width(), 0, reverseImage.width(), height), reverseImage,
                                QtCore.QRectF(0, 0, reverseImage.width(), height))
            paint.end()

            ba = QtCore.QByteArray()
            buffer = QtCore.QBuffer(ba)
            buffer.open(QtCore.QIODevice.WriteOnly)

            # Store as PNG for better view
            image.save(buffer, 'png')
            record.setValue('image', ba)

        currentTime = QtCore.QDateTime.currentDateTimeUtc()
        record.setValue('updatedat', currentTime.toString(Qt.ISODate))

    def submitAll(self):
        ret = super(CollectionModel, self).submitAll()

        if self.proxy:
            self.proxy.setDynamicSortFilter(True)

        return ret

    def select(self):
        ret = super(CollectionModel, self).select()

        self.modelChanged.emit()

        return ret

    def columnType(self, column):
        if isinstance(column, QtCore.QModelIndex):
            column = column.column()

        return self.fields.fields[column].type

    def setFilter(self, filter_):
        self.intFilter = filter_
        self.__applyFilter()

    def setAdditionalFilter(self, filter_):
        self.extFilter = filter_
        self.__applyFilter()

    def getImage(self, img_id):
        query = QSqlQuery(self.database())
        query.prepare("SELECT image FROM images WHERE id=?")
        query.addBindValue(img_id)
        query.exec_()
        if query.first():
            return query.record().value(0)

    def getPhoto(self, file_title):
        file_name = self.generatePhotoPath(file_title)
        try:
            file = open(file_name, "rb")
        except FileNotFoundError:
            return None
        ba = QtCore.QByteArray(file.read())
        file.close()
        return ba

    def __applyFilter(self):
        if self.intFilter and self.extFilter:
            combinedFilter = self.intFilter + " AND " + self.extFilter
        else:
            combinedFilter = self.intFilter + self.extFilter

        # Checking for SQLITE_MAX_SQL_LENGTH (default value - 1 000 000)
        if len(combinedFilter) > 900000:
            QtGui.QMessageBox.warning(self.parent(),
                            self.tr("Filtering"),
                            self.tr("Filter is too complex. Will be ignored"))
            return

        super(CollectionModel, self).setFilter(combinedFilter)


class CollectionSettings(BaseSettings):
    Default = {
            'Version': 1,
            'Type': version.AppName,
            'Password': cryptPassword()
    }

    def __init__(self, collection):
        super(CollectionSettings, self).__init__()
        self.db = collection.db

        if 'settings' not in self.db.tables():
            self.create(self.db)

        query = QSqlQuery("SELECT * FROM settings", self.db)
        while query.next():
            record = query.record()
            if record.value('title') in self.keys():
                self.__setitem__(record.value('title'), record.value('value'))

    def keys(self):
        return self.Default.keys()

    def _getValue(self, key):
        return self.Default[key]

    def save(self):
        self.db.transaction()

        for key, value in self.items():
            # TODO: Insert value if currently not present
            query = QSqlQuery(self.db)
            query.prepare("UPDATE settings SET value=? WHERE title=?")
            query.addBindValue(str(value))
            query.addBindValue(key)
            query.exec_()

        self.db.commit()

    @staticmethod
    def create(db=QSqlDatabase()):
        db.transaction()

        sql = """CREATE TABLE settings (
            title CHAR NOT NULL UNIQUE,
            value CHAR)"""
        QSqlQuery(sql, db)

        for key, value in CollectionSettings.Default.items():
            query = QSqlQuery(db)
            query.prepare("""INSERT INTO settings (title, value)
                    VALUES (?, ?)""")
            query.addBindValue(key)
            query.addBindValue(str(value))
            query.exec_()

        db.commit()


class Collection(QtCore.QObject):
    def __init__(self, reference, parent=None):
        super(Collection, self).__init__(parent)

        self.reference = reference
        self.db = QSqlDatabase.addDatabase('QSQLITE')
        self._pages = None
        self.fileName = None

    def isOpen(self):
        return self.db.isValid()

    def open(self, fileName):
        file = QtCore.QFileInfo(fileName)
        if file.isFile():
            self.db.setDatabaseName(fileName)
            if not self.db.open() or not self.db.tables():
                print(self.db.lastError().text())
                QtGui.QMessageBox.critical(self.parent(),
                                self.tr("Open collection"),
                                self.tr("Can't open collection %s") % fileName)
                return False
        else:
            QtGui.QMessageBox.critical(self.parent(),
                                self.tr("Open collection"),
                                self.tr("Collection %s not exists") % fileName)
            return False

        self.fileName = fileName

        self.settings = CollectionSettings(self)
        if self.settings['Type'] != version.AppName:
            QtGui.QMessageBox.critical(self.parent(),
                    self.tr("Open collection"),
                    self.tr("Collection %s in wrong format %s") % (fileName, version.AppName))
            return False

        if self.settings['Password'] != cryptPassword():
            dialog = PasswordDialog(self, self.parent())
            result = dialog.exec_()
            if result == QtGui.QDialog.Rejected:
                return False

        print(fileName)
        self.fields = CollectionFields(self.db)

        updateCollection(self)

        self._pages = CollectionPages(self.db)

        self.description = CollectionDescription(self)

        return True

    def create(self, fileName):
        if QtCore.QFileInfo(fileName).exists():
            QtGui.QMessageBox.critical(self.parent(),
                                    self.tr("Create collection"),
                                    self.tr("Specified file already exists"))
            return False

        self.db.setDatabaseName(fileName)
        if not self.db.open():
            print(self.db.lastError().text())
            QtGui.QMessageBox.critical(self.parent(),
                                       self.tr("Create collection"),
                                       self.tr("Can't open collection"))
            return False

        self.fileName = fileName

        self.fields = CollectionFields(self.db)

        self.createCoinsTable()

        self._pages = CollectionPages(self.db)

        self.settings = CollectionSettings(self)

        self.description = CollectionDescription(self)

        return True

    def createCoinsTable(self):
        self.db.transaction()

        sql = """CREATE TABLE coins (
                id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                title TEXT, denomination TEXT, country TEXT, period TEXT,
                year INTEGER, mintmark TEXT, category TEXT, subject TEXT,
                material TEXT, diameter NUMERIC, fineness NUMERIC,
                weight NUMERIC, grade TEXT, catalognum TEXT, rarity TEXT,
                variety TEXT, paid NUMERIC, saller TEXT, date TEXT,
                price NUMERIC, bailed NUMERIC, buyer TEXT, bids TEXT,
                bidders TEXT, auction_id INTEGER, lotnum INTEGER, info TEXT,
                image_id INTEGER, quantity INTEGER, url TEXT, createdat TEXT,
                updatedat TEXT)"""
        QSqlQuery(sql, self.db)

        sql = """CREATE INDEX coins_denomination ON coins (denomination)"""
        QSqlQuery(sql, self.db)

        sql = """CREATE TABLE images (
                id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                image BLOB)"""
        QSqlQuery(sql, self.db)

        sql = """CREATE TABLE photos (
                id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                file TEXT,
                url TEXT,
                position INTEGER,
                coin_id INTEGER REFERENCES coins(id) ON DELETE CASCADE)"""
        QSqlQuery(sql, self.db)

        sql = """PRAGMA foreign_keys = ON"""
        QSqlQuery(sql, self.db)

        sql = """CREATE INDEX photos_coin_id ON photos (coin_id)"""
        QSqlQuery(sql, self.db)

        sql = """CREATE TABLE auctions (
                id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                url TEXT,
                date TEXT,
                number INTEGER,
                site_id INTEGER,
                category_id INTEGER)"""
        QSqlQuery(sql, self.db)

        sql = """CREATE TABLE sites (
                id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                url TEXT,
                icon BLOB,
                firm TEXT)"""
        QSqlQuery(sql, self.db)

        sql = """CREATE TABLE categories (
                id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                site_id INTEGER)"""
        QSqlQuery(sql, self.db)

        if not self.db.commit():
            self.db.rollback()

    def getFileName(self):
        return QtCore.QDir(self.fileName).absolutePath()

    def getCollectionName(self):
        return Collection.fileNameToCollectionName(self.fileName)

    def getDescription(self):
        return self.description

    def model(self):
        return self.createModel()

    def pages(self):
        return self._pages

    def createModel(self):
        model = CollectionModel(self)
        model.title = self.getCollectionName()
        model.setEditStrategy(QSqlTableModel.OnManualSubmit)
        model.setTable('coins')
        model.select()
        for field in self.fields:
            model.setHeaderData(field.id, QtCore.Qt.Horizontal, field.title)

        return model

    def createReference(self):
        sections = self.reference.allSections()
        progressDlg = Gui.ProgressDialog(self.tr("Updating reference"),
                            self.tr("Cancel"), len(sections), self.parent())

        for columnName in sections:
            progressDlg.step()
            if progressDlg.wasCanceled():
                break

            refSection = self.reference.section(columnName)
            if isinstance(refSection, CrossReferenceSection):
                rel = refSection.model.relationModel(1)
                for i in range(rel.rowCount()):
                    data = rel.data(rel.index(i, rel.fieldIndex('value')))
                    parentId = rel.data(rel.index(i, rel.fieldIndex('id')))
                    query = QSqlQuery(self.db)
                    sql = "SELECT DISTINCT %s FROM coins WHERE %s<>'' AND %s IS NOT NULL AND %s=?" % (columnName, columnName, columnName, refSection.parentName)
                    query.prepare(sql)
                    query.addBindValue(data)
                    query.exec_()
                    refSection.fillFromQuery(parentId, query)
            else:
                sql = "SELECT DISTINCT %s FROM coins WHERE %s<>'' AND %s IS NOT NULL" % (columnName, columnName, columnName)
                query = QSqlQuery(sql, self.db)
                refSection.fillFromQuery(query)

        progressDlg.reset()

    def editReference(self):
        dialog = AllReferenceDialog(self.reference, self.parent())
        dialog.exec_()

    def referenceMenu(self, parent=None):
        createReferenceAct = QtGui.QAction(self.tr("Fill from collection"), parent)
        createReferenceAct.triggered.connect(self.createReference)

        editReferenceAct = QtGui.QAction(self.tr("Edit..."), parent)
        editReferenceAct.triggered.connect(self.editReference)

        return [createReferenceAct, editReferenceAct]

    @waitCursorDecorator
    def backup(self):
        backupDir = QtCore.QDir(Settings()['backup'])
        if not backupDir.exists():
            backupDir.mkpath(backupDir.path())

        backupFileName = backupDir.filePath("%s_%s.db" % (self.getCollectionName(), QtCore.QDateTime.currentDateTime().toString('yyMMddhhmm')))
        srcFile = QtCore.QFile(self.fileName)
        if not srcFile.copy(backupFileName):
            QtGui.QMessageBox.critical(self.parent(),
                            self.tr("Backup collection"),
                            self.tr("Can't make a collection backup at %s") %
                                                                backupFileName)
            return False

        return True

    @waitCursorDecorator
    def vacuum(self):
        QSqlQuery("VACUUM", self.db)

    @staticmethod
    def fileNameToCollectionName(fileName):
        file = QtCore.QFileInfo(fileName)
        return file.baseName()
