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


class Photo(QtCore.QObject):
    def __init__(self, id_, model):
        QtCore.QObject.__init__(self, model)
        self.model = model
        self.db = model.database()

        self.id_ = id_
        self.file = None
        self.url = None
        self.workingDir = model.workingDir
        self.collectionName = model.collectionName
        self.changed = False
        self.cleared = False
        self.image = QtGui.QImage()

        query = QSqlQuery(self.db)
        query.prepare("SELECT * FROM photos WHERE id=?")
        query.addBindValue(self.id_)
        query.exec_()
        if query.first():
            self.file = query.record().value('file')
            self.url = query.record().value('url')

    def clear(self):
        self.cleared = True

    def isNull(self):
        return not self.file and not self.url and self.image.isNull()

    def isEmpty(self):
        return self.image.isNull()

    def save(self):
        if self.cleared or self.isNull():
            self.remove()
        else:
            if not self.file:
                self.file = str(uuid.uuid1()) + '.jpg'

                if self.id_:
                    query = QSqlQuery(self.db)
                    query.prepare("UPDATE photos SET file=?, url=? WHERE id=?")
                    query.addBindValue(self.file)
                    query.addBindValue(self.url)
                    query.addBindValue(self.id_)
                    query.exec_()
                else:
                    query = QSqlQuery(self.db)
                    query.prepare("INSERT INTO photos (file, url) VALUES (?, ?)")
                    query.addBindValue(self.file)
                    query.addBindValue(self.url)
                    query.exec_()

                    self.id_ = query.lastInsertId()

            if not self.image.isNull():
                file_name = self._generateFileName(self.file, True)
                self.image.save(file_name)

    def remove(self):
        if self.file:
            file_name = self._generateFileName(self.file)
            try:
                os.remove(file_name)
            except FileNotFoundError:
                pass
            self.file = None

        if self.id_:
            query = QSqlQuery(self.db)
            query.prepare("DELETE FROM photos WHERE id=?")
            query.addBindValue(self.id_)
            query.exec_()

        self.id_ = None

    def fileName(self):
        if self.file:
            file_name = self._generateFileName(self.file)
            if os.path.exists(file_name):
                return file_name

        if self.uploadImage():
            self.save()
            return self._generateFileName(self.file)

        return None

    def uploadImage(self):
        if self.url:
            import urllib.request
            try:
                # Wikipedia require any header
                req = urllib.request.Request(self.url,
                                    headers={'User-Agent': version.AppName})
                data = urllib.request.urlopen(req).read()
                return self.image.loadFromData(data)
            except:
                print('Can not load image %s' % self.url)

        return False

    def _generateFileName(self, file_title, create_folder=False):
        path = os.path.join(self.workingDir,
                            '%s_images' % self.collectionName,
                            file_title[0:2], file_title[2:4])

        if create_folder:
            os.makedirs(path, exist_ok=True)
        file_name = os.path.join(path, file_title)

        return file_name


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
            record.setValue('image', img_id)
        else:
            record.setNull('image')

        for i in range(4):
            field = "photo%d" % (i + 1)
            if not record.isNull(field):
                photo = record.value(field)
                if photo.changed:
                    photo.save()
                record.setValue(field, photo.id_)

        return super(CollectionModel, self).insertRecord(row, record)

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

            record.setValue('image', img_id)
        else:
            if not record.isNull('image_id'):
                query = QSqlQuery(self.database())
                query.prepare("DELETE FROM images WHERE id=?")
                query.addBindValue(img_id)
                query.exec_()

            record.setNull('image')

        for i in range(4):
            field = "photo%d" % (i + 1)
            if not record.isNull(field):
                photo = record.value(field)
                if photo.changed:
                    photo.save()
                record.setValue(field, photo.id_)

        return super(CollectionModel, self).setRecord(row, record)

    def record(self, row= -1):
        if row >= 0:
            record = super(CollectionModel, self).record(row)
        else:
            record = super(CollectionModel, self).record()

        record.append(QSqlField('image_id'))
        if not record.isNull('image'):
            img_id = record.value('image')
            data = self.getImage(img_id)
            record.setValue('image', data)
            record.setValue('image_id', img_id)
        else:
            record.setValue('image', None)

        for i in range(4):
            field = "photo%d" % (i + 1)
            photo = Photo(record.value(field), self)
            record.setValue(field, photo)

        return record

    def removeRow(self, row):
        record = self.record(row)

        if not record.isNull('image'):
            query = QSqlQuery(self.database())
            query.prepare("DELETE FROM images WHERE id=?")
            query.addBindValue(record.value('image'))
            query.exec_()

        for i in range(4):
            field = "photo%d" % (i + 1)
            if not record.isNull(field):
                photo = record.value(field)
                photo.remove()

        return super(CollectionModel, self).removeRow(row)

    def _updateRecord(self, record):
        if self.proxy:
            self.proxy.setDynamicSortFilter(False)

        obverseImage = QtGui.QImage()
        reverseImage = QtGui.QImage()
        # Convert image to DB format
#        for field in self.fields.userFields:
#            if field.type == Type.Photo:
#                data = record.value(field.name)
#                if isinstance(data, QtGui.QImage):
#                    ba = QtCore.QByteArray()
#                    buffer = QtCore.QBuffer(ba)
#                    buffer.open(QtCore.QIODevice.WriteOnly)
#
#                    # Resize big images for storing in DB
#                    sideLen = Settings()['ImageSideLen']
#                    maxWidth = sideLen
#                    maxHeight = sideLen
#                    image = data
#                    if image.width() > maxWidth or image.height() > maxHeight:
#                        scaledImage = image.scaled(maxWidth, maxHeight,
#                                Qt.KeepAspectRatio, Qt.SmoothTransformation)
#                    else:
#                        scaledImage = image
#
#                    if field.name == 'photo1':
#                        obverseImage = scaledImage
#                    if field.name == 'photo2':
#                        reverseImage = scaledImage
#
#                    scaledImage.save(buffer, self.IMAGE_FORMAT)
#                    record.setValue(field.name, ba)

        # Creating preview image for list
        if (record.isNull('photo1') or record.value('photo1').isEmpty()) and \
           (record.isNull('photo2') or record.value('photo2').isEmpty()):
            record.setNull('image')
        elif (record.isNull('photo1') or not record.value('photo1').changed) and \
             (record.isNull('photo2') or not record.value('photo2').changed):
            pass
        else:
            # Get height of list view for resizing images
            tmp = QtGui.QTableView()
            height = int(tmp.verticalHeader().defaultSectionSize() * 1.5 - 1)

            if not record.isNull('photo1') and obverseImage.isNull():
                obverseImage = record.value('photo1').image
            if not obverseImage.isNull():
                obverseImage = obverseImage.scaledToHeight(height,
                                                    Qt.SmoothTransformation)
            if not record.isNull('photo2') and reverseImage.isNull():
                reverseImage = record.value('photo2').image
            if not reverseImage.isNull():
                reverseImage = reverseImage.scaledToHeight(height,
                                                    Qt.SmoothTransformation)

            image = QtGui.QImage(obverseImage.width() + reverseImage.width(),
                                 height, QtGui.QImage.Format_RGB32)
            image.fill(QtGui.QColor(Qt.white).rgb())

            paint = QtGui.QPainter(image)
            if not obverseImage.isNull():
                paint.drawImage(QtCore.QRectF(0, 0, obverseImage.width(), height), obverseImage,
                                QtCore.QRectF(0, 0, obverseImage.width(), height))
            if not reverseImage.isNull():
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
                variety TEXT, totalpayprice NUMERIC, saller TEXT, date TEXT,
                price NUMERIC, totalsaleprice NUMERIC, buyer TEXT, bids TEXT,
                bidders TEXT, auctionnum INTEGER, lotnum INTEGER, info TEXT,
                quantity INTEGER, url TEXT, site TEXT, place TEXT,
                image INTEGER, photo1 INTEGER, photo2 INTEGER, photo3 INTEGER,
                photo4 INTEGER, createdat TEXT, updatedat TEXT)"""
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
                url TEXT)"""
        QSqlQuery(sql, self.db)

        sql = """CREATE TABLE auctions (
                id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                date TEXT,
                number INTEGER,
                site TEXT,
                place TEXT,
                category TEXT)"""
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
