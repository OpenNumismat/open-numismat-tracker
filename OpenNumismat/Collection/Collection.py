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
                elif field.type == Type.Image:
                    if not isinstance(data, QtCore.QPyNullVariant):
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

    def generateImagePath(self, img_id, create_folder=False):
        path = '%s/%s_images/%s/%s' % (self.workingDir, self.collectionName,
                                       img_id[0:2], img_id[2:4])
        if create_folder:
            os.makedirs(path, exist_ok=True)
        file_name = '%s/%s.jpg' % (path, img_id)

        return file_name

    def insertRecord(self, row, record):
        self._updateRecord(record)
        record.setNull('id')  # remove ID value from record
        record.setValue('createdat', record.value('updatedat'))

        for field in ['photo1', 'photo2', 'photo3', 'photo4',
                      'photo5', 'photo6', 'photo7', 'photo8']:
            if not record.isNull(field):
                img_id = str(uuid.uuid1())
                file_name = self.generateImagePath(img_id, True)
                file = open(file_name, "wb")
                file.write(record.value(field))
                file.close()
            else:
                img_id = None

            record.setValue(field, img_id)

        return super(CollectionModel, self).insertRecord(row, record)

    def setRecord(self, row, record):
        self._updateRecord(record)
        for field in ['photo1', 'photo2', 'photo3', 'photo4',
                      'photo5', 'photo6', 'photo7', 'photo8']:
            img_id = record.value(field + '_id')
            if record.isNull(field):
                if not record.isNull(field + '_id'):
                    file_name = self.generateImagePath(img_id)
                    os.remove(file_name)

                    img_id = None
            else:
                if record.isNull(field + '_id'):
                    img_id = str(uuid.uuid1())
                    file_name = self.generateImagePath(img_id, True)
                    file = open(file_name, "wb")
                    file.write(record.value(field))
                    file.close()
                else:
                    file_name = self.generateImagePath(img_id)
                    os.remove(file_name)
                    file = open(file_name, "wb")
                    file.write(record.value(field))
                    file.close()

            record.setValue(field, img_id)
        return super(CollectionModel, self).setRecord(row, record)

    def record(self, row= -1):
        if row >= 0:
            record = super(CollectionModel, self).record(row)
        else:
            record = super(CollectionModel, self).record()

        for field in ['photo1', 'photo2', 'photo3', 'photo4',
                      'photo5', 'photo6', 'photo7', 'photo8']:
            record.append(QSqlField(field + '_id'))
            if not record.isNull(field):
                img_id = record.value(field)
                data = self.getImage(img_id)
                record.setValue(field, data)
                record.setValue(field + '_id', img_id)
            else:
                record.setValue(field, None)

        return record

    def removeRow(self, row):
        record = super(CollectionModel, self).record(row)
        for field in ['photo1', 'photo2', 'photo3', 'photo4',
                      'photo5', 'photo6', 'photo7', 'photo8']:
            if not record.isNull(field):
                img_id = record.value(field)
                file_name = self.generateImagePath(img_id)
                os.remove(file_name)

        return super(CollectionModel, self).removeRow(row)

    def _updateRecord(self, record):
        if self.proxy:
            self.proxy.setDynamicSortFilter(False)

        obverseImage = QtGui.QImage()
        reverseImage = QtGui.QImage()
        for field in self.fields.userFields:
            if field.type == Type.Image:
                # Convert image to DB format
                data = record.value(field.name)
                if isinstance(data, str):
                    # Copying record as text (from Excel) store missed images
                    # as string
                    record.setNull(field.name)
                elif isinstance(data, QtGui.QImage):
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
        file_name = self.generateImagePath(img_id)
        file = open(file_name, "rb")
        ba = QtCore.QByteArray(file.read())
        file.close()
        return ba

    def __applyFilter(self):
        if self.intFilter and self.extFilter:
            combinedFilter = self.intFilter + " AND " + self.extFilter
        else:
            combinedFilter = self.intFilter + self.extFilter
        super(CollectionModel, self).setFilter(combinedFilter)

    def isExist(self, record):
        fields = ['denomination', 'country', 'period', 'year', 'grade',
                  'mintmark', 'category', 'subject',
                  'material', 'quality', 'date', 'price',
                  'saller', 'auction', 'auctionnum', 'buyer', 'variety']
        filterParts = [field + '=?' for field in fields]
        sqlFilter = ' AND '.join(filterParts)

        db = self.database()
        query = QSqlQuery(db)
        query.prepare("SELECT count(*) FROM coins WHERE id<>? AND " + sqlFilter)
        query.addBindValue(record.value('id'))
        for field in fields:
            query.addBindValue(record.value(field))
        query.exec_()
        if query.first():
            count = query.record().value(0)
            if count > 0:
                return True

        return False


class CollectionSettings(BaseSettings):
    Default = {'Version': 1, 'Password': cryptPassword()}

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
        sqlFields = []
        for field in self.fields:
            if field.name == 'id':
                sqlFields.append('id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT')
            else:
                sqlFields.append("%s %s" % (field.name, Type.toSql(field.type)))

        sql = "CREATE TABLE coins (" + ", ".join(sqlFields) + ")"
        QSqlQuery(sql, self.db)

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
