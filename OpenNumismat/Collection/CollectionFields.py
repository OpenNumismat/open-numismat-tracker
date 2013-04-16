from PyQt4.QtCore import QT_TRANSLATE_NOOP, QObject
from PyQt4.QtGui import QApplication
from PyQt4.QtSql import QSqlDatabase, QSqlQuery


class FieldTypes():
    String = 1
    ShortString = 2
    Number = 3
    Text = 4
    Money = 5
    Date = 6
    BigInt = 7
    Image = 8
    Value = 9
    Status = 10
    DateTime = 11
    EdgeImage = 12
    PreviewImage = 13

    Mask = 0xFF
    Checkable = 0x100
    Disabled = 0x200

    ImageTypes = (Image, EdgeImage, PreviewImage)

    @staticmethod
    def toSql(type_):
        if type_ == FieldTypes.String:
            sql_type = 'TEXT'
        elif type_ == FieldTypes.ShortString:
            sql_type = 'TEXT'
        elif type_ == FieldTypes.Number:
            sql_type = 'INTEGER'
        elif type_ == FieldTypes.Text:
            sql_type = 'TEXT'
        elif type_ == FieldTypes.Money:
            sql_type = 'NUMERIC'
        elif type_ == FieldTypes.Date:
            sql_type = 'TEXT'
        elif type_ == FieldTypes.BigInt:
            sql_type = 'INTEGER'
        elif type_ == FieldTypes.PreviewImage:
            sql_type = 'BLOB'
        elif type_ == FieldTypes.Image:
            sql_type = 'TEXT'
        elif type_ == FieldTypes.Value:
            sql_type = 'NUMERIC'
        elif type_ == FieldTypes.DateTime:
            sql_type = 'TEXT'
        else:
            raise

        return sql_type


class CollectionField():
    def __init__(self, id_, name, title, type_):
        self.id = id_
        self.name = name
        self.title = title
        self.type = type_


class CollectionFieldsBase(QObject):
    def __init__(self, parent=None):
        from OpenNumismat.Collection.CollectionFields import FieldTypes as Type
        super(CollectionFieldsBase, self).__init__(parent)

        fields = [
                ('id', self.tr("ID"), Type.BigInt),

                ('title', self.tr("Name"), Type.String),
                ('denomination', self.tr("Denomination"), Type.String),
                ('country', self.tr("Country"), Type.String),
                ('period', self.tr("Period"), Type.String),
                ('year', self.tr("Year"), Type.Number),
                ('mintmark', self.tr("Mint mark"), Type.ShortString),
                ('category', self.tr("Category"), Type.String),
                ('subject', self.tr("Subject"), Type.String),
                ('material', self.tr("Material"), Type.String),
                ('diameter', self.tr("Diameter"), Type.Value),
                ('fineness', self.tr("Fineness"), Type.Value),
                ('weight', self.tr("Weight"), Type.Value),
                ('grade', self.tr("Grade"), Type.String),
                ('catalognum1', self.tr("1#"), Type.String),
                ('catalognum2', self.tr("2#"), Type.String),
                ('catalognum3', self.tr("3#"), Type.String),
                ('rarity', self.tr("Rarity"), Type.String),
                ('variety', self.tr("Variety"), Type.String),
                ('paid', self.tr("Paid"), Type.Money),
                ('saller', self.tr("Saller"), Type.String),
                ('date', self.tr("Date"), Type.Date),
                ('price', self.tr("Price"), Type.Money),
                ('bailed', self.tr("Bailed"), Type.Money),
                ('buyer', self.tr("Buyer"), Type.String),
                ('bids', self.tr("Bids"), Type.String),
                ('bidders', self.tr("Bidders"), Type.String),
                ('auction', self.tr("Auction"), Type.String),
                ('auctionnum', self.tr("Auction #"), Type.BigInt),
                ('info', self.tr("Info"), Type.Text),
                ('image', self.tr("Image"), Type.PreviewImage),
                ('photo1', self.tr("Photo 1"), Type.Image),
                ('photo2', self.tr("Photo 2"), Type.Image),
                ('photo3', self.tr("Photo 3"), Type.Image),
                ('photo4', self.tr("Photo 4"), Type.Image),
                ('photo5', self.tr("Photo 5"), Type.Image),
                ('photo6', self.tr("Photo 6"), Type.Image),
                ('photo7', self.tr("Photo 7"), Type.Image),
                ('photo8', self.tr("Photo 8"), Type.Image),
                ('quantity', self.tr("Quantity"), Type.BigInt),
                ('url', self.tr("URL"), Type.String),
                ('createdat', self.tr("Created at"), Type.DateTime),
                ('updatedat', self.tr("Updated at"), Type.DateTime),
            ]

        self.fields = []
        for id_, field in enumerate(fields):
            self.fields.append(
                            CollectionField(id_, field[0], field[1], field[2]))
            setattr(self, self.fields[id_].name, self.fields[id_])

        self.systemFileds = [self.id, self.createdat, self.updatedat]
        self.userFields = list(self.fields)
        for item in self.systemFileds:
            self.userFields.remove(item)

    def field(self, id_):
        return self.fields[id_]

    def __iter__(self):
        self.index = 0
        return self

    def __next__(self):
        if self.index == len(self.fields):
            raise StopIteration
        self.index = self.index + 1
        return self.fields[self.index - 1]


class CollectionFields(CollectionFieldsBase):
    def __init__(self, db, parent=None):
        super(CollectionFields, self).__init__(parent)
        self.db = db

        if 'fields' not in self.db.tables():
            self.create(self.db)

        query = QSqlQuery(self.db)
        query.prepare("SELECT * FROM fields")
        query.exec_()
        self.userFields = []
        self.disabledFields = []
        while query.next():
            record = query.record()
            fieldId = record.value('id')
            field = self.field(fieldId)
            field.title = record.value('title')
            field.enabled = bool(record.value('enabled'))
            if field.enabled:
                self.userFields.append(field)
            else:
                self.disabledFields.append(field)

    def save(self):
        self.db.transaction()

        for field in self.fields:
            query = QSqlQuery(self.db)
            query.prepare("UPDATE fields SET title=?, enabled=? WHERE id=?")
            query.addBindValue(field.title)
            query.addBindValue(int(field.enabled))
            query.addBindValue(field.id)
            query.exec_()

        self.db.commit()

    @staticmethod
    def create(db=QSqlDatabase()):
        db.transaction()

        sql = """CREATE TABLE fields (
            id INTEGER NOT NULL PRIMARY KEY,
            title TEXT,
            enabled INTEGER)"""
        QSqlQuery(sql, db)

        fields = CollectionFieldsBase()

        for field in fields:
            query = QSqlQuery(db)
            query.prepare("""INSERT INTO fields (id, title, enabled)
                VALUES (?, ?, ?)""")
            query.addBindValue(field.id)
            query.addBindValue(field.title)
            enabled = field in fields.userFields
            query.addBindValue(int(enabled))
            query.exec_()

        db.commit()
